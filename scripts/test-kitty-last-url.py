"""Exercise the kitten entrypoint using kitty's real screen parser."""

from pathlib import Path
from types import SimpleNamespace
import importlib.util

from kitty.fast_data_types import Screen, set_options, GLFW_MOD_SUPER, GLFW_MOD_SHIFT, GLFW_MOD_CONTROL
from kitty.config import load_config
from kitty.options.types import defaults
from kitty.window import Window


def parse_bytes(screen, data):
    data = memoryview(data)
    while data:
        written = screen.test_commit_write_buffer(data, screen.test_create_write_buffer())
        data = data[written:]
        screen.test_parse_written_data()


def expect_url(opened, expected):
    # Kitty embeds optimized Python, which removes assert statements.
    if not opened or opened[-1] != expected:
        raise AssertionError(f"Expected {expected!r}; opened {opened!r}")


def check_image_hints(root):
    spec = importlib.util.spec_from_file_location("select_hint", root / "kitty/select_hint.py")
    picker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(picker)
    from kittens.hints.main import parse_hints_args
    # Exercise the current generated palette rather than Kitty factory defaults.
    set_options(load_config(str(root / "design-system/generated/kitty.conf")))
    source = SimpleNamespace(screen=Screen(None, 4, 60, 4))
    overlay = SimpleNamespace(screen=Screen(None, 4, 60, 4))
    overlay.set_dynamic_color = lambda code, value: Window.set_dynamic_color(overlay, code, value)
    calls = []

    def run_picker(name, args, **kwargs):
        options, extra = parse_hints_args(args)
        calls.append((name, options, extra, kwargs))
        return overlay

    boss = SimpleNamespace(run_kitten_with_metadata=run_picker, window_id_map={7: source})
    for kind in ("hyperlink", "url"):
        picker.show_hints(boss, source, kind)
        name, options, extra, kwargs = calls[-1]
        if (name != "hints" or options.type != kind or options.alphabet != "asdfghjkl"
                or options.hints_offset != 0 or not options.ascending or not options.prefix_free or extra
                or options.hints_text_color != "#ECEFF4"
                or options.hints_background_color != "#434C5E"
                or options.hints_foreground_color != "#EBCB8B"
                or options.hints_text_background_color != "#3B4252" or kwargs["window"] is not source):
            raise AssertionError("Native hints did not receive the home-row and Nord style")
        if int(overlay.screen.color_profile.default_fg) != 0x8C929D:
            raise AssertionError("Non-link text did not dim on the native overlay")
        if int(source.screen.color_profile.default_fg) == 0x8C929D:
            raise AssertionError("Hint styling changed the source pane")
    picker.handle_result(["select_hint.py", "url"], None, 7, boss)
    if calls[-1][1].type != "url":
        raise AssertionError("URL shortcut did not reach the styled native picker")

    screen = Screen(None, 12, 94, 12)
    width = 60
    first = "(docs/screenshots/plan-viewer/fixture-"
    rows = [
        first.rjust(width - 2) + "  │ other/worktree.png",
        "  running-overview.png).",
        '\x1b]8;;https://example.org/photo.png\x1b\\release notes\x1b]8;;\x1b\\',
        '\x1b]8;;file:///tmp/space%20here.png\x1b\\thumbnail\x1b]8;;\x1b\\',
        '測 "screenshots/a b.png"',
    ]
    parse_bytes(screen, "\r\n".join(rows).encode())
    display, choices = picker.picker_input(picker.capture(screen), (0, 0, width, 8), "example")
    paths = {entry["path"] for entry in choices.values()}
    expected = {"docs/screenshots/plan-viewer/fixture-running-overview.png",
                "/tmp/space here.png", "screenshots/a b.png"}
    if paths != expected or "https://example.org/photo.png" not in display:
        raise AssertionError(f"Wrong targets in the originating pane: {choices}")
    rendered = Screen(None, 12, 94, 12)
    parse_bytes(rendered, display.replace("\n", "\r\n").encode())
    if rendered.hyperlink_at(2, 2) != "https://example.org/photo.png":
        raise AssertionError("Web link labels must retain their exact OSC 8 destination")

    references = {
        "src/main.rs:42:7": {"path": "src/main.rs", "line": 42, "column": 7},
        "src/main.rs:42:7:": {"path": "src/main.rs", "line": 42, "column": 7},
        "file:///tmp/source%20file.lua#L8C3": {"path": "/tmp/source file.lua", "host": "", "line": 8, "column": 3},
        "file://localhost/tmp/a.py#L9-L12": {"path": "/tmp/a.py", "host": "localhost", "line": 9},
        "README": {"path": "README"},
        ".zshrc": {"path": ".zshrc"},
        "~/notes.md": {"path": "~/notes.md"},
        "https://example.org/code.rs:42": None,
        "file:///tmp/a%0Ab.rs": None,
    }
    for reference, expected in references.items():
        if picker.file_target(reference) != expected:
            raise AssertionError(f"Wrong file reference: {reference}: {picker.file_target(reference)}")
    source_files = Screen(None, 8, 80, 8)
    parse_bytes(source_files, b'src/main.rs:42:7\r\n"docs/design notes.md"\r\nREADME\r\n')
    _, files = picker.picker_input(picker.capture(source_files), (0, 0, 80, 8), "files")
    if {entry["path"] for entry in files.values()} != {"src/main.rs", "docs/design notes.md", "README"}:
        raise AssertionError(f"Missing source file hints: {files}")
    _, old_files = picker.picker_input(picker.capture(source_files), (0, 0, 80, 8), "old", files=False)
    if old_files:
        raise AssertionError("An older image-only receiver was offered source files")
    prose = Screen(None, 8, 80, 8)
    parse_bytes(prose, b'(see src/main.rs:42)\r\n(src/main.rs:42 and src/other.rs:7)\r\n')
    _, prose_files = picker.picker_input(picker.capture(prose), (0, 0, 80, 8), "prose")
    if {(entry["path"], entry.get("line")) for entry in prose_files.values()} != {("src/main.rs", 42), ("src/other.rs", 7)}:
        raise AssertionError(f"Parenthesized prose swallowed file references: {prose_files}")
    quoted = Screen(None, 8, 80, 8)
    parse_bytes(quoted, ('"docs/it\'s here.md"\r\n\'docs/a "quoted" file.rs\'\r\n').encode())
    _, quoted_files = picker.picker_input(picker.capture(quoted), (0, 0, 80, 8), "quoted")
    if {entry["path"] for entry in quoted_files.values()} != {"docs/it's here.md", 'docs/a "quoted" file.rs'}:
        raise AssertionError(f"Opposite quotes split a quoted filename: {quoted_files}")
    diagnostics = Screen(None, 8, 80, 8)
    parse_bytes(diagnostics, b'src/main.rs:42:7: error: failed\r\n"src/a b.rs":42:7\r\n`src/main.rs`:42\r\n')
    _, diagnostic_files = picker.picker_input(picker.capture(diagnostics), (0, 0, 80, 8), "diagnostics")
    if {(entry["path"], entry.get("line"), entry.get("column")) for entry in diagnostic_files.values()} != {
        ("src/main.rs", 42, 7), ("src/a b.rs", 42, 7), ("src/main.rs", 42, None)
    }:
        raise AssertionError(f"Diagnostic or quoted positions were lost: {diagnostic_files}")
    diagnostic_wrap = Screen(None, 8, 60, 8)
    parse_bytes(diagnostic_wrap, ("src/main.rs:42:7:".rjust(58) + "\r\n  error: failed\r\n").encode())
    _, diagnostic_wrap_files = picker.picker_input(picker.capture(diagnostic_wrap), (0, 0, 60, 8), "diagnostic-wrap")
    if list(diagnostic_wrap_files.values()) != [{"path": "src/main.rs", "line": 42, "column": 7}]:
        raise AssertionError(f"A wrapped diagnostic joined the error message to the filename: {diagnostic_wrap_files}")
    wrapped = Screen(None, 8, 60, 8)
    parse_bytes(wrapped, ("src/very-long-module-".rjust(58) + "\r\n  name.rs:42:7\r\n" +
                          "screenshots/overview.p".rjust(58) + "\r\n  ng\r\n").encode())
    _, wrapped_files = picker.picker_input(picker.capture(wrapped), (0, 0, 60, 8), "wrapped")
    if {entry["path"] for entry in wrapped_files.values()} != {"src/very-long-module-name.rs", "screenshots/overview.png"}:
        raise AssertionError(f"Wrapped references were split: {wrapped_files}")

    source.child = SimpleNamespace(foreground_processes=[{"cmdline": ["zellij"]}])
    source.user_vars = {}
    source.as_text = lambda **kwargs: "Preview ./fixture.png"
    sent, timers, removed = [], [], []
    source.write_to_child = sent.append
    picker.add_timer = lambda callback, interval, repeat: timers.append(callback)
    picker.remove_timer = removed.append
    now = [0.0]
    picker.time = SimpleNamespace(monotonic=lambda: now[0])
    parse_bytes(source.screen, b"\x1b[?1049h\r\nPreview ./fixture.png")

    def marker(value):
        parse_bytes(source.screen, ("\x1b[H\x1b]8;;" + value +
                                   "\x1b\\Updating helper\x1b]8;;\x1b\\\r").encode())

    for phase in ("building", "failed", "unmanaged"):
        now[0] = 0
        marker("")
        calls.clear()
        sent.clear()
        removed.clear()
        picker.handle_result(["select_hint.py"], None, 7, boss)
        if sent != [picker.REQUEST]:
            raise AssertionError("Image hints did not request their Zellij receiver")
        callback = timers[-1]
        now[0] = 6
        if phase == "building":
            marker(picker.BUILDING)
            callback(17)
            if calls or removed:
                raise AssertionError("A helper build fell back after the ordinary startup timeout")
            ticket = "a" * 32
            marker(f"dotfiles-hints://{ticket}/0/0/60/4/0/0")
            callback(17)
            if sent[-1] != b"!" or removed != [17]:
                raise AssertionError("The rebuilt receiver was not acknowledged")
            calls[-1][3]["custom_callback"]({}, 7, boss)
            if sent[-1] != ticket.encode() + b".":
                raise AssertionError("Cancelling after a build did not release the receiver")
        elif phase == "failed":
            marker(picker.FAILED)
            callback(17)
            if calls or removed != [17]:
                raise AssertionError("A build error must remain visible without a hint overlay")
        else:
            callback(17)
            if removed != [17] or calls[-1][3]["input_data"] != "Preview ./fixture.png":
                raise AssertionError("Unmanaged sessions lost the original five-second fallback")

    parse_bytes(source.screen, b"\x1b[2J\x1b[Hhttps://example.org/release")
    sent.clear()
    calls.clear()
    picker.handle_result(["select_hint.py"], None, 7, boss)
    if sent or not calls or calls[-1][1].type != "hyperlink":
        raise AssertionError("A web-only screen should open native hints without waiting for a receiver")


