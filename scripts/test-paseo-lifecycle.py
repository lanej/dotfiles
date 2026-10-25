#!/usr/bin/env python3
"""Makefile workflows for persistent lifecycle control and live device pairing."""
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
elif command == "paseo":
    if args == ["--home", str(Path.home() / ".paseo"), "daemon", "status", "--json"]:
        state["status_checks"] += 1
        ready = state["status_checks"] > 1 and state["jobs"]["local.paseo.daemon"]["loaded"]
        print(json.dumps({
            "localDaemon": "running" if ready else "not_ready",
            "connectedDaemon": "reachable" if ready else "not_probed",
            "listen": "127.0.0.1:6767" if ready else None,
        }))
    elif args == ["--host", "127.0.0.1:6767", "daemon", "pair", "--relay"]:
        if state["status_checks"] < 2 or not all(
            state["jobs"][label]["loaded"]
            for label in ("local.paseo.daemon", "local.paseo.relay", "local.paseo.lan-ingress")
        ):
            sys.exit(1)
        state["pair_calls"] += 1
        print("Scan to pair:\\n[fixture QR code]\\nPairing link:\\nhttps://fixture.invalid/#offer=fixture")
    else:
        sys.exit(2)
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
        certificate = home / ".local/share/paseo-secure/pairing/paseo-lan-ca.cer"
        certificate.parent.mkdir(parents=True)
        certificate.write_text("fixture public certificate\n")
        executables = fixture / "bin"
        executables.mkdir()
        for name in ("launchctl", "open", "pkill", "paseo"):
            command = executables / name
            command.write_text(f"#!{sys.executable}\n{BOUNDARY}")
            command.chmod(0o755)
        state = fixture / "state.json"
        unrelated = {"loaded": True, "disabled": False}
        state.write_text(json.dumps({
            "jobs": {**{label: {"loaded": True, "disabled": False} for label in LABELS},
                     "local.unrelated": unrelated},
            "app_running": True,
            "status_checks": 0,
            "pair_calls": 0,
        }))
        env = {**os.environ, "HOME": str(home),
               "PATH": f"{executables}{os.pathsep}{os.environ['PATH']}",
               "PASEO_FIXTURE_STATE": str(state),
               "PASEO_HOST": "unrelated.invalid:9999",
               "PASEO_HOME": str(fixture / "unrelated-home")}
        outputs = {}

        def run(target):
            result = subprocess.run(
                [shutil.which("make"), "--no-print-directory", "UNAME_S=Darwin", target],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
            outputs[target] = result.stdout
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
        paired = run("paseo-pair")
        assert paired["app_running"], paired
        assert paired["status_checks"] == 2 and paired["pair_calls"] == 1, paired
        assert "[fixture QR code]" in outputs["paseo-pair"], outputs["paseo-pair"]
        assert "https://fixture.invalid/#offer=fixture" in outputs["paseo-pair"], outputs["paseo-pair"]
        assert str(certificate) in outputs["paseo-pair"], outputs["paseo-pair"]
        assert "VPN & Device Management" in outputs["paseo-pair"], outputs["paseo-pair"]
        assert "Certificate Trust Settings" in outputs["paseo-pair"], outputs["paseo-pair"]
        assert paired["jobs"]["local.unrelated"] == unrelated, paired
        print("PASS: Device pairing starts the local host, waits for readiness, and prints its live offer.")


if __name__ == "__main__":
    main()
