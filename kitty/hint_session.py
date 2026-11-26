"""Minimal, on-demand Kitty overlay session; no Kitty/Python GUI imports."""
import base64
import json
import os
import re
import select
import signal
import sys
import termios
import tty

# The script may be reached through a configuration symlink. Isolated Python
# intentionally does not add the script directory to sys.path.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from hint_renderer import ALPHABET, FrameRenderer, active_cells, decode_session


ESC = b"\x1b"
READY = ESC + b"P@kitty-overlay-ready|" + ESC + b"\\"
CSI = re.compile(rb"\x1b\[([0-?]*)([ -/]*)([@-~])")
MOUSE = re.compile(rb"<(\d+);(\d+);(\d+)")
PASTE_END = b"\x1b[201~"


class Input:
    """Decode only the events the picker consumes; discard other sequences."""
    def __init__(self):
        self.pending = b""
        self.pasting = False

    def feed(self, data):
        self.pending += data
        events = []
        while self.pending:
            buf = self.pending
            if self.pasting:
                i = buf.find(PASTE_END)
                if i < 0:
                    self.pending = buf[-(len(PASTE_END) - 1):]
                    break
                self.pending = buf[i + len(PASTE_END):]
                self.pasting = False
                continue
            if buf[0] != 27:
                self.pending = buf[1:]
                if buf[:1] in (b"\x03", b"\x04"):
                    events.append(("cancel", None))
                elif buf[:1] in (b"\x7f", b"\x08"):
                    events.append(("backspace", None))
                elif chr(buf[0]) in ALPHABET:
                    events.append(("key", chr(buf[0])))
                continue
            if len(buf) == 1:
                break
            if buf.startswith(b"\x1bP"):
                end = buf.find(b"\x1b\\", 2)
                if end < 0:
                    break
                self.pending = buf[end+2:]
                if buf.startswith(b"\x1bP@kitty-cmd"):
                    try:
                        response = json.loads(buf[len(b"\x1bP@kitty-cmd"):end])
                        if response.get("Type") == "mark_activated":
                            events.append(("mark", response.get("Mark")))
                    except (ValueError, AttributeError):
                        pass
                continue
            if buf.startswith(b"\x1b["):
                match = CSI.match(buf)
                if match is None:
                    # Retain fragmented CSI; discard malformed or oversized input.
                    if len(buf) < 128 and all(32 <= c <= 63 for c in buf[2:]):
                        break
                    self.pending = buf[2:]
                    continue
                self.pending = buf[match.end():]
                params, intermediate, final = match.groups()
                if intermediate:
                    continue
                if final == b"~" and params == b"200":
                    self.pasting = True
                elif final in (b"M", b"m"):
                    mouse = MOUSE.fullmatch(params)
                    if mouse:
                        button, x, y = map(int, mouse.groups())
                        if button & 0b11100011 == 0:
                            events.append(("press" if final == b"M" else "release", (x-1, y-1)))
                elif final == b"u":
                    # Kitty keyboard protocol, disambiguation only (flag 1).
                    fields = params.split(b";")
                    try:
                        code = int(fields[0].split(b":")[0])
                        mods = int(fields[1].split(b":")[0]) if len(fields) > 1 else 1
                        action = fields[1].split(b":")[1:] if len(fields) > 1 else []
                    except ValueError:
                        continue
                    if action == [b"3"]:
                        continue
                    if code == 27 or (mods == 5 and code in (99, 100)):
                        events.append(("cancel", None))
                    elif code in (8, 127) and mods == 1:
                        events.append(("backspace", None))
                    elif mods == 1 and 0 <= code < 128 and chr(code) in ALPHABET:
                        events.append(("key", chr(code)))
                continue
            if buf.startswith(b"\x1bO"):
                if len(buf) < 3:
                    break
                self.pending = buf[3:]
                continue
            # Alt-modified characters are not hint keystrokes.
            self.pending = buf[2:]
        return events

    def expire(self):
        # Legacy Escape, if sent before the keyboard protocol was enabled.
        if self.pending == ESC:
            self.pending = b""
            return [("cancel", None)]
        self.pending = b""
        return []


def result(model, index):
    return {"match": [model["marks"][index]["target"]], "groupdicts": [{}],
            "programs": [], "multiple_joiner": "auto", "customize_processing": "",
            "type": model["type"], "extra_cli_args": [], "cwd": os.getcwd()}


def write_all(fd, data):
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


class SessionEnded(Exception):
    pass


def end_session(*_):
    raise SessionEnded


def main():
    model = decode_session(sys.stdin.buffer.read())
    if not model["marks"]:
        return
    renderer = FrameRenderer(model)
    codes = renderer.codes
    prefix = ""
    parser = Input()
    pressed = None
    fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    original = termios.tcgetattr(fd)
    selected = None
    # Match the existing behavior: resize closes the immutable snapshot.
    for sig in (signal.SIGWINCH, signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(sig, end_session)

    def draw():
        frame = renderer.draw(prefix)
        if frame:
            write_all(fd, b"\x1b[?2026h" + frame.encode("utf-8") + b"\x1b[?2026l")

    try:
        tty.setraw(fd, termios.TCSANOW)
        # An independent overlay window owns these modes, never the source.
        write_all(fd, b"\x1b[?25l\x1b[?7l\x1b[>1u\x1b[?2004h\x1b[?1000h\x1b[?1006h")
        draw()
        write_all(fd, READY)
        while selected is None:
            timeout = .025 if parser.pending and not parser.pasting else None
            readable, _, _ = select.select([fd], [], [], timeout)
            if readable:
                data = os.read(fd, 4096)
                if not data:
                    break
                events = parser.feed(data)
            else:
                events = parser.expire()
            changed = False
            for kind, value in events:
                if kind == "cancel":
                    raise SessionEnded
                if kind == "backspace":
                    prefix = prefix[:-1]
                    changed = True
                elif kind == "key":
                    candidate = prefix + value
                    matches = [i for i, code in enumerate(codes) if code.startswith(candidate)]
                    if matches:
                        prefix = candidate
                        changed = True
                        if codes[matches[0]] == prefix:
                            selected = matches[0]
                            break
                elif kind == "mark":
                    if isinstance(value, int) and 0 <= value < len(codes) and codes[value].startswith(prefix):
                        selected = value
                        break
                elif kind == "press":
                    pressed = value
                elif kind == "release":
                    if pressed == value:
                        marked, _, _ = active_cells(model, prefix)
                        selected = marked.get(value)
                        if selected is not None:
                            break
                    pressed = None
            if changed and selected is None:
                draw()
    except SessionEnded:
        pass
    finally:
        # Restore tty modes even on cancellation or resize. The source is untouched.
        try:
            if selected is not None:
                payload = base64.b85encode(json.dumps(result(model, selected)).encode("utf-8"))
                write_all(fd, b"\x1bP@kitty-kitten-result|" + payload + b"\x1b\\")
            termios.tcsetattr(fd, termios.TCSANOW, original)
        except OSError:
            pass
        os.close(fd)


if __name__ == "__main__":
    main()
