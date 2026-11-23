"""Checkpoint, activate, and reconcile independently owned runtime targets."""

import hashlib
import subprocess

from project_update_activation import IncompleteActivation, native, reconcile_sessions, verified
from project_update_operations import private_directory, write_json

ERRORS = (OSError, ValueError, IncompleteActivation, subprocess.SubprocessError)


def aggregate(row):
    targets = row.get("target_results", [])
    problems = [target for target in targets if target["outcome"] != "ok"]
    if problems:
        problem = next((target for target in problems if target["outcome"] == "failed"), problems[0])
        row.update(outcome=problem["outcome"], reason=problem["reason"], error=problem["error"])


def one(project, target, action, directory, **options):
    values = native({**project, "target": target["target"],
                     "expected_process": target.get("process"), **options}, action, directory,
                    timeout=60 if action == "checkpoint" else None)
    if len(values) != 1 or values[0]["target"] != target["target"]:
        raise IncompleteActivation(f"{action}-target-identity-changed", values)
    return values[0]


def checkpoint(project, target, directory):
    if not target.get("expected_identity"):
        raise IncompleteActivation("selected-artifact-identity-unknown")
    process = target.get("process")
    if process is not None and (
            not isinstance(process, dict) or type(process.get("pid")) is not int or process["pid"] <= 0
            or process.get("owner_verified") is not True
            or not all(isinstance(process.get(field), str) and process[field]
                       for field in ("start_identity", "native_id"))):
        raise IncompleteActivation("process-ownership-or-start-identity-unknown")
    result = one(project, target, "checkpoint", directory)
    if (result.get("process") != process or result["expected_identity"] != target["expected_identity"]
            or result["running_identity"] != target["running_identity"]):
        raise IncompleteActivation("checkpoint-process-or-artifact-identity-changed", [result])
    if result.get("checkpoint", {}).get("state") != "confirmed":
        raise IncompleteActivation("checkpoint-not-confirmed", [result])
    if result["checkpoint"].get("run_id") != directory.name:
        raise IncompleteActivation("checkpoint-operation-identity-changed", [result])
    original = {**result, "sessions": [
        {**session, **({"branch_id": session["pre_checkpoint_branch_id"]}
                      if "pre_checkpoint_branch_id" in session else {})} for session in result["sessions"]]}
    reconcile_sessions([target], [original])
    if type(target.get("scheduler_paused")) is bool:
        result["restore_scheduler_paused"] = target["scheduler_paused"]
    return result


def deferred_process(project, target, sessions, inventories, restorations):
    """Bind each deferred application to its terminal's observed native launch."""
    bindings = []
    for session in sessions:
        owner = session.get("restoration_owner", target.get("restoration_owner")) or {}
        terminals = [value for value in inventories.get(owner.get("project"), {}).values()
                     if owner.get("target") in (value["target"], value.get("native_session_id"))]
        if len(terminals) != 1:
            raise IncompleteActivation("terminal-restoration-owner-is-ambiguous")
        terminal = terminals[0]
        restored = restorations.get((owner["project"], terminal["target"]))
        if restored is None:
            raise IncompleteActivation("authoritative-terminal-restoration-missing")
        entries = [entry for entry in restored.get("restored_applications", [])
                   if isinstance(entry, dict) and entry.get("project") == project
                   and entry.get("target") == target["target"]
                   and isinstance(entry.get("session"), dict)
                   and entry["session"].get("session_id") == session["session_id"]]
        if len(entries) != 1:
            raise IncompleteActivation("authoritative-application-restoration-missing")
        entry = entries[0]
        process, wrapper = entry.get("process"), entry.get("wrapper_process")
        if (entry.get("original_process") != target.get("process")
                or entry.get("terminal_session_id") != terminal.get("native_session_id")
                or type(entry.get("pane_id")) is not int or entry["pane_id"] != owner.get("pane_id")
                or not isinstance(process, dict) or not isinstance(wrapper, dict)
                or type(process.get("pid")) is not int or process["pid"] <= 0
                or process.get("owner_verified") is not True
                or not all(isinstance(process.get(key), str) and process[key]
                           for key in ("start_identity", "native_id"))
                or process["pid"] != wrapper.get("pid")
                or process["start_identity"] != wrapper.get("start_identity")
                or any(entry["session"].get(key) != session[key]
                       for key in ("session_id", "transcript_path", "branch_id", "cwd") if key in session)):
            raise IncompleteActivation("terminal-application-restoration-binding-differs")
        bindings.append(process)
    if not bindings or any(process != bindings[0] for process in bindings):
        raise IncompleteActivation("restored-application-process-is-ambiguous")
    return bindings[0]


