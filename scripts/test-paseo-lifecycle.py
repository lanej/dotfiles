#!/usr/bin/env python3
"""One Makefile workflow: stop, stay stopped, start, and stop again."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
LABELS = ("local.paseo.daemon", "local.paseo.relay", "local.paseo.lan-ingress")
BOUNDARY = """\
import json, os, sys
from pathlib import Path

path = Path(os.environ["PASEO_FIXTURE_STATE"])
state = json.loads(path.read_text())
command = Path(sys.argv[0]).name
args = sys.argv[1:]
if command == "launchctl":
    action = args[0]
    label = Path(args[-1]).stem if action == "bootstrap" else args[-1].split("/")[-1]
    job = state["jobs"][label]
    if action == "print":
        sys.exit(0 if job["loaded"] else 1)
    if action == "disable":
        job["disabled"] = True
    elif action == "enable":
        job["disabled"] = False
    elif action == "bootout":
        if not job["loaded"]:
            sys.exit(1)
        job["loaded"] = False
    elif action == "bootstrap":
        if job["disabled"] or job["loaded"] or not Path(args[-1]).is_file():
            sys.exit(1)
        job["loaded"] = True
    else:
        sys.exit(2)
elif command == "open" and args == ["-a", "Paseo"]:
    state["app_running"] = True
elif command == "pkill" and args == ["-TERM", "-u", str(os.getuid()), "-x", "Paseo"]:
    if not state["app_running"]:
        sys.exit(1)
    state["app_running"] = False
else:
    sys.exit(2)
path.write_text(json.dumps(state))
"""


def main():
    with tempfile.TemporaryDirectory(prefix="paseo-lifecycle-") as directory:
        fixture = Path(directory)
        home = fixture / "home"
        agents = home / "Library/LaunchAgents"
        agents.mkdir(parents=True)
        for label in LABELS:
            (agents / f"{label}.plist").write_text("fixture LaunchAgent\n")
        executables = fixture / "bin"
        executables.mkdir()
        for name in ("launchctl", "open", "pkill"):
            command = executables / name
            command.write_text(f"#!{sys.executable}\n{BOUNDARY}")
            command.chmod(0o755)
        state = fixture / "state.json"
        unrelated = {"loaded": True, "disabled": False}
        state.write_text(json.dumps({
            "jobs": {**{label: {"loaded": True, "disabled": False} for label in LABELS},
                     "local.unrelated": unrelated},
            "app_running": True,
        }))
        env = {**os.environ, "HOME": str(home),
               "PATH": f"{executables}{os.pathsep}{os.environ['PATH']}",
               "PASEO_FIXTURE_STATE": str(state)}

        def run(target):
            result = subprocess.run(
                [shutil.which("make"), "--no-print-directory", "UNAME_S=Darwin", target],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
            return json.loads(state.read_text())

        def expect_stopped(observed):
            assert not observed["app_running"], observed
            assert all(observed["jobs"][label] == {"loaded": False, "disabled": True}
                       for label in LABELS), observed
            assert observed["jobs"]["local.unrelated"] == unrelated, observed

        expect_stopped(run("paseo-stop"))
        expect_stopped(run("paseo-stop"))
        started = run("paseo-start")
        assert started["app_running"], started
        assert all(started["jobs"][label] == {"loaded": True, "disabled": False}
                   for label in LABELS), started
        assert started["jobs"]["local.unrelated"] == unrelated, started
        expect_stopped(run("paseo-stop"))
        print("PASS: Paseo stops persistently, starts through launchd, and leaves unrelated jobs alone.")


if __name__ == "__main__":
    main()
