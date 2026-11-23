#!/usr/bin/env python3
"""Use each service's native identity and guarded activation controls."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from bun_runtime import require_runtime
from project_update_operations import read_json, write_json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selection_path():
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return root / "dotfiles/project-update/selected-octo-manager.json"


def validate_selection(value):
    if (not isinstance(value, dict) or value.get("schema_version") != 1
            or value.get("staged") is not True or value.get("promoted") is not False
            or not isinstance(value.get("release_path"), str)
            or not isinstance(value.get("revision"), str)
            or not isinstance(value.get("expected_identity"), str)
            or not value["expected_identity"]):
        raise ValueError("Native Octo staging receipt is invalid")
    selected = Path(value["release_path"])
    base = Path.home() / ".local/share/octo-manager/releases"
    if (not selected.is_absolute() or selected.is_symlink() or not selected.is_dir()
            or not selected.resolve().is_relative_to(base.resolve())
            or selected.resolve() == base.resolve()):
        raise ValueError("Native Octo staged release is outside its immutable release store")
    selected = selected.resolve()
    metadata = json.loads((selected / "release.json").read_text())
    if metadata.get("revision") != value["revision"]:
        raise ValueError("Native Octo staged revision differs from its receipt")
    return {**value, "release_path": str(selected)}


def staged_selection():
    path = selection_path()
    return validate_selection(read_json(path)) if path.exists() or path.is_symlink() else None


def selected_release():
    staged = staged_selection()
    return Path(staged["release_path"]) if staged else Path.home() / ".local/share/octo-manager/current"


def record_selection(value):
    value = validate_selection(value)
    selected = Path(value["release_path"])
    bun = require_runtime(selected)
    observed, code = native([str(bun), str(selected / "dist/cli.js"), "lifecycle"], "artifact")
    if code or not isinstance(observed, dict) or observed.get("expected_identity") != value["expected_identity"]:
        raise ValueError("Native Octo staged artifact is not confirmed")
    path = selection_path()
    if path.is_symlink():
        raise ValueError("Preserve symlinked Octo selection receipt")
    if path.exists():
        read_json(path)
    write_json(path, value)


def specification(project):
    if project == "bedrock-router":
        home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
        binary = home / "bedrock-router/bedrock-router"
        return [str(binary), "lifecycle"], binary, binary.parent / ".project-update.json"
    selected = selected_release()
    bun = require_runtime(selected)
    return [str(bun), str(selected / "dist/cli.js"), "lifecycle"], selected / "dist/cli.js", selected / "release.json"


def native(command, action):
    result = subprocess.run([*command, action], capture_output=True, text=True, timeout=65)
    try:
        return json.loads(result.stdout), result.returncode
    except ValueError:
        return None, result.returncode


def inspect(project, action="inventory"):
    try:
        command, binary, receipt = specification(project)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        target = {"target": "local", "expected_identity": None, "running_identity": None,
                  "ready": False, "process": None, "sessions": [],
                  "reason": f"required-shared-runtime-unavailable: {error}"}
        if action == "checkpoint":
            target["checkpoint"] = {"state": "refused", "run_id": os.environ.get("PROJECT_UPDATE_RUN_ID")}
        return {"schema_version": 1, "targets": [target]}, 0 if action == "inventory" else 3
    selected = binary.resolve()
    expected = None
    record = None
    if project == "bedrock-router" and binary.is_file() and receipt.is_file():
        record = json.loads(receipt.read_text())
        if record.get("sha256") == digest(binary):
            expected = record.get("expected_identity")
    elif project == "octo-manager" and receipt.is_file():
        record = json.loads(receipt.read_text())
        expected = "revision:" + record["revision"]
    attempted = False
    try:
        if project == "octo-manager":
            command[1] = str(selected)
            artifact, artifact_code = native(command, "artifact")
            if artifact_code == 0 and isinstance(artifact, dict):
                expected = artifact.get("expected_identity")
            staged = staged_selection()
            if staged and expected != staged["expected_identity"]:
                raise ValueError("Native Octo artifact changed after staging")
        if action == "checkpoint":
            before, before_code = native(command, "inventory")
            if not isinstance(before, dict) or before.get("schema_version") != 1 or not before.get("targets") or before_code:
                raise ValueError("Native inventory unavailable before checkpoint")
        attempted = True
        value, code = native(command, action)
        if isinstance(value, dict) and value.get("schema_version") == 1 and value.get("targets"):
            if binary.resolve() != selected or (
                    project == "bedrock-router" and
                    (not isinstance(record, dict) or not receipt.is_file() or json.loads(receipt.read_text()) != record
                     or digest(binary) != record.get("sha256"))):
                expected = None
            for target in value["targets"]:
                target["expected_identity"] = expected
                if project == "octo-manager":
                    release = selected.parent.parent
                    target["selected_release"] = str(release)
                    current = Path.home() / ".local/share/octo-manager/current"
                    if not current.exists() or current.resolve() != release:
                        target["ready"] = False
                        target["reason"] = target.get("reason") or "selected-native-cli-not-promoted"
            return value, code
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    target = {"target": "local", "expected_identity": expected, "running_identity": None,
              "ready": False, "process": None, "sessions": [],
              "reason": f"{project}-native-checkpoint-control-unavailable"}
    if action == "checkpoint":
        target["checkpoint"] = {"state": "unknown" if attempted else "refused",
                                "run_id": os.environ.get("PROJECT_UPDATE_RUN_ID")}
    return {"schema_version": 1, "targets": [target]}, 0 if action == "inventory" else 3


def frozen(project):
    directory = os.environ.get("PROJECT_UPDATE_OPERATION_DIR")
    if not directory:
        raise ValueError("A detached update checkpoint is required for service replacement")
    targets = read_json(Path(directory) / f"{project}-inventory.json")["targets"]
    if len(targets) != 1:
        raise ValueError("Unexpected service target inventory")
    return targets[0]


def checkpoint_binding(project):
    before = frozen(project)
    value, code = inspect(project)
    current = value["targets"][0]
    if (code or current["process"] != before["process"]
            or current["expected_identity"] != before["expected_identity"]
            or current["running_identity"] != before["running_identity"]
            or current.get("checkpoint", {}).get("state") != "confirmed"
            or current["checkpoint"].get("run_id") != os.environ.get("PROJECT_UPDATE_RUN_ID")):
        raise ValueError("Service checkpoint or process incarnation differs")
    return current


def emit(value, code):
    print(json.dumps(value))
    return code


def main():
    project, action = sys.argv[1:]
    if action in ("inventory", "checkpoint", "verify"):
        value, code = inspect(project, action)
        if action == "verify" and any(not target["ready"] or not target["expected_identity"]
                                      or target["running_identity"] != target["expected_identity"] for target in value["targets"]):
            code = 3
        return emit(value, 0 if action == "inventory" else code)
    if action == "restore":
        value, code = inspect(project)
        target = value["targets"][0]
        command, _, _ = specification(project)
        before = frozen(project)
        if os.environ.get("PROJECT_UPDATE_RECOVER_ORIGINAL") == "1":
            if target["process"] != before["process"]:
                target["reason"] = "original-service-incarnation-differs"
                return emit(value, 3)
            return emit(*inspect(project, "restore"))
        if project == "octo-manager":
            return emit(*inspect(project, "restore"))
        if code == 0 and target["ready"] and target["running_identity"] == target["expected_identity"]:
            return emit(value, 0)
        return emit(value, 3)
    raise ValueError("This adapter supports inventory, checkpoint, restore and verify")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        project = sys.argv[1] if len(sys.argv) > 1 else "service"
        value, _ = inspect(project)
        value["targets"][0]["reason"] = str(error)
        sys.exit(emit(value, 3))
