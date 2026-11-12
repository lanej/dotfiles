"""Drive the actual Kitty shortcut, Zellij split, and icat pixels on an X11 display."""
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import zlib

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
IMAGE = Path("docs/screenshots/plan-viewer/fixture-running-overview.png")
URL = "https://example.invalid/release?q=exact"


def png(path, color):
    def chunk(kind, contents):
        return struct.pack(">I", len(contents)) + kind + contents + struct.pack(">I", zlib.crc32(kind + contents))
    path.parent.mkdir(parents=True, exist_ok=True)
    pixels = (b"\0" + bytes(color) * 120) * 96
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 120, 96, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


def until(label, predicate, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {label}")


def exercise(work):
    home = work / "home"
    home.mkdir()
    session = "image-hints-test"
    repo, source = work / "checkout", work / "treehouse-14"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-qm", "fixture", "--allow-empty"], check=True)
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(source)], check=True)
    png(repo / IMAGE, (20, 60, 240))
    png(source / IMAGE, (245, 35, 40))
    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
           "XDG_CACHE_HOME": str(home / ".cache"), "XDG_DATA_HOME": str(home / ".local/share"),
           "XDG_RUNTIME_DIR": str(work / "run"), "ZELLIJ_SOCKET_DIR": str(work / "run"),
           "PATH": str(work / "bin") + os.pathsep + os.environ["PATH"]}
    (work / "run").mkdir(mode=0o700)
    (work / "bin").mkdir()
    helper = os.environ.get("IMAGE_HINTS_HELPER", str(ROOT / "zellij/target/debug/lane-zellij"))
    (work / "bin/zellij-helper").symlink_to(Path(helper).resolve(strict=True))
    subprocess.run(["make", "-s", "kitty-config", "zellij-config"], cwd=ROOT, env=env, check=True)
    config = work / "config.kdl"
    # Exercise the repository's actual keybindings without needing unrelated status-bar plugins.
    bindings = (ROOT / "zellij/config.kdl").read_text().split("keybinds clear-defaults=true", 1)[1]
    config.write_text('default_mode "locked"\nshow_startup_tips false\nshow_release_notes false\n'
                      'pane_frame_style "full"\nkeybinds clear-defaults=true' + bindings)
    fixture = work / "source.py"
    fixture.write_text('''import os, signal, time
time.sleep(.4)
width = os.get_terminal_size().columns
print("Synthetic preview (docs/screenshots/plan-viewer/fixture-".rjust(width - 2))
print("  running-overview.png).")
print("\\033]8;;''' + URL + '''\\033\\\\release notes\\033]8;;\\033\\\\", flush=True)
signal.pause()
''')
    layout = work / "layout.kdl"
    layout.write_text('layout {\n    pane command="python3" cwd=' + json.dumps(str(source)) +
                      ' { args ' + json.dumps(str(fixture)) + '; }\n}\n')
    opener = work / "bin/open-hint"
    opener.write_text('#!/bin/sh\nprintf "%s" "$1" > "$HOME/opened-url"\n')
    opener.chmod(0o755)
    socket = "unix:" + str(work / "kitty.sock")
    def command(*args):
        return subprocess.check_output(args, env=env, text=True, stderr=subprocess.DEVNULL, timeout=6)
    def remote(*args):
        return command("kitten", "@", "--to", socket, *args)
    def panes():
        return json.loads(command("zellij", "--session", session, "action", "list-panes", "--json"))
    def key(name):
        command("xdotool", "key", "--clearmodifiers", name)
    def hint(fragment):
        def find():
            for os_window in json.loads(remote("ls")):
                for tab in os_window["tabs"]:
                    for window in tab["windows"]:
                        if window["title"] == "Choose text":
                            output = remote("get-text", "--ansi", "--match", f'id:{window["id"]}')
                            for line in output.splitlines():
                                if fragment in line:
                                    marks = re.findall(r"\x1b\]8;[^;]*;mark:(\d+)", line.split(fragment)[0])
                                    if marks:
                                        return marks[-1]
            return None
        key("super+shift+u")
        key(until("a native Kitty hint for " + fragment, find))

    log = work / "kitty.log"
    with log.open("w") as output:
        app = subprocess.Popen(["kitty", "--listen-on", socket, "-o", "allow_remote_control=socket-only",
                                "-o", "linux_display_server=x11", "-o", "allow_hyperlinks=yes",
                                "-o", "open_url_with=" + str(opener), "-o", "initial_window_width=100c",
                                "-o", "initial_window_height=32c", "-o", "remember_window_size=no",
                                "--directory", str(repo), "zellij", "--config", str(config),
                                "--session", session, "--new-session-with-layout", str(layout)],
                               env=env, stdout=output, stderr=output)
        try:
            until("the source pane", lambda: any(p.get("pane_cwd") == str(source) for p in panes()))
            until("the original preview", lambda: "running-overview.png" in remote("get-text"))
            # Xvfb has no window manager to assign keyboard focus.
            xid = command("xdotool", "search", "--onlyvisible", "--class", "kitty").splitlines()[-1]
            command("xdotool", "windowfocus", "--sync", xid)
            hint("screenshots/plan-viewer")
            def preview_has_focus():
                current = panes()
                original = next((p for p in current if str(fixture) in (p.get("terminal_command") or "")), None)
                return original and any(
                    str(source / IMAGE) in (p.get("terminal_command") or "") and p["is_focused"]
                    and not p["is_floating"] and p["tab_id"] == original["tab_id"]
                    and p["pane_x"] >= original["pane_x"] + original["pane_columns"] for p in current)
            until("the focused icat split beside the originating worktree", preview_has_focus)
            def red_pixels():
                image = ImageGrab.grab().convert("RGB")
                colors = image.getcolors(image.width * image.height)
                return any(color == (245, 35, 40) and count >= 200 for count, color in colors)
            until("the source worktree's red image pixels", red_pixels)
            key("q")
            until("the preview pane to close", lambda: not any("icat" in (p.get("terminal_command") or "") for p in panes()))
            hint("lease notes")
            until("the exact hyperlink at the desktop opener", lambda: (home / "opened-url").read_text() == URL)
            print("PASS: Cmd+Shift+U selected the wrapped PNG, displayed the correct worktree's pixels, and opened the native web link.")
        except Exception:
            print(log.read_text()[-3200:], file=sys.stderr)
            try:
                print("Zellij panes:", command("zellij", "--session", session, "action", "list-panes", "--json"), file=sys.stderr)
            except subprocess.SubprocessError:
                pass
            try:
                for os_window in json.loads(remote("ls")):
                    for tab in os_window["tabs"]:
                        for window in tab["windows"]:
                            print("Kitty window:", window["title"], file=sys.stderr)
                            print(repr(remote("get-text", "--ansi", "--match", f'id:{window["id"]}'))[-5000:], file=sys.stderr)
            except (subprocess.SubprocessError, ValueError):
                pass
            raise
        finally:
            subprocess.run(["zellij", "delete-session", session, "--force"], env=env, capture_output=True)
            app.terminate()
            try: app.wait(timeout=3)
            except subprocess.TimeoutExpired: app.kill(); app.wait()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="image-hints-") as directory:
        exercise(Path(directory))
