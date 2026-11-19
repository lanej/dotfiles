#!/usr/bin/env python3
"""Stage and activate the dotfiles-curated Beads runtime."""

import fcntl
import hashlib
import json
from pathlib import Path
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
    files = ("tools/beads-service/project-update.py", "tools/beads-service/beads-service.py", "tools/beads-service/beads_config.py", "config/beads/trial.toml", "bootstrap/tools.toml")
    hashes = {name: binary_digest(ROOT / name) for name in files}
    revision = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture=True)
    dirty = bool(run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all", "--", *files], capture=True))
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return {"revision": revision, "dirty": dirty, "fingerprint": fingerprint}


def beads_artifacts(home):
    share = home / ".local/share/beads-service"
    manifest = share / "runtime.json"
    binaries = json.loads(manifest.read_text())
    paths = [share / "beads-service.py", share / "beads_config.py", manifest,
             Path(binaries["bd"]), Path(binaries["dolt"])]
    return {str(path): binary_digest(path) for path in paths}


def beads(action):
    if action == "status":
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
        controller = ROOT / "tools/beads-service/beads-service.py"
        run([sys.executable, str(controller), "install", "--home", str(home), "--no-start",
             "--install-lock-fd", str(lock_fd)], pass_fds=(lock_fd,))
        if beads_source() != source:
            raise ValueError("Beads source changed during staging; inspect the installation before retrying")
        for name in ("beads-service.py", "beads_config.py"):
            if binary_digest(ROOT / "tools/beads-service" / name) != binary_digest(share / name):
                raise ValueError("Installed Beads controller differs from the selected source")
        catalog = tomllib.loads((ROOT / "bootstrap/tools.toml").read_text())["tools"]["beads"]
        record = {"source": source, "artifacts": beads_artifacts(home),
                  "versions": {"beads": catalog["version"], "dolt": catalog["dolt_version"]}}
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
    run([sys.executable, str(installed), "restart", "--install-lock-fd", str(lock_fd)], pass_fds=(lock_fd,))
    if beads_artifacts(home) != record["artifacts"]:
        raise ValueError("Beads installation changed during restart; running revision is unknown")
    return 0



if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Usage: project-update.py ACTION")
        sys.exit(beads(sys.argv[1]))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(f"beads project-update: {error}")