def activate_targets(names, projects, rows, directory, save, ordering, failure):
    inventory, baselines, final_bindings, deferred_bindings = {}, {}, {}, {}
    restorations = {}
    for name in names:
        row = rows[name]
        if row["outcome"] != "ok":
            continue
        try:
            values = native(projects[name], "inventory", directory)
            inventory[name] = {value["target"]: value for value in values}
            baselines[name] = dict(inventory[name])
            final_bindings[name] = {value["target"]: value.get("process") for value in values}
            write_json(directory / f"{name}-inventory.json", {"schema_version": 1, "targets": values})
            row["targets"] = values
            row["target_results"] = [
                {"target": value["target"], "outcome": "ok", "completed": [],
                 "replacement_needed": not bool(value.get("expected_identity") and
                                                value["expected_identity"] == value["running_identity"])}
                for value in values]
            blockers = row.get("previous_target_blockers", {})
            for target in row["target_results"]:
                reason = blockers.get(target["target"], blockers.get(None))
                # JSON converts a null mapping key into the string "null".
                reason = reason or blockers.get("null")
                if reason:
                    failure(target, IncompleteActivation(reason))
                value = inventory[name][target["target"]]
                if (not projects[name].get("activation_deferred")
                        and value.get("session_replacement_supported") is False):
                    failure(target, IncompleteActivation("zellij-session-restoration-not-supported"))
            row["completed"].append("inventory")
            aggregate(row)
            if projects[name].get("activation_deferred"):
                row.update(activation="deferred", activation_verified=False,
                           deferred_reason="terminal-session-restart-not-requested", phase="deferred")
                for target in row["target_results"]:
                    target["activation"] = "deferred"
        except ERRORS as error:
            failure(row, error)
        save()

    def disrupted(name, seen=None):
        seen = set() if seen is None else seen
        if name in seen:
            return False
        seen.add(name)
        return any(
            any(target["replacement_needed"] for target in rows[dependency].get("target_results", []))
            or disrupted(dependency, seen)
            for dependency in projects[name].get("depends_on", []) if dependency in names
            and not projects[dependency].get("activation_deferred"))

    def consumer_blocker(name):
        return next((consumer for consumer in names
                     if name in projects[consumer].get("depends_on", [])
                     and rows[consumer]["outcome"] != "ok"), None)

    def terminal_disrupted(target):
        for session in target["sessions"]:
            owner = session.get("restoration_owner", target.get("restoration_owner")) or {}
            if not projects.get(owner.get("project"), {}).get("activation_deferred") and any(result["replacement_needed"]
                   and owner.get("target") in (
                       result["target"],
                       inventory.get(owner.get("project"), {}).get(result["target"], {}).get("native_session_id"))
                   for result in rows.get(owner.get("project"), {}).get("target_results", [])):
                return True
        return False

    def deferred_terminal(target):
        for session in target["sessions"]:
            owner = session.get("restoration_owner", target.get("restoration_owner")) or {}
            if projects.get(owner.get("project"), {}).get("activation_deferred"):
                return owner["project"]
        return None

    # Complete inventory precedes all disruption; consumers settle first.
    checkpoint_order = sorted(reversed(ordering),
                              key=lambda name: projects[name].get("lifecycle") == "terminal")
    for name in checkpoint_order:
        row = rows[name]
        if name not in inventory or projects[name].get("activation_deferred"):
            continue
        for result in row["target_results"]:
            if result["outcome"] != "ok":
                continue
            target = inventory[name][result["target"]]
            if verified([target])[0] and not disrupted(name) and not terminal_disrupted(target):
                result["activation"] = "already-current"
                continue
            try:
                terminal = deferred_terminal(target)
                if terminal is not None:
                    raise IncompleteActivation(f"terminal-session-restart-deferred: {terminal}")
                consumer = consumer_blocker(name)
                if consumer is not None:
                    raise IncompleteActivation(f"dependent-checkpoint-incomplete: {consumer}")
                # This phase is intent only. The native evidence journal records
                # whether a request was issued, refused, confirmed, or unknown.
                result["phase"] = row["phase"] = "checkpoint-requested"
                save()
                confirmed = checkpoint(projects[name], target, directory)
                baselines[name][target["target"]] = confirmed
                result["completed"].append("checkpoint")
                result["phase"] = "checkpoint-confirmed"
                path = private_directory(directory / "checkpoints") / (
                    f"{name}-{hashlib.sha256(target['target'].encode()).hexdigest()}.json")
                write_json(path, [confirmed])
            except ERRORS as error:
                failure(result, error)
            aggregate(row)
            save()
        if all("checkpoint" in target["completed"] or target.get("activation") == "already-current"
               for target in row["target_results"]) and any(
                   "checkpoint" in target["completed"] for target in row["target_results"]):
            row["completed"].append("checkpoint")
        if all(target.get("activation") == "already-current" for target in row["target_results"]):
            row["activation"] = "already-current"
        save()
    write_json(directory / "restoration-plan.json",
               {name: {"targets": list(targets.values())} for name, targets in baselines.items()})

    def prerequisite_blocker(name):
        for prerequisite in projects[name].get("depends_on", []):
            if prerequisite in rows:
                if rows[prerequisite]["outcome"] != "ok":
                    return prerequisite
            elif not verified(native(projects[prerequisite], "verify", directory))[0]:
                return prerequisite
        return None

    for name in ordering:
        row = rows[name]
        if name not in inventory or projects[name].get("activation_deferred"):
            continue
        for result in row["target_results"]:
            if result["outcome"] != "ok" or result.get("activation") == "already-current":
                continue
            target = baselines[name][result["target"]]
            try:
                prerequisite = prerequisite_blocker(name)
                consumer = consumer_blocker(name)
                if prerequisite is not None:
                    raise IncompleteActivation(f"prerequisite-activation-incomplete: {prerequisite}")
                if consumer is not None:
                    raise IncompleteActivation(f"dependent-checkpoint-incomplete: {consumer}")
                def deferred_owner(session):
                    owner = session.get("restoration_owner", target.get("restoration_owner")) or {}
                    return any(value["replacement_needed"] and value["outcome"] == "ok"
                               and owner.get("target") in (
                                   value["target"],
                                   inventory.get(owner.get("project"), {}).get(value["target"], {}).get("native_session_id"))
                               for value in rows.get(owner.get("project"), {}).get("target_results", []))
                deferred = [session["session_id"] for session in target["sessions"] if deferred_owner(session)]
                if result["replacement_needed"]:
                    result["phase"] = row["phase"] = "replacement-requested"
                    save()
                    replaced = one(projects[name], target, "restart", directory, deferred_sessions=deferred)
                    reconcile_sessions([target], [replaced])
                    target = {**target, "process": replaced.get("process")}
                    result["completed"].append("restart")
                result["phase"] = row["phase"] = "restoration-requested"
                save()
                restored = one(projects[name], target, "restore", directory, deferred_sessions=deferred,
                               recover_original=not result["replacement_needed"] and not deferred)
                reconcile_sessions([target], [restored], restored=not deferred)
                if not deferred and restored.get("process") != target.get("process"):
                    raise IncompleteActivation("restoration-process-incarnation-changed", [restored])
                if deferred:
                    deferred_bindings[(name, target["target"])] = [
                        session for session in target["sessions"] if session["session_id"] in deferred]
                else:
                    final_bindings[name][target["target"]] = restored.get("process")
                    result["restored_process"] = restored.get("process")
                restorations[(name, target["target"])] = restored
                if projects[name].get("lifecycle", "service") in ("service", "stateless"):
                    complete, reason = verified([restored])
                    if not complete:
                        raise IncompleteActivation(reason, [restored])
                result["completed"].append("restore")
                result["phase"] = "restoration-observed"
            except ERRORS as error:
                failure(result, error)
            aggregate(row)
            save()
        for action in ("restart", "restore"):
            needed = [target for target in row["target_results"] if (
                target.get("activation") != "already-current" and
                (action == "restore" or target["replacement_needed"]))]
            if needed and all(action in target["completed"] for target in needed):
                row["completed"].append(action)

    # Recover only an original process whose replacement was never attempted.
    # Native owners may remove its admission fence; this path cannot launch.
    for name in names:
        if name not in inventory or projects[name].get("activation_deferred"):
            continue
        row = rows[name]
        for result in row["target_results"]:
            if (result["outcome"] == "ok" or "checkpoint" not in result["completed"]
                    or result.get("phase") in ("replacement-requested", "restoration-requested", "restoration-observed")):
                continue
            target = baselines[name][result["target"]]
            try:
                result["phase"] = "original-restoration-requested"
                save()
                restored = one(projects[name], target, "restore", directory, recover_original=True)
                reconcile_sessions([target], [restored], restored=True)
                if (restored.get("process") != inventory[name][target["target"]].get("process")
                        or restored["running_identity"] != inventory[name][target["target"]]["running_identity"]
                        or not restored["ready"]):
                    raise IncompleteActivation("original-process-restoration-unverified", [restored])
                result["recovered_original"] = True
            except ERRORS as error:
                result["recovery_reason"] = str(error)
            save()

    # All terminal-owned launches precede final consumer verification.
    for name in names:
        if name not in inventory or projects[name].get("activation_deferred"):
            continue
        row = rows[name]
        observed = dict(inventory[name])
        for result in row["target_results"]:
            target = baselines[name][result["target"]]
            try:
                binding = final_bindings[name][target["target"]]
                if (name, target["target"]) in deferred_bindings:
                    binding = deferred_process(name, target, deferred_bindings[(name, target["target"])],
                                               inventory, restorations)
                    result["restored_process"] = binding
                value = one(projects[name], {**target, "process": binding}, "verify", directory)
                observed[target["target"]] = value
                reconcile_sessions([target], [value], restored=True)
                if value.get("process") != binding:
                    raise IncompleteActivation("final-process-incarnation-changed", [value])
                complete, reason = verified([value])
                if not complete:
                    raise IncompleteActivation(reason, [value])
                if result["outcome"] == "ok":
                    result["completed"].append("verify")
                    result["phase"] = "verified"
            except ERRORS as error:
                if isinstance(error, IncompleteActivation) and error.targets:
                    for value in error.targets:
                        observed[value["target"]] = value
                if result["outcome"] == "ok":
                    failure(result, error)
            aggregate(row)
            save()
        row["targets"] = list(observed.values())
        if all("verify" in target["completed"] for target in row["target_results"]):
            row["completed"].append("verify")
            row["phase"] = "verified"
        save()
