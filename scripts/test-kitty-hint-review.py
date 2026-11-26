"""Capture normal and URL-hint frames of a representative terminal under a selected preset."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import time

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]


def until(label, predicate):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
        time.sleep(.1)
    raise AssertionError(f"Timed out waiting for {label}")


def main():
    destination = Path(os.environ["KITTY_HINT_ARTIFACTS"])
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kitty-hint-review-") as temp:
        work = Path(temp)
        home = work / "home"
        home.mkdir()
        env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(home / ".cache"), "XDG_DATA_HOME": str(home / ".local/share")}
        subprocess.run(["make", "-s", "kitty-config"], cwd=ROOT, env=env, check=True)
        theme = os.environ.get("KITTY_HINT_THEME", "nord")
        generated = work / "theme"
        subprocess.run([sys.executable, str(ROOT / "scripts/theme.py"), "--theme", theme,
                        "--output-dir", str(generated)], cwd=ROOT, env=env, check=True)
        # Resolve the same generated palette used by the installed theme, in
        # an isolated review config. Never modify the checkout or active preset.
        config = home / ".config/kitty/kitty.conf"
        original = config.read_text()
        config.unlink()
        config.write_text(original.replace("include ../dotfiles/theme/kitty.conf",
                                           f"include {generated / 'kitty.conf'}"))
        palette = dict(line.split() for line in (generated / "kitty.conf").read_text().splitlines()
                       if line and not line.startswith("#"))
        helper = Path(os.environ["KITTY_NATIVE_HINTS_BIN"]).resolve()
        installed = home / ".local/bin/hint-native"
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.symlink_to(helper)
        env["PATH"] = str(installed.parent) + os.pathsep + env["PATH"]
        socket = "unix:" + str(work / "kitty.sock")

        def command(*args):
            return subprocess.check_output(args, env=env, text=True, stderr=subprocess.DEVNULL, timeout=5)

        def remote(*args):
            return command("kitten", "@", "--to", socket, *args)

        def windows():
            return [w for oswin in json.loads(remote("ls")) for tab in oswin["tabs"] for w in tab["windows"]]

        def capture(name, xid):
            geometry = dict(line.split("=", 1) for line in command(
                "xdotool", "getwindowgeometry", "--shell", xid).splitlines())
            x, y, width, height = (int(geometry[k]) for k in ("X", "Y", "WIDTH", "HEIGHT"))
            # Allow the last committed GPU frame to reach X11 before reading pixels.
            time.sleep(.3)
            image = ImageGrab.grab().convert("RGB").crop((x, y, x + width, y + height))
            image.save(destination / name)
            return image

        with (work / "kitty.log").open("w") as log:
            app = subprocess.Popen(["kitty", "--listen-on", socket,
                "-o", "allow_remote_control=socket-only", "-o", "linux_display_server=x11",
                "-o", "initial_window_width=82c", "-o", "initial_window_height=27c",
                "-o", "remember_window_size=no", "--directory", str(ROOT),
                "python3", str(ROOT / "scripts/fixtures/kitty-hint-review.py")],
                env=env, stdout=log, stderr=log)
            try:
                until("representative source", lambda: "21 deletions" in remote("get-text"))
                xid = command("xdotool", "search", "--onlyvisible", "--class", "kitty").splitlines()[-1]
                command("xdotool", "windowfocus", "--sync", xid)
                source = remote("get-text", "--ansi")
                capture("review-normal.png", xid)
                command("xdotool", "key", "--clearmodifiers", "ctrl+shift+e")
                overlay_id = until("styled URL overlay", lambda: next(
                    (w["id"] for w in windows() if w["title"] == "Choose URL"), None))
                until("rendered URL links", lambda: "a github.com/lanej/dotfiles/pull/429"
                      in remote("get-text", "--match", f"id:{overlay_id}"))
                if "https://" in remote("get-text", "--match", f"id:{overlay_id}"):
                    raise AssertionError("An active HTTPS scheme remained visible")
                expected_helper = os.environ.get("KITTY_NATIVE_HINTS_BIN")
                if expected_helper:
                    actual = next(w for w in windows() if w["id"] == overlay_id)
                    if not actual.get("cmdline") or Path(actual["cmdline"][0]).resolve() != Path(expected_helper).resolve():
                        raise AssertionError(f"Expected native Go helper, found {actual.get('cmdline')}")
                image = capture("review-url-hints.png", xid)
                counts = dict((color, count) for count, color in image.getcolors(image.width * image.height))
                def rgb(name):
                    value = palette[name]
                    return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))
                # Scheme badge, unchanged target hues, target background and
                # key background must originate in the selected preset.
                for color in (rgb("color6"), rgb("color2"), rgb("color0"), rgb("selection_background")):
                    if counts.get(color, 0) < 5:
                        raise AssertionError(f"Representative frame is missing rendered color {color}")
                command("xdotool", "key", "--clearmodifiers", "Escape")
                until("unchanged source after cancellation", lambda:
                    all(w["title"] != "Choose URL" for w in windows()) and remote("get-text", "--ansi") == source)
            except Exception:
                print((work / "kitty.log").read_text()[-6000:])
                try:
                    print("Overlay state:", [(w["id"], w["title"], w.get("cmdline")) for w in windows()])
                    print("Active screen:", repr(remote("get-text", "--ansi")))
                except (OSError, subprocess.SubprocessError):
                    pass
                raise
            finally:
                app.terminate()
                try:
                    app.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait()


if __name__ == "__main__":
    main()
