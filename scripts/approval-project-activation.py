#!/usr/bin/env python3
"""Delegate activation to the owners' native, incarnation-bound controls."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from project_update_operations import read_json, state_root, write_json


PROJECT, ACTION = sys.argv[1:]
PREFIX = Path(os.environ.get("APPROVAL_PROJECT_PREFIX", Path.home() / ".local"))
BINARY = (PREFIX / "bin" / PROJECT).resolve()
STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
MANIFEST = STATE / "dotfiles/project-update/approval-artifacts" / f"{PROJECT}.json"


def digest(path):
    with Path(path).open("rb") as stream:
        value = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
        return value.hexdigest()


def invoke(arguments, *, host=None, input_file=None, timeout=60, environment=None):
    if host is not None:
        arguments = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                     "-o", "ClearAllForwardings=yes",
                     "-o", "PermitLocalCommand=no", "--", host, shlex.join(arguments)]
    result = subprocess.run(arguments, stdin=input_file, capture_output=True, text=True,
                            timeout=timeout, env=environment)
    try:
        value = json.loads(result.stdout)
    except ValueError:
        value = None
    return result, value


def unavailable(target, expected, reason, **metadata):
    return {"target": target, "expected_identity": expected, "running_identity": None,
            "ready": False, "process": None, "sessions": [], "reason": reason, **metadata}


def artifact():
    _, value = invoke([str(BINARY), "lifecycle", "artifact"])
    if not isinstance(value, dict) or value.get("sha256") != digest(BINARY):
        raise ValueError("selected-native-image-identity-unavailable")
    if not isinstance(value.get("expected_identity"), str) or not value["expected_identity"]:
        raise ValueError("selected-native-image-is-unmanaged")
    return value


def profiles():
    result, value = invoke([str(BINARY), "lifecycle", "profiles"])
    if result.returncode or not isinstance(value, list):
        raise ValueError("native-profile-discovery-unavailable")
    return value


def save_manifest(record):
    # Create the operation root before its child; mkdir(parents=True) gives
    # intermediate directories the process umask rather than the leaf's mode.
    state_root()
    if MANIFEST.exists() or MANIFEST.is_symlink():
        read_json(MANIFEST)
    write_json(MANIFEST, record)


def selected_manifest(local):
    if not MANIFEST.is_file():
        return {"local": local, "remotes": {}}
    if MANIFEST.is_symlink() or MANIFEST.stat().st_uid != os.getuid() or MANIFEST.stat().st_mode & 0o077:
        raise ValueError("artifact-manifest-is-not-private-and-owned")
    record = json.loads(MANIFEST.read_text())
    if record["local"] != local:
        return {"local": local, "remotes": {}}
    return record


def inspect_target(arguments, target, expected, *, host=None, timeout=60):
    """Keep one unavailable owner from hiding independent inventory rows."""
    try:
        _, value = invoke(arguments, host=host, timeout=timeout)
        if isinstance(value, dict) and value.get("schema_version") == 1 and len(value.get("targets", [])) == 1:
            actual = value["targets"][0]
            if actual.get("process") is None:
                actual["target"] = target
            return actual
        return unavailable(target, expected, "native-control-unavailable")
    except (OSError, ValueError, subprocess.SubprocessError):
        return unavailable(target, expected, "native-control-unreachable")


def stage_remotes():
    """Compile selected remote images locally; deployment belongs to restart."""
    local = artifact()
    record = {"local": local, "remotes": {}}
    systems = {"Linux": "linux", "Darwin": "darwin"}
    architectures = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "dotfiles/project-update/intent"
    source_key = hashlib.sha256(local["expected_identity"].encode()).hexdigest()
    built = {}
    for profile in profiles():
        host = profile["host"]
        try:
            result, _ = invoke(["uname", "-sm"], host=host, timeout=15)
            words = result.stdout.split()
            if result.returncode or len(words) != 2 or words[0] not in systems or words[1] not in architectures:
                raise ValueError("remote-platform-unavailable")
            platform, architecture = systems[words[0]], architectures[words[1]]
            key = (platform, architecture)
            if key not in built:
                output = cache / source_key / f"{platform}-{architecture}" / "intent"
                manifest = output.with_suffix(".build.json")
                environment = {**os.environ, "GOOS": platform, "GOARCH": architecture, "CGO_ENABLED": "0"}
                subprocess.run([sys.executable, "scripts/build-lifecycle.py", "--tool", "intent",
                                "--output", str(output), "--manifest", str(manifest)],
                               check=True, env=environment, stdout=sys.stderr)
                image = json.loads(manifest.read_text())
                if digest(output) != image["sha256"]:
                    raise ValueError("compiled-remote-artifact-changed")
                built[key] = {**image, "binary": str(output)}
            record["remotes"][host] = built[key]
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            record["remotes"][host] = {"reason": str(error)}
    save_manifest(record)
    print(json.dumps(record))
    return 0


def inventory_intent(local):
    selected = selected_manifest(local)
    targets = []
    deduplicated = {}
    configured = profiles()
    if not configured:
        return [{"target": "intent-cli", "expected_identity": local["expected_identity"],
                 "running_identity": local["expected_identity"], "ready": True,
                 "process": None, "sessions": [], "kind": "stateless-cli"}]
    for profile in configured:
        path, host, directory = profile["profile_path"], profile["host"], profile["remote_directory"]
        target = inspect_target([str(BINARY), "lifecycle", "inventory", "--profile", path],
                                "local:" + profile["local_socket"], local["expected_identity"])
        target.update(expected_identity=local["expected_identity"], profile_path=path,
                      activation_kind="local", paired_mac_id=profile["mac_id"])
        if target.get("process") is not None and target.get("mac_id") != profile["mac_id"]:
            target.update(ready=False, reason="configured-local-profile-pairing-differs")
        targets.append(target)
        selected_remote = selected["remotes"].get(host, {})
        if selected_remote.get("binary"):
            try:
                if digest(selected_remote["binary"]) != selected_remote["sha256"]:
                    selected_remote = {"reason": "selected-remote-artifact-changed"}
            except OSError:
                selected_remote = {"reason": "selected-remote-artifact-unavailable"}
        remote = inspect_target(["intent", "lifecycle", "inventory", "--directory", directory],
                                f"remote:{host}:{directory}", None, host=host, timeout=15)
        remote.update(expected_identity=selected_remote.get("expected_identity"), host=host,
                      remote_directory=directory, activation_kind="remote", aliases=[host],
                      paired_mac_id=profile["mac_id"],
                      selected_binary=selected_remote.get("binary"), selected_sha256=selected_remote.get("sha256"))
        if selected_remote.get("reason"):
            remote["reason"] = selected_remote["reason"]
        elif not remote["expected_identity"]:
            remote["reason"] = "selected-remote-platform-artifact-not-staged"
        if remote.get("process") is not None and remote.get("mac_id") != profile["mac_id"]:
            remote.update(ready=False, reason="configured-remote-profile-pairing-differs")
        process = remote.get("process")
        identity = ((process.get("pid"), process.get("start_identity"), process.get("native_id"), remote.get("mac_id"))
                    if isinstance(process, dict) else None)
        if identity is not None and identity in deduplicated:
            previous = deduplicated[identity]
            if previous["expected_identity"] != remote["expected_identity"]:
                previous.update(ready=False, reason="aliases-select-different-artifacts-for-one-broker")
            if previous["paired_mac_id"] != remote["paired_mac_id"]:
                previous.update(ready=False, reason="aliases-pair-different-routing-identities-for-one-broker")
            previous["aliases"].append(host)
        else:
            targets.append(remote)
            if identity is not None:
                deduplicated[identity] = remote
    return targets


def inventory_keylease(local):
    targets = []
    result, backends = invoke([str(BINARY), "lifecycle", "backends"])
    if result.returncode or not isinstance(backends, list) or any(
            backend not in ("1password", "mock") for backend in backends):
        raise ValueError("native-backend-discovery-unavailable")
    if not backends:
        return [{"target": "keylease-cli", "expected_identity": local["expected_identity"],
                 "running_identity": local["expected_identity"], "ready": True,
                 "process": None, "sessions": [], "kind": "stateless-cli"}]
    for backend in backends:
        target = inspect_target([str(BINARY), "--backend", backend, "lifecycle", "inventory"],
                                f"broker:{backend}", local["expected_identity"], timeout=10)
        target.update(expected_identity=local["expected_identity"], backend=backend)
        targets.append(target)
    return targets


def frozen_target():
    directory = Path(os.environ["PROJECT_UPDATE_OPERATION_DIR"])
    path = directory / f"{PROJECT}-inventory.json"
    if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise ValueError("inventory-record-is-not-private-and-owned")
    targets = json.loads(path.read_text())["targets"]
    target_id = os.environ.get("PROJECT_UPDATE_TARGET")
    selected = [target for target in targets if target["target"] == target_id]
    if len(selected) != 1:
        raise ValueError("exact-native-target-required")
    return selected[0]


def guard_arguments(target):
    process = target.get("process")
    if not isinstance(process, dict):
        raise ValueError("legacy-process-checkpoint-unavailable")
    return ["--pid", str(process["pid"]), "--start-identity", process["start_identity"],
            "--native-id", process["native_id"], "--run-id", os.environ["PROJECT_UPDATE_RUN_ID"]]


def native_target(target, action, *, selected=False, input_file=None):
    if target.get("kind") == "stateless-cli":
        return 0, target
    if PROJECT == "keylease":
        arguments = [str(BINARY), "--backend", target["backend"], "lifecycle", action]
        host = None
    elif target.get("activation_kind") == "local":
        arguments = [str(BINARY), "lifecycle", action, "--profile", target["profile_path"]]
        host = None
    elif target.get("activation_kind") == "remote":
        binary = target["selected_remote_executable"] if selected else target.get("executable") or "intent"
        arguments = [binary, "lifecycle", action, "--directory", target["remote_directory"]]
        host = target["host"]
    else:
        return 0, target
    if action not in ("inventory", "verify", "artifact"):
        if PROJECT == "intent":
            validate_profile_pairing(target)
            _, current = native_target(target, "inventory")
            if current.get("mac_id") != target.get("paired_mac_id") or current.get("process") != target["process"]:
                raise ValueError("native-pairing-or-process-incarnation-differs")
        arguments.extend(guard_arguments(target))
    result, value = invoke(arguments, host=host, input_file=input_file)
    if not isinstance(value, dict) or value.get("schema_version") != 1 or len(value.get("targets", [])) != 1:
        raise ValueError(f"{action}-native-outcome-unavailable-or-unknown")
    actual = value["targets"][0]
    if actual.get("process") is None and result.returncode == 3:
        # The exact original target is retained as context for a refused or
        # unknown native outcome; it never turns refusal into completion.
        actual["target"] = target["target"]
    actual["expected_identity"] = target["expected_identity"]
    for key in ("backend", "activation_kind", "profile_path", "host", "remote_directory", "aliases", "paired_mac_id",
                "selected_binary", "selected_sha256", "selected_remote_executable"):
        if key in target:
            actual[key] = target[key]
    if actual["target"] != target["target"]:
        raise ValueError("native-target-identity-changed")
    if PROJECT == "intent" and actual.get("process") is not None and actual.get("mac_id") != target.get("paired_mac_id"):
        actual.update(ready=False, reason="native-pairing-differs")
    return result.returncode, actual


def validate_profile_pairing(target):
    configured = profiles()
    if target.get("activation_kind") == "local":
        matched = [profile for profile in configured if profile["profile_path"] == target["profile_path"]]
        if len(matched) != 1 or matched[0]["mac_id"] != target["paired_mac_id"]:
            raise ValueError("configured-local-profile-pairing-changed")
    else:
        aliases = set(target["aliases"])
        matched = [profile for profile in configured if profile["host"] in aliases]
        if (set(profile["host"] for profile in matched) != aliases
                or any(profile["mac_id"] != target["paired_mac_id"]
                       or profile["remote_directory"] != target["remote_directory"] for profile in matched)):
            raise ValueError("configured-remote-profile-pairing-changed")


def deploy_remote(target):
    validate_profile_pairing(target)
    _, current = native_target(target, "inventory")
    if current.get("mac_id") != target.get("paired_mac_id") or current.get("process") != target["process"]:
        raise ValueError("native-pairing-or-process-incarnation-differs")
    binary = Path(target["selected_binary"])
    if digest(binary) != target["selected_sha256"]:
        raise ValueError("staged-platform-artifact-changed")
    arguments = [target.get("executable") or "intent", "lifecycle", "stage",
                 "--directory", target["remote_directory"], "--sha256", target["selected_sha256"]]
    with binary.open("rb") as stream:
        result, value = invoke(arguments, host=target["host"], input_file=stream)
    if result.returncode or not isinstance(value, dict) or value.get("sha256") != target["selected_sha256"]:
        raise ValueError("remote-artifact-deployment-not-confirmed")
    path = value.get("installed_binary")
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise ValueError("verified-remote-executable-path-missing")
    target["selected_remote_executable"] = path
    return target


def complete(target):
    return bool(target.get("expected_identity") and target.get("running_identity") == target["expected_identity"]
                and target.get("ready") is True
                and all(session["restoration"] in ("restored", "unchanged") for session in target["sessions"]))


def main():
    if PROJECT not in ("intent", "keylease"):
        raise ValueError("unknown approval project")
    if ACTION == "stage-remotes":
        if PROJECT != "intent":
            raise ValueError("remote staging belongs to Intent")
        return stage_remotes()
    local = artifact()
    if ACTION in ("inventory", "verify"):
        targets = inventory_intent(local) if PROJECT == "intent" else inventory_keylease(local)
        selected = os.environ.get("PROJECT_UPDATE_TARGET")
        if selected is not None:
            targets = [target for target in targets if target["target"] == selected]
            if len(targets) != 1:
                raise ValueError("exact-native-target-not-in-inventory")
        print(json.dumps({"schema_version": 1, "targets": targets}))
        return 0 if ACTION == "inventory" or all(complete(target) for target in targets) else 3
    target = frozen_target()
    recovering_original = ACTION == "restore" and os.environ.get("PROJECT_UPDATE_RECOVER_ORIGINAL") == "1"
    if (not recovering_original and local["expected_identity"] != target["expected_identity"]
            and target.get("activation_kind") != "remote"):
        raise ValueError("selected-local-native-image-changed")
    if ACTION == "restart" and target.get("activation_kind") == "remote":
        target = deploy_remote(target)
    if ACTION == "restore" and os.environ.get("PROJECT_UPDATE_RECOVER_ORIGINAL") != "1":
        if PROJECT == "intent" and target.get("kind") != "stateless-cli":
            validate_profile_pairing(target)
        expected_process = json.loads(os.environ["PROJECT_UPDATE_EXPECTED_PROCESS"])
        code, actual = native_target(target, "inventory")
        if actual.get("process") != expected_process:
            actual["reason"] = "replacement-process-incarnation-differs"
            print(json.dumps({"schema_version": 1, "targets": [actual]}))
            return 3
        if expected_process is None and target.get("kind") != "stateless-cli":
            actual["reason"] = "replacement-process-binding-unavailable"
            print(json.dumps({"schema_version": 1, "targets": [actual]}))
            return 3
        if complete(actual):
            print(json.dumps({"schema_version": 1, "targets": [actual]}))
            return 0
        actual["reason"] = actual.get("reason") or "replacement-restoration-not-confirmed"
        print(json.dumps({"schema_version": 1, "targets": [actual]}))
        return 3
    code, actual = native_target(target, ACTION, selected=ACTION == "restart" and target.get("activation_kind") == "remote")
    print(json.dumps({"schema_version": 1, "targets": [actual]}))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        selected = os.environ.get("PROJECT_UPDATE_TARGET", "local")
        print(json.dumps({"schema_version": 1, "targets": [
            unavailable(selected, None, str(error))], "reason": str(error)}))
        sys.exit(3)
