"""Keep Kitty's native hint picker and open image selections on their Zellij host."""
import base64
import json
import os
import re
import time
from urllib.parse import unquote, urlsplit

from kittens.hints.main import handle_result as open_native_hint
from kittens.tui.handler import result_handler
from kitty.fast_data_types import add_timer, remove_timer


EXT = r"\.(?:png|jpe?g|webp|gif|bmp|tiff?|avif|ico|svg|heic|jxl)"
IMAGE_END = re.compile(EXT + "$", re.I)
POSSIBLE_IMAGE = re.compile(EXT + r"|file:|\.[a-z]{0,3}[ \t]*(?:[\r\n│┃]|$)", re.I)
TOKEN = r"""[^\s<>"'`()\[\]{},;│┃]+"""
PATH = re.compile(
    rf"""(?P<quote>["'`])(?P<quoted>[^\n"'`]+?{EXT})(?P=quote)"""
    rf"""|\((?P<parenthesized>[^()\n]+?{EXT})\)"""
    rf"""|(?P<bare>{TOKEN}?{EXT})(?=\.(?!\w)|$|[\s,;:!?'"`)\]}}>│┃])""", re.I)
READY = re.compile(r"dotfiles-hints://([0-9a-f]{32})" + r"/(\d+)" * 6)
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


def file_image(url):
    if not url.startswith("file:"):
        return None
    try:
        target = urlsplit(url)
        path = unquote(target.path)
        if path.startswith("/") and IMAGE_END.search(path):
            return {"path": path, "host": target.hostname or ""}
    except ValueError:
        pass
    return None


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
                     and last_word[-1] not in ")]}\"'`,;")
    return "".join(chars), positions


def picker_input(rows, rect, ticket):
    left, top, width, height = rect
    choices, marks, tokens = {}, {}, {}

    def mark(image):
        key = (image["path"], image.get("host", ""))
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
        image = file_image(path) if "://" in path else {"path": path}
        if not image:
            continue
        token = mark(image)
        # Hint the first visible fragment once, even if the full path wraps.
        row = positions[start][1]
        for point in positions[start:end]:
            if point is None or point[1] != row:
                break
            marks[point] = token

    lines = []
    for y, row in enumerate(rows):
        previous, parts = "", []
        for x, (char, url) in enumerate(row):
            if not char:
                continue
            if url and top <= y < top + height and left <= x < left + width:
                image = file_image(url)
                if image:
                    url = mark(image)
            url = marks.get((x, y), url)
            if url != previous:
                parts.append(OSC8 + url + ST)
                previous = url
            parts.append(char)
        if previous:
            parts.append(OSC8 + ST)
        lines.append("".join(parts))
    return "\n".join(lines), choices


def show_hints(boss, window, hint_type="hyperlink", **kwargs):
    overlay = boss.run_kitten_with_metadata(
        "hints", ["--type", hint_type, "--alphabet", "asdfghjkl", "--hints-offset", "0",
                  "--ascending", "--prefix-free", "--hints-foreground-color", "#2E3440",
                  "--hints-background-color", "#B48EAD", "--hints-text-color", "#ECEFF4"],
        window=window, **kwargs)
    if overlay is not None:
        overlay.set_dynamic_color(10, "#4C566A")


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
    if hint_type == "url" or not in_zellij(window):
        show_hints(boss, window, hint_type)
        return

    original = window.as_text(as_ansi=True, add_wrap_markers=True)
    if not POSSIBLE_IMAGE.search(original):
        show_hints(boss, window)
        return
    rows = capture(window.screen)
    previous_marker = at_cursor(window)
    window.write_to_child(REQUEST)
    deadline = time.monotonic() + 5

    def wait(timer):
        if boss.window_id_map.get(target_window_id) is not window:
            remove_timer(timer)
            return
        marker = at_cursor(window)
        ready = READY.fullmatch(marker) if marker != previous_marker else None
        if not ready and time.monotonic() < deadline:
            return
        remove_timer(timer)
        if not ready:
            # Older or unmanaged remote sessions still get Kitty's ordinary hyperlink picker.
            show_hints(boss, window, input_data=original)
            return
        ticket = ready[1]
        left, top, width, height, receiver_x, receiver_y = map(int, ready.groups()[1:])
        # Guest Zellij coordinates can start inside an outer terminal pane.
        cursor = window.screen.cursor
        rect = (max(0, left + cursor.x - receiver_x), max(0, top + cursor.y - receiver_y), width, height)
        display, choices = picker_input(rows, rect, ticket)
        window.write_to_child(b"!")

        def selected(data, window_id, current_boss):
            matches = data.get("match", [])
            target = matches[0] if matches else None
            image = choices.get(target)
            if current_boss.window_id_map.get(window_id) is window and at_cursor(window) == marker:
                # Only ASCII data without a command terminator crosses the terminal connection.
                payload = base64.urlsafe_b64encode(json.dumps(image).encode()).rstrip(b"=") if image else b""
                window.write_to_child(ticket.encode() + payload + b".")
            elif image:
                current_boss.show_error("Image preview", "The source pane changed. Select the image again.")
            if target and image is None:
                open_native_hint([], data, window_id, current_boss)

        show_hints(boss, window, input_data=display, custom_callback=selected, default_data={})

    add_timer(wait, 0.05, True)