def main():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("open_last_url", root / "kitty/open_last_url.py")
    kitten = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kitten)
    set_options(defaults)
    check_image_hints(root)
    screen = Screen(None, 20, 90, 100)
    window = SimpleNamespace(screen=screen, cwd_of_child=str(root))
    window.as_text = lambda **kwargs: Window.as_text(window, **kwargs)
    opened = []
    boss = SimpleNamespace(window_id_map={7: window}, open_url=lambda url, **kwargs: opened.append(url))
    url = "https://example.org/a/long/path/" + "alphabeticonly" * 8
    parse_bytes(screen, f"{url} followed by prose\r\n".encode())
    kitten.handle_result([], None, 7, boss)
    expect_url(opened, url)
    parse_bytes(screen,
        (
            "  Open https://example.org/a/very/long/path/to/a/pull/           \r\n"
            "  123/files?diff=split&view=full                               \r\n"
            "  This paragraph must not become part of the URL.\r\n"
        ).encode(),
    )
    kitten.handle_result([], None, 7, boss)
    expect_url(opened, "https://example.org/a/very/long/path/to/a/pull/123/files?diff=split&view=full")
    # The exact OSC 8 target wins over a shortened URL used as the label.
    parse_bytes(screen, b"\x1b]8;;https://example.org/exact?q=yes!\x1b\\  https://example.org/short\x1b]8;;\x1b\\\r\n")
    kitten.handle_result([], None, 7, boss)
    expect_url(opened, "https://example.org/exact?q=yes!")
    parse_bytes(screen,
        (
            "\x1b]8;;https://github.com/owner/repo/pull/42\x1b\\\x1b[4mowner/repo#42\x1b[0m\x1b]8;;\x1b\\  "
            "\x1b]8;;https://github.com/owner/repo/commit/" + "a" * 40 +
            "\x1b\\\x1b[4mHead: aaaaaaaa\x1b[0m\x1b]8;;\x1b\\\r\n"
        ).encode(),
    )
    kitten.handle_result([], None, 7, boss)
    expect_url(opened, "https://github.com/owner/repo/commit/" + "a" * 40)
    options = load_config(str(root / "kitty/kittyconf"))
    keymap = options.keyboard_modes[""].keymap
    actions = {}
    for key, definitions in keymap.items():
        if key.mods == GLFW_MOD_SUPER | GLFW_MOD_SHIFT and key.key in (ord("o"), ord("u")):
            actions[chr(key.key)] = options.alias_map.resolve_aliases(definitions[-1].definition)
    if actions["o"][0].func != "kitten" or actions["o"][0].args != ("open_last_url.py",):
        raise AssertionError("Cmd+Shift+O no longer invokes the tested last-link opener")
    if actions["u"][0].func != "kitten" or actions["u"][0].args != ("select_hint.py",):
        raise AssertionError("Cmd+Shift+U does not invoke the link and image picker")
    url_actions = [options.alias_map.resolve_aliases(definitions[-1].definition)
                   for key, definitions in keymap.items()
                   if key.mods == GLFW_MOD_CONTROL | GLFW_MOD_SHIFT and key.key == ord("e")]
    if len(url_actions) != 1 or url_actions[0][0].args != ("select_hint.py", "url"):
        raise AssertionError("Ctrl+Shift+E does not invoke styled URL hints")
    print("PASS: Cmd+Shift+O opens exact OSC 8 destinations; Cmd+Shift+U invokes the hint picker.")


if __name__ == "__main__":
    main()
