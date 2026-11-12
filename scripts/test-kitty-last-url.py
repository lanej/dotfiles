"""Exercise the kitten entrypoint using kitty's real screen parser."""

from pathlib import Path
from types import SimpleNamespace
import importlib.util

from kitty.fast_data_types import Screen, set_options, GLFW_MOD_SUPER, GLFW_MOD_SHIFT
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
    print("PASS: Cmd+Shift+O opens exact OSC 8 destinations; Cmd+Shift+U invokes the hint picker.")


if __name__ == "__main__":
    main()
