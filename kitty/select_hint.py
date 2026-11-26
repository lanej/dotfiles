"""Select hyperlinks and file references, opening files on their Zellij host."""
import base64
import json
import os
import re
import subprocess
import sys
import time
from functools import partial
from urllib.parse import unquote, urlsplit

from kittens.hints.main import handle_result as open_native_hint, on_mark_clicked
from kittens.tui.handler import result_handler
from kitty.fast_data_types import add_timer, remove_timer

from hint_overlay import encode_snapshot, hyperlink_marks, raw_url_marks, source_snapshot
from hint_renderer import encode_session


EXT = r"\.(?:png|jpe?g|webp|gif|bmp|tiff?|avif|ico|svg|heic|jxl)"
IMAGE_END = re.compile(EXT + "$", re.I)
TOKEN = r"""[^\s<>"'`()\[\]{},;│┃]+"""
QUOTED_POSITION = r"(?::[1-9][0-9]*(?::[1-9][0-9]*)?:?)?"
PATH = re.compile(
    rf'"(?P<double_quoted>[^"\n]+)"{QUOTED_POSITION}'
    rf"|'(?P<single_quoted>[^'\n]+)'{QUOTED_POSITION}"
    rf"|`(?P<backtick_quoted>[^`\n]+)`{QUOTED_POSITION}"
    rf"""|(?P<bare>{TOKEN})""")
