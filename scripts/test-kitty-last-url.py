"""Exercise the kitten entrypoint using kitty's real screen parser."""

from pathlib import Path
from types import SimpleNamespace
import importlib.util

from kitty.fast_data_types import Screen, set_options
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


def main():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("open_last_url", root / "kitty/open_last_url.py")
    kitten = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kitten)
    set_options(defaults)
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
    print("PASS: the shortcut opens the complete last padded URL and honors terminal hyperlink targets.")


if __name__ == "__main__":
    main()
