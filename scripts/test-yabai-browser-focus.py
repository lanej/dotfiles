#!/usr/bin/env python3
"""Reload yabai's config and leave a visible test browser alone."""
from pathlib import Path
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="yabai-browser-focus-") as temporary:
        home = Path(temporary)
        (home / ".files").symlink_to(root)
        binary = home / "bin"
        binary.mkdir()
        python = shutil.which("python3")
        assert python, "Python is required."
        fixture = binary / "yabai"
        fixture.write_text(f"#!{python}\n" + r'''
from pathlib import Path
import json
import os
import sys

path = Path(os.environ["YABAI_FIXTURE"])
state = json.loads(path.read_text())
args = sys.argv[2:]
domain = args[0]
if domain == "signal":
    if args[1] == "--remove":
        state["signals"].pop(args[2], None)
    elif args[1] == "--add":
        options = dict(item.split("=", 1) for item in args[2:])
        state["signals"][options["label"]] = options
    else:
        raise AssertionError(args)
elif domain in ("rule", "config"):
    pass
elif domain == "query":
    if args == ["query", "--windows"]:
        print(json.dumps(state["windows"]))
    elif args == ["query", "--windows", "--window", "recent"]:
        print(json.dumps(state["windows"][0]))
    else:
        raise AssertionError(args)
elif domain == "window":
    window = next(w for w in state["windows"] if w["id"] == int(args[1]))
    assert args[2] == "--minimize", args
    window["is-minimized"] = True
    window["has-focus"] = False
else:
    raise AssertionError(args)
path.write_text(json.dumps(state))
''')
        fixture.chmod(0o755)
        native = binary / "osascript"
        native.write_text("#!/bin/sh\necho 'Unexpected native focus operation' >&2\nexit 1\n")
        native.chmod(0o755)
        state_path = home / "state.json"
        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{binary}:{os.environ['PATH']}",
            "YABAI_FIXTURE": str(state_path),
        }
        helper = shlex.quote(str(root / "bin/yabai-suppress-fullscreen-popup"))
        app_filter = "^(Chromium|Google Chrome for Testing)$"
        pending = f"{helper} window $YABAI_WINDOW_ID"
        state = {
            "signals": {
                "test-browser-created": {"event": "window_created", "app": app_filter, "action": pending},
                "test-browser-focused": {"event": "window_focused", "app": app_filter, "action": pending},
                "test-browser-activated": {
                    "event": "application_front_switched",
                    "action": f"{helper} application $YABAI_PROCESS_ID $YABAI_RECENT_PROCESS_ID",
                },
            },
            "windows": [
                {"id": 101, "pid": 10, "app": "kitty", "has-focus": False,
                 "is-minimized": False, "is-hidden": False},
                {"id": 201, "pid": 20, "app": "Google Chrome for Testing", "has-focus": True,
                 "is-minimized": False, "is-hidden": False},
                {"id": 202, "pid": 20, "app": "Google Chrome for Testing", "has-focus": False,
                 "is-minimized": False, "is-hidden": False},
            ],
        }
        state_path.write_text(json.dumps(state))
        original_windows = state["windows"]
        subprocess.run(["/bin/sh", str(root / "yabai/yabairc")], env=env, check=True)
        subprocess.run(["/bin/sh", str(root / "yabai/yabairc")], env=env, check=True)

        def dispatch(event, **arguments):
            for signal in json.loads(state_path.read_text())["signals"].values():
                if signal["event"] == event and re.search(signal.get("app", ""), "Google Chrome for Testing"):
                    subprocess.run(["/bin/sh", "-c", signal["action"]],
                                   env={**env, **arguments}, check=True, timeout=10)

        dispatch("window_created", YABAI_WINDOW_ID="201")
        dispatch("window_focused", YABAI_WINDOW_ID="201")
        dispatch("application_front_switched", YABAI_PROCESS_ID="20", YABAI_RECENT_PROCESS_ID="10")
        # A callback queued before the reload must also leave the browser alone.
        subprocess.run(["/bin/sh", "-c", pending], env={**env, "YABAI_WINDOW_ID": "201"},
                       check=True, timeout=10)
        assert json.loads(state_path.read_text())["windows"] == original_windows, "Browser visibility or focus changed."
        print("PASS: config reload and stale callbacks leave Chrome for Testing visible and focused.")


if __name__ == "__main__":
    main()