POSITION = re.compile(r"^(.*?):([1-9][0-9]*)(?::([1-9][0-9]*))?$")
FRAGMENT = re.compile(r"(?:L)?([1-9][0-9]*)(?:C([1-9][0-9]*))?(?:-(?:L)?[1-9][0-9]*)?$")
BASENAME = re.compile(r"^[^/]+\.[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
DOTFILE = re.compile(r"^\.[a-zA-Z0-9_][\w.-]*$")
PLAIN_NAMES = {"Makefile", "Dockerfile", "Containerfile", "README", "LICENSE", "COPYING", "Justfile", "Gemfile", "Rakefile"}
READY = re.compile(r"dotfiles-hints(?:-v2)?://([0-9a-f]{32})" + r"/(\d+)" * 6)
BUILDING = "dotfiles-hints-building"
FAILED = "dotfiles-hints-error"
REQUEST = b"\x1b[24;7~"  # Ctrl+Alt+F12, a single Zellij action on this connection
OSC8 = "\x1b]8;;"
ST = "\x1b\\"


def in_zellij(window):
    commands = {os.path.basename(p["cmdline"][0]) for p in window.child.foreground_processes if p["cmdline"]}
    return window.screen.is_using_alternate_linebuf() and (
        "zellij" in commands or ("ssh" in commands and window.user_vars.get("dotfiles_zellij"))
    )


def capture(screen):
    rows = []
    destinations = {}
    for y in range(screen.lines):
        line = screen.visual_line(y)
        row = []
        for x, ident in enumerate(line.hyperlink_ids()):
            char = line[x]
            if char == "\0":
                char = " "
            elif line.width(x) == 0:
                char = ""  # wide character continuation
            if ident and ident not in destinations:
                destinations[ident] = screen.hyperlink_for_id(ident)
            row.append((char, destinations.get(ident, "")))
        rows.append(row)
    return rows


def file_target(value):
    """Parse links or printed references without treating web URLs as local files."""
    if value.startswith("file:"):
        try:
            url = urlsplit(value)
            path = unquote(url.path)
            if not path.startswith("/") or any(ord(char) < 32 for char in path):
                return None
            target = {"path": path, "host": url.hostname or ""}
            if url.fragment:
                position = FRAGMENT.fullmatch(url.fragment)
                if not position:
                    return None
                target["line"] = int(position[1])
                if position[2]:
                    target["column"] = int(position[2])
            return target
        except ValueError:
            return None
    if "://" in value or value.startswith(("mailto:", "dotfiles-")):
        return None
    value = value.rstrip(".,;!?")
    target = {}
    position = POSITION.fullmatch(value.removesuffix(":"))
    if position:
        value = position[1]
        target["line"] = int(position[2])
        if position[3]:
            target["column"] = int(position[3])
    if not value or any(ord(char) < 32 for char in value):
        return None
    if not ("/" in value or BASENAME.fullmatch(value) or DOTFILE.fullmatch(value) or value in PLAIN_NAMES):
        return None
    target["path"] = value
    return target


def has_file_hints(rows):
    destinations = {url for row in rows for _, url in row if url}
    if any(file_target(url) for url in destinations):
        return True
    text = "\n".join("".join(char if not url else " " for char, url in row) for row in rows)
    return any(file_target(match[match.lastgroup]) for match in PATH.finditer(text))


def pane_text(rows, rect):
    left, top, width, height = rect
    chars, positions = [], []
    join_next = False
    for y in range(top, min(top + height, len(rows))):
        cells = rows[y][left:left + width]
        line, points = [], []
        for x, (char, url) in enumerate(cells, left):
            value = " " if url else char
            line.extend(value)
            points.extend([(x, y)] * len(value))
        raw = "".join(line)
        content = raw.rstrip()
        start = len(raw) - len(raw.lstrip()) if join_next else 0
        if not join_next:
            chars.append("\n")
            positions.append(None)
        chars.extend(content[start:])
        positions.extend(points[start:len(content)])
        # A TUI may hard-wrap inside its pane with a few cells of right/left padding.
        last_word = content.split()[-1] if content else ""
        join_next = (bool(last_word) and len(raw) - len(content) <= 4
                     and ("/" in last_word or last_word.endswith(("-", "_", ".")))
                     and not IMAGE_END.search(last_word)
                     and not POSITION.fullmatch(last_word.removesuffix(":"))
                     and last_word[-1] not in ")]}\"'`,;")
    return "".join(chars), positions


def picker_input(rows, rect, ticket, files=True, return_overrides=False):
    left, top, width, height = rect
    choices, marks, tokens = {}, {}, {}

    def mark(image):
        key = (image["path"], image.get("host", ""), image.get("line"), image.get("column"))
        if key not in tokens:
            token = f"dotfiles-image:{ticket}/{len(tokens)}"
            choices[token] = image
            tokens[key] = token
        return tokens[key]

    text, positions = pane_text(rows, rect)
    for match in PATH.finditer(text):
        group = match.lastgroup
        start, end = match.span(group)
        path = text[start:end]
        if group != "bare":
            path += text[end + 1:match.end()]
        image = file_target(path)
        if not image or (not files and not IMAGE_END.search(image["path"])):
            continue
        token = mark(image)
        # Hint the first visible fragment once, even if the full path wraps.
        row = positions[start][1]
        for point in positions[start:end]:
            if point is None or point[1] != row:
                break
            marks[point] = token

    lines, overrides = [], {}
    for y, row in enumerate(rows):
        previous, parts = "", []
        for x, (char, url) in enumerate(row):
            if not char:
                continue
            if url and top <= y < top + height and left <= x < left + width:
                image = file_target(url)
                if image and (files or IMAGE_END.search(image["path"])):
                    url = mark(image)
            url = marks.get((x, y), url)
            if url:
                overrides[(x, y)] = url
            if url != previous:
                parts.append(OSC8 + url + ST)
                previous = url
            parts.append(char)
        if previous:
            parts.append(OSC8 + ST)
        lines.append("".join(parts))
    if return_overrides:
        return overrides, choices
    return "\n".join(lines), choices


def native_helper():
    from kitty.constants import config_dir, version
    # This helper is compiled against the pinned upstream native APIs.
    if tuple(version)[:3] != (0, 50, 0):
        return None
    candidate = os.environ.get("KITTY_NATIVE_HINTS_BIN", os.path.join(config_dir, "hint-native"))
    return candidate if os.path.isfile(candidate) and os.access(candidate, os.X_OK) else None


def native_request(window, hint_type):
    """Snapshot the actual Kitty configuration and source pane before routing."""
    from kitty.fast_data_types import get_options

    opts = get_options()
    screen = window.screen
    profile = screen.color_profile
    ansi = window.as_text(as_ansi=True, add_wrap_markers=True)
    if "\x1b]66;" in ansi or "\t" in ansi:
        return None
    return {"ANSI": ansi, "Cols": screen.columns, "Rows": screen.lines, "Type": hint_type,
            "Foreground": int(profile.default_fg), "Background": int(profile.default_bg),
            "Target": int(opts.color0), "KeyBG": int(opts.selection_background),
            "KeyFG": int(opts.color3), "Accent": int(opts.url_color),
            "Colors": [int(profile.as_color((i << 8) | 1)) for i in range(256)],
            "DimOpacity": float(opts.dim_opacity),
            "URLPrefixes": ",".join(opts.url_prefixes),
            "URLExcludedCharacters": "".join(f"\\U{ord(ch):08x}" for ch in opts.url_excluded_characters)}


def native_payload(request):
    return json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode()


def native_overlay(boss, window, helper, request, callback=None):
    from kitty.tabs import SpecialWindow
    from kitty.window import CwdRequest
    from kitty.constants import config_dir

    tab = window.tabref()
    if tab is None:
        return None
    overlay = tab.new_special_window(
        SpecialWindow([helper], stdin=native_payload(request),
                      cwd=CwdRequest(window).cwd_of_child or window.cwd_of_child,
                      override_title="Choose URL" if request["Type"] == "url" else "Choose text",
                      overlay_for=window.id, overlay_behind=True,
                      env={"KITTEN_RUNNING_AS_UI": "1", "KITTY_CONFIG_DIRECTORY": config_dir}),
        copy_colors_from=window)

    def selected(data, window_id, current_boss):
        if callback is not None:
            callback(data, window_id, current_boss)
        elif data.get("match"):
            open_native_hint([], data, window_id, current_boss)
        if data.get("error"):
            current_boss.show_error("Native hints", data["error"])

    overlay.actions_on_close.append(partial(boss.on_kitten_finish, window.id, selected, default_data={}))
    overlay.open_url_handler = on_mark_clicked
    return overlay


def request_receiver(boss, window, target_window_id, on_ready, on_timeout):
    """Keep the terminal connection and receiver lifecycle in the Kitty adapter."""
    previous_marker = at_cursor(window)
    window.write_to_child(REQUEST)
    started = time.monotonic()
    deadline = started + 5

    def wait(timer):
        nonlocal deadline
        if boss.window_id_map.get(target_window_id) is not window:
            remove_timer(timer)
            return
        marker = at_cursor(window)
        if marker == FAILED:
            remove_timer(timer)
            return
        if marker == BUILDING:
            deadline = started + 300
        ready = READY.fullmatch(marker) if marker != previous_marker else None
        if not ready and time.monotonic() < deadline:
            return
        remove_timer(timer)
        if not ready:
            on_timeout()
            return
        ticket = ready[1]
        left, top, width, height, receiver_x, receiver_y = map(int, ready.groups()[1:])
        cursor = window.screen.cursor
        rect = (max(0, left + cursor.x - receiver_x), max(0, top + cursor.y - receiver_y), width, height)
        window.write_to_child(b"!")
        on_ready(marker, ticket, rect, marker.startswith("dotfiles-hints-v2://"))

    add_timer(wait, 0.05, True)


def deliver_selection(boss, window, window_id, marker, ticket, data, image):
    """Only send a receiver-scoped selection over the original terminal connection."""
    matches = data.get("match", [])
    target = matches[0] if matches else None
    if boss.window_id_map.get(window_id) is window and at_cursor(window) == marker:
        payload = base64.urlsafe_b64encode(json.dumps(image).encode()).rstrip(b"=") if image else b""
        window.write_to_child(ticket.encode() + payload + b".")
    elif image:
        boss.show_error("Open file", "The source pane changed. Select the file again.")
    if target and image is None:
        open_native_hint([], data, window_id, boss)


def try_native(boss, window, target_window_id, hint_type):
    helper = native_helper()
    if not helper:
        return False
    request = native_request(window, hint_type)
    if request is None:
        return False
    if hint_type == "url" or not in_zellij(window):
        return native_overlay(boss, window, helper, request) is not None

    # The compiled helper owns file eligibility. The probe avoids waiting for
    # an unmanaged receiver when the source contains only web links.
    probe = {**request, "Pane": {"Left": 0, "Top": 0, "Width": request["Cols"],
                                "Height": request["Rows"], "Files": True}}
    try:
        result = subprocess.run([helper, "--probe"], input=native_payload(probe),
                                capture_output=True, check=True, timeout=2)
        needs_receiver = json.loads(result.stdout)
        if type(needs_receiver) is not bool:
            raise ValueError("Expected native hint eligibility boolean")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Native hint probe failed; using compatibility path: {error}", file=sys.stderr)
        return False
    if not needs_receiver:
        return native_overlay(boss, window, helper, request) is not None

    def fallback():
        native_overlay(boss, window, helper, request)

    def ready(marker, ticket, rect, files):
        left, top, width, height = rect
        routed = {**request, "Pane": {"Left": left, "Top": top, "Width": width,
                                     "Height": height, "Files": files}}

        def selected(data, window_id, current_boss):
            groupdicts = data.get("groupdicts") or []
            image = groupdicts[0].get("file") if groupdicts and isinstance(groupdicts[0], dict) else None
            deliver_selection(current_boss, window, window_id, marker, ticket, data, image)

        if native_overlay(boss, window, helper, routed, selected) is None:
            deliver_selection(boss, window, target_window_id, marker, ticket, {}, None)

    request_receiver(boss, window, target_window_id, ready, fallback)
    return True


def launch_overlay(boss, window, snapshot, embedded=False, **kwargs):
    """Use a lightweight local session; retain Kitty's embedded kitten fallback."""
    from kitty.utils import which
    from kitty.tabs import SpecialWindow
    from kitty.window import CwdRequest
    from kitty.constants import config_dir

    # No daemon, worker or persistent process. The normal Python installation
    # used by the dotfiles is sufficient, and the embedded kitten remains usable.
    python = None if embedded else which("python3")
    helper = os.path.join(config_dir, "hint_session.py")
    tab = window.tabref() if python and os.path.isfile(helper) else None
    if tab is None:
        return boss.run_kitten_with_metadata(
            "hint_overlay.py", (), window=window, input_data=encode_snapshot(snapshot), **kwargs)

    overlay = tab.new_special_window(
        SpecialWindow([python, "-I", "-S", helper], stdin=encode_session(snapshot),
                      cwd=CwdRequest(window).cwd_of_child or window.cwd_of_child,
                      override_title="Choose URL" if snapshot["type"] == "url" else "Choose text",
                      overlay_for=window.id, overlay_behind=True),
        copy_colors_from=window)
    overlay.actions_on_close.append(partial(boss.on_kitten_finish, window.id,
                                            kwargs["custom_callback"], default_data=kwargs.get("default_data")))
    overlay.open_url_handler = on_mark_clicked
    return overlay


def show_hints(boss, window, hint_type="hyperlink", *, rows=None, snapshot=None, overrides=None, embedded=False, **kwargs):
    if rows is None:
        rows = capture(window.screen)
    if snapshot is None:
        snapshot = source_snapshot(window.screen, rows)
    snapshot = dict(snapshot)
    snapshot["type"] = hint_type
    snapshot["marks"] = (raw_url_marks(rows, snapshot["wrapped"]) if hint_type == "url"
                         else hyperlink_marks(rows, overrides))
    kwargs.setdefault("default_data", {})
    if "custom_callback" not in kwargs:
        def selected(data, window_id, current_boss):
            if data.get("match"):
                open_native_hint([], data, window_id, current_boss)
        kwargs["custom_callback"] = selected
    return launch_overlay(boss, window, snapshot, embedded=embedded, **kwargs)


def at_cursor(window):
    cursor = window.screen.cursor
    return window.screen.hyperlink_at(cursor.x, cursor.y) or ""


def main(args):
    pass


@result_handler(no_ui=True)
def handle_result(args, answer, target_window_id, boss):
    window = boss.window_id_map.get(target_window_id)
    if window is None:
        return
    hint_type = args[1] if len(args) > 1 else "hyperlink"
    if hint_type not in ("hyperlink", "url"):
        raise ValueError("Expected hyperlink or url hint selection")
    if not any(x in args[2:] for x in ("--embedded", "--python")):
        if try_native(boss, window, target_window_id, hint_type):
            return
    if hint_type == "url" or not in_zellij(window):
        show_hints(boss, window, hint_type, embedded="--embedded" in args[2:])
        return

    rows = capture(window.screen)
    snapshot = source_snapshot(window.screen, rows)
    if not has_file_hints(rows):
        show_hints(boss, window, rows=rows, snapshot=snapshot)
        return
    def fallback():
        show_hints(boss, window, rows=rows, snapshot=snapshot)

    def ready(marker, ticket, rect, files):
        overrides, choices = picker_input(rows, rect, ticket, files=files, return_overrides=True)

        def selected(data, window_id, current_boss):
            matches = data.get("match", [])
            target = matches[0] if matches else None
            deliver_selection(current_boss, window, window_id, marker, ticket, data, choices.get(target))

        show_hints(boss, window, rows=rows, snapshot=snapshot, overrides=overrides,
                   custom_callback=selected, default_data={})

    request_receiver(boss, window, target_window_id, ready, fallback)
