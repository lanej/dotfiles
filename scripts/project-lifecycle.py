#!/usr/bin/env python3
"""Project-owned adapters for the workstation lifecycle convention."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from bun_runtime import ensure_runtime, require_runtime
from runtime_requirements import project_requirements, register_requirements

ROOT = Path(__file__).resolve().parent.parent


def run(args, capture=False, **kwargs):
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None, **kwargs)
    return result.stdout.strip() if capture else ""


def activate_service(project, arguments):
    """Preserve native refusal codes and evidence after an attempted replacement."""
    result = subprocess.run(arguments, text=True, capture_output=True)
    if result.returncode == 0:
        return json.loads(result.stdout) if project == "octo-manager" and result.stdout.strip() else {}
    service = importlib.import_module("service-project-activation")
    value, _ = service.inspect(project)
    reason = result.stderr.strip()[-1200:] or f"{project}-native-replacement-unverified"
    try:
        native_result = json.loads(result.stdout)
        if isinstance(native_result, dict) and isinstance(native_result.get("reason"), str):
            reason = native_result["reason"]
    except ValueError:
        pass
    value["targets"][0].update(reason=reason, replacement_outcome="unverified; do not repeat replacement")
    return service.emit(value, 3 if result.returncode == 3 else 1)


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
    config = installed.parent / "config.json"
    if not config.is_file():
        config = Path.cwd() / "config.json"
    flags = ["install", "--config", str(config), "--keep-env", "--preserve-mcp"]
    if action == "build":
        built.parent.mkdir(parents=True, exist_ok=True)
        run([sys.executable, "scripts/build-lifecycle.py", "--output", str(built),
             "--manifest", str(built.with_suffix(".build.json"))])
        artifact = json.loads(built.with_suffix(".build.json").read_text())
        if (not artifact.get("expected_identity")
                or artifact.get("sha256") != binary_digest(built)):
            raise ValueError("Native Router build manifest does not bind the staged image")
        run([str(built), *flags, "--no-start"])
        if artifact["sha256"] != binary_digest(installed):
            raise ValueError("Selected Router installation differs from its native build manifest")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=receipt.parent, prefix=".project-update-", delete=False) as staged:
                temporary = Path(staged.name)
                json.dump({"revision": revision, "sha256": artifact["sha256"],
                           "expected_identity": artifact["expected_identity"]}, staged)
            os.replace(temporary, receipt)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    elif action == "restart":
        if not built.is_file() or not installed.is_file() or not same_binary(built, installed):
            raise ValueError("Build and stage this Bedrock Router revision before restarting")
        service = importlib.import_module("service-project-activation")
        try:
            service.checkpoint_binding("bedrock-router")
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            value, _ = service.inspect("bedrock-router")
            value["targets"][0]["reason"] = str(error)
            return service.emit(value, 3)
        activated = activate_service("bedrock-router", [str(built), *flags])
        if isinstance(activated, int):
            return activated
        return service.emit(*service.inspect("bedrock-router", "verify"))
    else:
        raise ValueError("Bedrock Router supports build, restart and status; clean is not configured")
    return 0


def same_binary(first, second):
    return binary_digest(first) == binary_digest(second)


def binary_digest(path):
    with path.open("rb") as binary:
        return hashlib.file_digest(binary, "sha256").hexdigest()


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
    activation = ("Native lifecycle controls preserve unsupported conversations and require fresh approval after replacement"
                  if project == "keylease" else
                  "Native lifecycle controls discover existing local and paired remote profiles; "
                  "installation does not create or enable SSH transports")
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
    if len(sys.argv) != 3 or sys.argv[1] not in ("octo-manager", "zellij", "bedrock-router", "intent", "keylease"):
        raise ValueError("Usage: project-lifecycle.py PROJECT ACTION")
    project, action = sys.argv[1:]
    if project in ("intent", "keylease"):
        if action in ("inventory", "checkpoint", "restart", "restore", "verify"):
            return subprocess.run([sys.executable, str(ROOT / "scripts/approval-project-activation.py"),
                                   project, action]).returncode
        if action == "build":
            result = approval_cli(project, action)
            if project == "intent":
                return subprocess.run([sys.executable, str(ROOT / "scripts/approval-project-activation.py"),
                                       project, "stage-remotes"]).returncode
            return result
        return approval_cli(project, action)
    if action in ("inventory", "checkpoint", "restore", "verify"):
        script = "zellij-activation.py" if project == "zellij" else "service-project-activation.py"
        command = [sys.executable, str(ROOT / "scripts" / script)]
        if project != "zellij":
            command.append(project)
        return subprocess.run([*command, action]).returncode
    if project == "bedrock-router":
        return router(action)
    if action == "status":
        if project == "octo-manager":
            metadata = Path.home() / ".local/share/octo-manager/current/release.json"
            installed = json.loads(metadata.read_text()) if metadata.exists() else None
            service = importlib.import_module("service-project-activation")
            print(json.dumps({"installed": installed, "staged": service.staged_selection(), "running_revision": None}))
        else:
            stamp = Path.home() / ".local/.dotfiles-zellij-install"
            print(json.dumps({"installed_runtime": stamp.read_text().strip() if stamp.exists() else None,
                              "running_revision": None,
                              "activation": "New sessions load installed runtime and plugins; existing sessions require restart"}))
        return 0
    if project == "octo-manager":
        if action == "build":
            bun = str(ensure_runtime(Path.cwd()))
            environment = {**os.environ, "PATH": str(Path(bun).parent) + os.pathsep + os.environ.get("PATH", "")}
            run([bun, "install", "--frozen-lockfile", "--ignore-scripts"], env=environment)
            staged = json.loads(run([bun, "scripts/install-local.ts", "--stage-only"], capture=True, env=environment))
            service = importlib.import_module("service-project-activation")
            service.record_selection(staged)
            register_requirements("octo-manager", project_requirements(Path.cwd()), source=str(Path.cwd() / "package.json"))
        elif action == "restart":
            revision = run(["git", "rev-parse", "HEAD"], capture=True)
            service = importlib.import_module("service-project-activation")
            metadata = service.selected_release() / "release.json"
            if not metadata.exists() or json.loads(metadata.read_text())["revision"] != revision:
                raise ValueError("Build this revision before restarting OctoManager")
            try:
                service.checkpoint_binding("octo-manager")
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                value, _ = service.inspect("octo-manager")
                value["targets"][0]["reason"] = str(error)
                return service.emit(value, 3)
            bun = str(require_runtime(Path.cwd()))
            result = activate_service("octo-manager", [bun, "scripts/install-local.ts"])
            if isinstance(result, int):
                return result
            if result.get("started") is not True:
                value, _ = service.inspect("octo-manager")
                value["targets"][0]["reason"] = "native-service-start-unavailable"
                return service.emit(value, 3)
            return service.emit(*service.inspect("octo-manager", "verify"))
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
        run([sys.executable, str(ROOT / "scripts/zellij-activation.py"), "stage"])
    elif action == "restart":
        return subprocess.run([sys.executable, str(ROOT / "scripts/zellij-activation.py"), action]).returncode

    else:
        raise ValueError(f"{project} supports build, restart and status; clean is not configured")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(f"project-lifecycle: {error}")
