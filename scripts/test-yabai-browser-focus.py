#!/usr/bin/env python3
"""Exercise registered yabai signals; the window server is a stateful fixture."""
from pathlib import Path
import json
import os
import re
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
        node = shutil.which("node")
        assert python and node and shutil.which("jq"), "Python, Node and jq are required."
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
    options = dict(item.split("=", 1) for item in args[2:])
    state["signals"][options["label"]] = options
elif domain == "rule" or domain == "config":
    pass
elif domain == "query":
    if args == ["query", "--windows"]:
        result = state["windows"]
    elif args == ["query", "--windows", "--window", "recent"]:
        result = next(w for w in state["windows"] if w["id"] == state["recent"])
    elif args == ["query", "--windows", "--window"]:
        result = next(w for w in state["windows"] if w["has-focus"])
    else:
        raise AssertionError(args)
    print(json.dumps(result))
elif domain == "window":
    window = next(w for w in state["windows"] if w["id"] == int(args[1]))
    if args[2] == "--focus":
        state["recent"] = next(w["id"] for w in state["windows"] if w["has-focus"])
        for other in state["windows"]:
            other["has-focus"] = other["id"] == window["id"]
        window["is-minimized"] = False
    elif args[2] == "--minimize":
        window["is-minimized"] = True
        window["has-focus"] = False
    else:
        raise AssertionError(args)
else:
    raise AssertionError(args)
path.write_text(json.dumps(state))
''')
        fixture.chmod(0o755)
        native = binary / "osascript"
        native.write_text(f"#!{node}\n" + r'''
const fs = require('node:fs');
const vm = require('node:vm');
const path = process.env.YABAI_FIXTURE;
const state = JSON.parse(fs.readFileSync(path, 'utf8'));
function application(pid) {
    const name = state.apps[pid];
    if (!name) return { isNil: () => true };
    return {
        isNil: () => false,
        localizedName: name,
        get active() { return state.front === pid; },
        get hidden() {
            return state.windows.filter(w => w.pid === pid).every(w => w['is-hidden']);
        },
        terminated: false,
        activateWithOptions() {
            state.front = pid;
            for (const w of state.windows)
                w['has-focus'] = w.pid === pid && !w['is-minimized'] && !w['is-hidden'];
        },
        get hide() {
            for (const w of state.windows.filter(w => w.pid === pid)) {
                w['is-hidden'] = true;
                w['has-focus'] = false;
            }
            return true;
        },
    };
}
const context = vm.createContext({
    ObjC: { import() {}, unwrap: value => value },
    $: { NSRunningApplication: { runningApplicationWithProcessIdentifier: application },
         NSApplicationActivateIgnoringOtherApps: 2 },
});
vm.runInContext(fs.readFileSync(0, 'utf8'), context);
context.run(process.argv.slice(5));
fs.writeFileSync(path, JSON.stringify(state));
''')
        native.chmod(0o755)
        state_path = home / "state.json"
        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{binary}:{os.environ['PATH']}",
            "YABAI_FIXTURE": str(state_path),
        }
        state = {
            "signals": {},
            "apps": {"10": "kitty", "11": "Google Chrome", "20": "Google Chrome for Testing"},
            "front": 20,
            "recent": 101,
            "windows": [
                {"id": 101, "pid": 10, "app": "kitty", "has-focus": False},
                {"id": 102, "pid": 11, "app": "Google Chrome", "has-focus": False},
                {"id": 201, "pid": 20, "app": "Google Chrome for Testing", "has-focus": True},
                {"id": 202, "pid": 20, "app": "Google Chrome for Testing", "has-focus": False},
            ],
        }
        for window in state["windows"]:
            window.update({"is-minimized": False, "is-hidden": False})
        state_path.write_text(json.dumps(state))

        def load():
            return json.loads(state_path.read_text())

        def dispatch(event, app, **arguments):
            for signal in load()["signals"].values():
                if signal["event"] == event and re.search(signal.get("app", ""), app):
                    subprocess.run(
                        ["/bin/sh", "-c", signal["action"]],
                        env={**env, **arguments}, check=True, timeout=10,
                    )

        def activate(window_id):
            current = load()
            current["recent"] = next(w["id"] for w in current["windows"] if w["has-focus"])
            for window in current["windows"]:
                window["has-focus"] = window["id"] == window_id
                if window["has-focus"]:
                    window["is-minimized"] = False
                    window["is-hidden"] = False
                    current["front"] = window["pid"]
            state_path.write_text(json.dumps(current))

        def expect_background(focused_id):
            windows = {window["id"]: window for window in load()["windows"]}
            assert windows[focused_id]["has-focus"], windows
            assert load()["front"] == windows[focused_id]["pid"], "Browser still owns application shortcuts."
            assert windows[201]["is-minimized"] and windows[202]["is-minimized"], windows
            assert windows[201]["is-hidden"] and windows[202]["is-hidden"], windows
            assert not windows[102]["is-minimized"], "Regular Chrome was minimized."

        subprocess.run(["/bin/sh", str(root / "yabai/yabairc")], env=env, check=True)
        subprocess.run(["/bin/sh", str(root / "yabai/yabairc")], env=env, check=True)
        dispatch("window_created", "Google Chrome for Testing", YABAI_WINDOW_ID="201")
        expect_background(101)

        # A user switches to ordinary Chrome, then an agent reactivates its browser.
        activate(102)
        dispatch("application_front_switched", "Google Chrome",
                 YABAI_PROCESS_ID="11", YABAI_RECENT_PROCESS_ID="10")
        activate(201)
        dispatch("application_front_switched", "Google Chrome for Testing",
                 YABAI_PROCESS_ID="20", YABAI_RECENT_PROCESS_ID="11")
        expect_background(102)

        # An agent can activate an app while all its windows remain minimized.
        current = load()
        current["front"] = 20
        for window in current["windows"]:
            window["has-focus"] = False
        state_path.write_text(json.dumps(current))
        dispatch("application_front_switched", "Google Chrome for Testing",
                 YABAI_PROCESS_ID="20", YABAI_RECENT_PROCESS_ID="11")
        expect_background(102)

        activate(201)
        dispatch("window_focused", "Google Chrome for Testing", YABAI_WINDOW_ID="201")
        expect_background(102)

        # The same signal arriving after a user switch must leave that switch alone.
        activate(201)
        activate(101)
        dispatch("window_focused", "Google Chrome for Testing", YABAI_WINDOW_ID="201")
        expect_background(101)
        print("PASS: test-browser launches and reactivation return focus without affecting regular Chrome or later user switches.")


if __name__ == "__main__":
    main()
