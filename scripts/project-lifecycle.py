#!/usr/bin/env python3
"""Project-owned adapters for the workstation lifecycle convention."""

import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(args, capture=False):
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("octo-manager", "zellij"):
        raise ValueError("Usage: project-lifecycle.py PROJECT ACTION")
    project, action = sys.argv[1:]
    if action == "status":
        if project == "octo-manager":
            metadata = Path.home() / ".local/share/octo-manager/current/release.json"
            installed = json.loads(metadata.read_text()) if metadata.exists() else None
            print(json.dumps({"installed": installed, "running_revision": None}))
        else:
            stamp = Path.home() / ".local/.dotfiles-zellij-install"
            print(json.dumps({"installed_runtime": stamp.read_text().strip() if stamp.exists() else None,
                              "running_revision": None,
                              "activation": "New sessions load installed runtime and plugins; existing sessions require restart"}))
        return 0
    if project == "octo-manager":
        architecture = {"aarch64": "arm64", "x86_64": "x64"}.get(platform.machine(), platform.machine())
        private_bun = Path.home() / f".local/share/octo-manager/runtime/{sys.platform}-{architecture}/bun-1.4.4/bun"
        bun = str(private_bun) if private_bun.is_file() else (shutil.which("bun") or str(private_bun))
        if action == "build":
            run([bun, "install", "--frozen-lockfile", "--ignore-scripts"])
            run([bun, "scripts/install-local.ts", "--no-start"])
        elif action == "restart":
            revision = run(["git", "rev-parse", "HEAD"], capture=True)
            metadata = Path.home() / ".local/share/octo-manager/current/release.json"
            if not metadata.exists() or json.loads(metadata.read_text())["revision"] != revision:
                raise ValueError("Build this revision before restarting OctoManager")
            result = json.loads(run([bun, "scripts/install-local.ts"], capture=True))
            print(json.dumps(result))
            if result.get("started") is not True:
                print("OctoManager requires manual startup; see manualCommand above", file=sys.stderr)
                return 3
        else:
            raise ValueError("OctoManager supports build, restart and status; clean is not configured")
    elif action == "build":
        run(["make", "-C", str(ROOT), "zellij-runtime", "zellij-status", "zellij-config"])
    elif action == "restart":
        binary = Path.home() / ".local/bin/zellij"
        sessions = subprocess.run([str(binary), "list-sessions", "--no-formatting"], text=True, capture_output=True)
        if sessions.returncode == 1 and sessions.stderr.strip() == "No active zellij sessions found.":
            return 0
        if sessions.returncode != 0:
            print(sessions.stderr, file=sys.stderr)
            raise ValueError("Cannot determine Zellij session state; no sessions were stopped")
        active = [line for line in sessions.stdout.splitlines() if line.strip() and not line.endswith("(EXITED - attach to resurrect)")]
        if active:
            print("Zellij restart required. Existing sessions were preserved:\n" + "\n".join(active), file=sys.stderr)
            return 3
    else:
        raise ValueError(f"{project} supports build, restart and status; clean is not configured")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(f"project-lifecycle: {error}")
