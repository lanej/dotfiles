#!/usr/bin/env python3
"""Stage and activate the dotfiles-curated Beads runtime."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def run(args, capture=False, **kwargs):
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, **kwargs)
    return result.stdout.strip() if capture else ""


def binary_digest(path):
    with path.open("rb") as binary:
        return hashlib.file_digest(binary, "sha256").hexdigest()


def beads_source():
    files = ("tools/beads/project-update.py", "tools/beads/beads-service.py", "tools/beads/beads_config.py",
             "tools/beads/beads_lifecycle.py", "config/beads/trial.toml", "tools/beads/tool.toml")
    hashes = {name: binary_digest(ROOT / name) for name in files}
    revision = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture=True)
    dirty = bool(run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all", "--", *files], capture=True))
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return {"revision": revision, "dirty": dirty, "fingerprint": fingerprint}


def beads_artifacts(home):
    share = home / ".local/share/beads-service"
    manifest = share / "runtime.json"
    binaries = json.loads(manifest.read_text())
    paths = [share / "beads-service.py", share / "beads_config.py", share / "beads_lifecycle.py", manifest,
             Path(binaries["bd"]), Path(binaries["dolt"])]
    return {str(path): binary_digest(path) for path in paths}


def beads(action):
    if action in ("status", "inventory", "checkpoint", "verify", "restore"):
        return beads_locked(action)
    if action not in ("build", "restart"):
        raise ValueError("Beads supports build, restart and status; clean is not configured")
    share = Path.home() / ".local/share/beads-service"
    share.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (share / "install.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another Beads installation or service operation is in progress") from error
        return beads_locked(action, lock.fileno())


def beads_locked(action, lock_fd=None):
    """Stage curated artifacts and activate only the matching staged source."""
    home = Path.home()
    share = home / ".local/share/beads-service"
    receipt = share / "project-update.json"
    installed = share / "beads-service.py"
    record = json.loads(receipt.read_text()) if receipt.is_file() else None
    verified = False
    if record:
        try:
            verified = beads_artifacts(home) == record["artifacts"]
        except (OSError, ValueError, KeyError):
            pass
    if action in ("inventory", "checkpoint", "verify", "restore"):
        target = {"target": "local", "expected_identity": None, "running_identity": None,
                  "ready": False, "process": None, "sessions": [],
                  "reason": "beads-native-checkpoint-control-unavailable"}
        if verified:
            from beads_lifecycle import artifact_identity
            target["expected_identity"] = artifact_identity(home)
        if installed.is_file():
            result = subprocess.run([sys.executable, str(installed), action], text=True, capture_output=True)
            try:
                value = json.loads(result.stdout)
                if value.get("schema_version") == 1 and isinstance(value.get("targets"), list):
                    if not verified:
                        for native_target in value["targets"]:
                            native_target.update(expected_identity=None, reason="beads-staged-artifacts-changed")
                    print(json.dumps(value))
                    return 0 if action == "inventory" else result.returncode if verified else 3
            except (ValueError, AttributeError):
                pass
        print(json.dumps({"schema_version": 1, "targets": [target]}))
        return 0 if action == "inventory" else 3
    if action == "status":
        service = None
        if installed.is_file():
            result = subprocess.run([sys.executable, str(installed), "status"], text=True, capture_output=True)
            try:
                service = json.loads(result.stdout)
            except ValueError:
                service = {"ready": False, "error": result.stderr.strip()[:800]}
        source = record["source"] if verified else None
        print(json.dumps({"installed_revision": source["revision"] if source and not source["dirty"] else None,
                          "installed_source_dirty": source["dirty"] if source else None,
                          "installed_source_fingerprint": source["fingerprint"] if source else None,
                          "installed_versions": record["versions"] if verified else None,
                          "running_revision": None, "service": service}))
        return 0
    if action not in ("build", "restart"):
        raise ValueError("Beads supports build, restart and status; clean is not configured")
    source = beads_source()
    if action == "build":
        controller = ROOT / "tools/beads/beads-service.py"
        run([sys.executable, str(controller), "install", "--home", str(home), "--no-start",
             "--install-lock-fd", str(lock_fd)], pass_fds=(lock_fd,))
        if beads_source() != source:
            raise ValueError("Beads source changed during staging; inspect the installation before retrying")
        for name in ("beads-service.py", "beads_config.py", "beads_lifecycle.py"):
            if binary_digest(ROOT / "tools/beads" / name) != binary_digest(share / name):
                raise ValueError("Installed Beads controller differs from the selected source")
        catalog = tomllib.loads((ROOT / "tools/beads/tool.toml").read_text())["tools"]["beads"]
        versions = {"beads": catalog["version"], "dolt": catalog["dolt_version"]}
        if platform.system() == "Darwin":
            binaries = json.loads((share / "runtime.json").read_text())
            for name, key in (("bd", "beads"), ("dolt", "dolt")):
                output = run([binaries[name], "version"], capture=True)
                match = re.search(rf"\b{name} version v?(\d+\.\d+\.\d+)(?=\s|$)", output)
                if match is None:
                    raise ValueError(f"Cannot record staged Homebrew {name} version: {output!r}")
                versions[key] = match[1]
        record = {"source": source, "artifacts": beads_artifacts(home), "versions": versions}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=share, prefix=".project-update-", delete=False) as output:
                temporary = Path(output.name)
                json.dump(record, output)
                output.write("\n")
            temporary.replace(receipt)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return 0
    if not verified or record["source"]["fingerprint"] != source["fingerprint"]:
        raise ValueError("Build this Beads source before restarting; staged artifacts must remain unchanged")
    operation = os.environ.get("PROJECT_UPDATE_OPERATION_DIR")
    if not operation:
        return beads_locked("verify")
    frozen = json.loads((Path(operation) / "beads-inventory.json").read_text())["targets"][0]
    expected = frozen.get("process")
    os.environ["PROJECT_UPDATE_EXPECTED_PROCESS"] = json.dumps(expected)
    from beads_lifecycle import inspect
    current = inspect(home, "inventory")["targets"][0]
    if (current["process"] != expected
            or current.get("checkpoint", {}).get("state") != "confirmed"
            or current["checkpoint"].get("run_id") != os.environ.get("PROJECT_UPDATE_RUN_ID")):
        print(json.dumps({"schema_version": 1, "targets": [{**current, "reason": "beads-checkpoint-binding-differs"}]}))
        return 3
    result = subprocess.run([sys.executable, str(installed), "restart", "--install-lock-fd", str(lock_fd)],
                            text=True, capture_output=True, pass_fds=(lock_fd,))
    if result.returncode:
        try:
            observed = inspect(home, "inventory")["targets"][0]
        except (OSError, ValueError, KeyError):
            observed = {"target": "local", "expected_identity": current["expected_identity"],
                        "running_identity": None, "ready": False, "process": None, "sessions": []}
        observed.update(reason=result.stderr.strip()[-1200:] or "native-beads-restart-unverified",
                        replacement_outcome="unverified; do not repeat replacement")
        print(json.dumps({"schema_version": 1, "targets": [observed]}))
        return 3 if result.returncode == 3 else 1
    if beads_artifacts(home) != record["artifacts"]:
        raise ValueError("Beads installation changed during restart; running revision is unknown")
    return beads_locked("verify")



if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Usage: project-update.py ACTION")
        sys.exit(beads(sys.argv[1]))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(f"beads project-update: {error}")
