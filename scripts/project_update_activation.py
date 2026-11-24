"""Validate the activation evidence returned by project-owned controls."""

import json
import os
import subprocess
import uuid

from project_update_operations import private_directory, write_json


class IncompleteActivation(Exception):
    def __init__(self, reason, targets=None):
        super().__init__(reason)
        self.targets = targets


def evidence(value):
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise IncompleteActivation("native-lifecycle-contract-unavailable")
    targets = value.get("targets")
    if not isinstance(targets, list) or not targets:
        raise IncompleteActivation("target-inventory-missing")
    ids = set()
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("target"), str) or not target["target"]:
            raise IncompleteActivation("invalid-target-identity")
        if target["target"] in ids:
            raise IncompleteActivation("duplicate-target-identity")
        ids.add(target["target"])
        for name in ("expected_identity", "running_identity"):
            target.setdefault(name, None)
            if target.get(name) is not None and (
                    not isinstance(target[name], str) or not target[name]):
                raise IncompleteActivation(f"invalid-{name}")
        if type(target.get("ready")) is not bool:
            raise IncompleteActivation("readiness-evidence-missing")
        if "process" not in target:
            raise IncompleteActivation("process-inventory-missing")
        sessions = target.get("sessions")
        if not isinstance(sessions, list):
            raise IncompleteActivation("session-inventory-missing")
        session_ids = set()
        for session in sessions:
            if (not isinstance(session, dict) or not isinstance(session.get("session_id"), str)
                    or not session["session_id"] or session["session_id"] in session_ids):
                raise IncompleteActivation("invalid-session-identity")
            session_ids.add(session["session_id"])
            if session.get("restoration") not in ("restored", "unchanged", "blocked", "unknown", "pending"):
                raise IncompleteActivation("session-restoration-evidence-missing")
    return targets


def verified(targets):
    for target in targets:
        if not target.get("expected_identity"):
            return False, target.get("reason", "selected-artifact-identity-unknown")
        if target["running_identity"] != target["expected_identity"]:
            return False, target.get("reason", "running-artifact-does-not-match")
        if target["ready"] is not True:
            return False, target.get("reason", "target-not-ready")
        if target.get("selected_cli_ready", True) is not True:
            return False, target.get("reason", "selected-native-cli-not-promoted")
        if any(session["restoration"] not in ("restored", "unchanged") for session in target["sessions"]):
            return False, target.get("reason", "session-restoration-incomplete")
    return True, None


def native(project, action, directory=None, timeout=None):
    env = os.environ.copy()
    if directory is not None:
        env["PROJECT_UPDATE_RUN_ID"] = directory.name
        env["PROJECT_UPDATE_CHECKPOINT_DIR"] = str(directory / "checkpoints")
        env["PROJECT_UPDATE_OPERATION_DIR"] = str(directory)
    if project.get("target"):
        env["PROJECT_UPDATE_TARGET"] = project["target"]
    if project.get("expected_process"):
        env["PROJECT_UPDATE_EXPECTED_PROCESS"] = json.dumps(project["expected_process"])
        env["PROJECT_UPDATE_INSTANCE_ID"] = project["expected_process"]["native_id"]
    if project.get("deferred_sessions"):
        env["PROJECT_UPDATE_DEFER_RESTORATION"] = "1"
        env["PROJECT_UPDATE_DEFERRED_SESSION_IDS"] = json.dumps(project["deferred_sessions"])
    if project.get("recover_original"):
        env["PROJECT_UPDATE_RECOVER_ORIGINAL"] = "1"
    attempt = None
    if directory is not None:
        attempt = private_directory(directory / "evidence") / f"{uuid.uuid4()}.json"
        write_json(attempt, {"project": project.get("name"), "action": action,
                             "target": project.get("target"), "state": "requested"})
    # The adapter is outside the target's process group. A deadline does not
    # authorize terminating that target or replaying an uncertain operation.
    try:
        result = subprocess.run([*project["command"], action], cwd=project["path"],
                                env=env, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        if attempt is not None:
            write_json(attempt, {"project": project.get("name"), "action": action,
                                 "target": project.get("target"), "state": "outcome-unknown"})
        raise
    try:
        value = json.loads(result.stdout)
    except ValueError as error:
        if result.returncode in (0, 2, 3):
            raise IncompleteActivation(
                f"{action}: native-lifecycle-contract-unavailable"
                + (f": {result.stderr.strip()[-1200:]}" if result.stderr.strip() else "")) from error
        raise subprocess.CalledProcessError(result.returncode, result.args,
                                            result.stdout, result.stderr) from error
    targets = evidence(value)
    if attempt is not None:
        write_json(attempt, {"project": project.get("name"), "action": action,
                             "target": project.get("target"), "state": "observed",
                             "exit_code": result.returncode, "response": value})
    if result.returncode == 3:
        raise IncompleteActivation(value.get("reason") or next(
            (target["reason"] for target in targets if target.get("reason")), f"{action}-incomplete"), targets)
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, result.args,
                                            result.stdout, result.stderr)
    return targets


def reconcile_sessions(before, after, *, restored=False, selected=True):
    """Every observed native session must still be accounted for after restore."""
    actual = {target["target"]: target for target in after}
    for target in before:
        observed = actual.get(target["target"])
        if observed is None:
            raise IncompleteActivation(f"target-disappeared: {target['target']}")
        if selected and observed["expected_identity"] != target["expected_identity"]:
            raise IncompleteActivation(f"selected-artifact-changed: {target['target']}")
        paused = target.get("restore_scheduler_paused", target.get("scheduler_paused"))
        if restored and type(paused) is bool and observed.get("scheduler_paused") != paused:
            raise IncompleteActivation(f"restored-scheduler-pause-differs: {target['target']}")
        sessions = {session["session_id"]: session for session in observed["sessions"]}
        for session in target["sessions"]:
            if session["session_id"] not in sessions:
                raise IncompleteActivation(f"session-not-restored: {session['session_id']}")
            for key in ("transcript_path", "branch_id", "cwd", "layout_identity"):
                if key in session and session[key] != sessions[session["session_id"]].get(key):
                    raise IncompleteActivation(f"restored-{key}-differs: {session['session_id']}")


def original_restored(before, after, run_id):
    """Prove release of an original checkpoint without claiming an upgrade."""
    process = before.get("process")
    checkpoint = before.get("checkpoint") or {}
    if (not isinstance(process, dict) or process.get("owner_verified") is not True
            or type(process.get("pid")) is not int or process["pid"] <= 0
            or not all(isinstance(process.get(key), str) and process[key]
                       for key in ("start_identity", "native_id"))
            or checkpoint.get("state") != "confirmed" or checkpoint.get("run_id") != run_id
            or not before.get("running_identity")
            or after.get("process") != process
            or after.get("running_identity") != before["running_identity"]
            or after.get("ready") is not True or after.get("checkpoint") is not None
            or any(session["restoration"] not in ("restored", "unchanged")
                   for session in after["sessions"])):
        raise IncompleteActivation("original-process-restoration-unverified", [after])
    reconcile_sessions([before], [after], restored=True, selected=False)
