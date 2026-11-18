#!/usr/bin/env python3
"""Project-owned adapters for the workstation lifecycle convention."""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent.parent


def run(args, capture=False):
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def router(action):
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    installed = codex_home / "bedrock-router/bedrock-router"
    receipt = installed.parent / ".project-update.json"
    revision = run(["git", "rev-parse", "HEAD"], capture=True)
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    built = cache / "dotfiles/project-update/bedrock-router" / revision / "bedrock-router"
    if action == "status":
        record = json.loads(receipt.read_text()) if receipt.is_file() else None
        installed_revision = None
        if record and installed.is_file() and record["sha256"] == binary_digest(installed):
            installed_revision = record["revision"]
        print(json.dumps({"installed_binary": str(installed) if installed.is_file() else None,
                          "installed_revision": installed_revision,
                          "running_revision": None}))
        return 0
    if action in ("build", "restart") and run(["git", "status", "--porcelain"], capture=True):
        raise ValueError("Preserve Bedrock Router checkout changes before installing or restarting a versioned build")
    flags = ["install", "--config", str(Path.cwd() / "config.json"), "--keep-env", "--preserve-mcp"]
    if action == "build":
        built.parent.mkdir(parents=True, exist_ok=True)
        run(["go", "build", "-buildvcs=true", "-o", str(built), "."])
        run([str(built), *flags, "--no-start"])
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=receipt.parent, prefix=".project-update-", delete=False) as staged:
                temporary = Path(staged.name)
                json.dump({"revision": revision, "sha256": binary_digest(installed)}, staged)
            os.replace(temporary, receipt)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    elif action == "restart":
        if not built.is_file() or not installed.is_file() or not same_binary(built, installed):
            raise ValueError("Build and stage this Bedrock Router revision before restarting")
        run([str(built), *flags])
    else:
        raise ValueError("Bedrock Router supports build, restart and status; clean is not configured")
    return 0


def same_binary(first, second):
    return binary_digest(first) == binary_digest(second)


def binary_digest(path):
    with path.open("rb") as binary:
        return hashlib.file_digest(binary, "sha256").hexdigest()


def beads_source():
    files = ("scripts/beads-service.py", "scripts/beads_config.py", "config/beads/trial.toml", "bootstrap/tools.toml")
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
        controller = ROOT / "scripts/beads-service.py"
        run([sys.executable, str(controller), "install", "--home", str(home), "--no-start"])
        if beads_source() != source:
            raise ValueError("Beads source changed during staging; inspect the installation before retrying")
        for name in ("beads-service.py", "beads_config.py"):
            if binary_digest(ROOT / "scripts" / name) != binary_digest(share / name):
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
    run([sys.executable, str(installed), "restart"])
    if beads_artifacts(home) != record["artifacts"]:
        raise ValueError("Beads installation changed during restart; running revision is unknown")
    return 0



def approval_cli(project, action):
    """Install through each CLI's native target without stopping live sessions."""
    prefix = Path.home() / ".local"
    installed = prefix / "bin" / project
    receipt = prefix / "share/dotfiles/project-update" / f"{project}.json"
    revision = run(["git", "rev-parse", "HEAD"], capture=True)
    record = json.loads(receipt.read_text()) if receipt.is_file() else None
    installed_revision = None
    if record and installed.is_file() and record["sha256"] == binary_digest(installed):
        installed_revision = record["revision"]
    activation = ("Start new Keylease sessions; existing brokers and leases are preserved"
                  if project == "keylease" else
                  "Automatic SSH approval awaits production stable-socket integration; "
                  "installation does not activate transport. Existing sessions are preserved")
    if action == "status":
        print(json.dumps({"installed_binary": str(installed) if installed.is_file() else None,
                          "installed_revision": installed_revision, "running_revision": None,
                          "activation": activation}))
        return 0
    if action not in ("build", "restart"):
        raise ValueError(f"{project} supports build, restart and status; clean is not configured")
    if run(["git", "status", "--porcelain", "--untracked-files=all"], capture=True):
        raise ValueError(f"Preserve {project} checkout changes before installing or restarting a versioned build")
    if action == "restart":
        if installed_revision != revision:
            raise ValueError(f"Build and install this {project} revision before restarting")
        print(activation + "; active process revisions are unknown", file=sys.stderr)
        return 3
    if project == "keylease" and run(["go", "env", "CGO_ENABLED"], capture=True) != "1":
        raise ValueError("Keylease desktop authentication requires CGO_ENABLED=1 and a native C compiler")
    run(["make", "install", f"PREFIX={prefix}"])
    built = Path.cwd() / "bin" / project
    built_digest = binary_digest(built) if built.is_file() else None
    if built_digest is None or not installed.is_file() or binary_digest(installed) != built_digest:
        raise ValueError(f"Native {project} installation did not match the built executable")
    if run(["git", "rev-parse", "HEAD"], capture=True) != revision or run(
            ["git", "status", "--porcelain", "--untracked-files=all"], capture=True):
        raise ValueError(f"{project} checkout changed during installation; installed revision remains unrecorded")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=receipt.parent, prefix=f".{project}-", delete=False) as staged:
            temporary = Path(staged.name)
            json.dump({"revision": revision, "sha256": built_digest}, staged)
        os.replace(temporary, receipt)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return 0


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("octo-manager", "zellij", "bedrock-router", "intent", "keylease", "beads"):
        raise ValueError("Usage: project-lifecycle.py PROJECT ACTION")
    project, action = sys.argv[1:]
    if project == "beads":
        return beads(action)
    if project in ("intent", "keylease"):
        return approval_cli(project, action)
    if project == "bedrock-router":
        return router(action)
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
        configuration = json.loads(run([sys.executable, str(ROOT / "scripts/dotfiles-config.py"), "--format", "json"], capture=True))
        source = configuration["settings"]["zellij.source"]
        targets = ["zellij-runtime"]
        if source != "release":
            targets.append("zellij-status")
        targets.append("zellij-config")
        if source == "patched":
            targets.append("zellij-copy-hop")
        run(["make", "-C", str(ROOT), *targets])
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
