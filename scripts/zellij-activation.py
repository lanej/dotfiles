#!/usr/bin/env python3
"""Inventory native Zellij sessions without guessing application resume IDs."""

import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import sqlite3
import stat
import struct
import subprocess
import sys
import tempfile
import time
import uuid
import zellij_activation_baseline as baseline


def run(argv):
    environment = {**os.environ, "LC_ALL": "C", "TZ": "UTC"} if argv[0] == "ps" else None
    result = subprocess.run(argv, capture_output=True, text=True, timeout=10, env=environment)
    if result.returncode:
        raise ValueError(f"Native Zellij inspection failed: {result.stderr.strip()[-1000:]}")
    return result.stdout


def private_directory(path):
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError(f"Zellij lifecycle directory is not private and owned: {path}")


def save(path, value):
    private_directory(path.parent)
    if path.exists():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Preserving unexpected Zellij lifecycle file")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(value, output)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_private(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Zellij lifecycle file is not private and owned")
    return json.loads(path.read_text())


def application_snapshot(intent):
    if intent["project"] != "studio":
        raise ValueError("Application owner has no authoritative restored-process probe")
    state = intent["restore_env"].get("STUDIO_STATE_DIR")
    if state is None:
        state = str(Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "studio")
    directory = Path(state) / "activation"
    for file in directory.glob("*.json"):
        record = read_private(file)
        if record.get("target") != intent["target"]:
            continue
        if not process_alive(record["process"]):
            continue
        endpoint = Path(record["socket"])
        info = endpoint.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Restored native application endpoint is not owned")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(3)
            connection.connect(str(endpoint))
            pid, started = peer(connection)
            if pid != record["process"]["pid"] or started != record["process"]["start_identity"]:
                raise ValueError("Restored native application endpoint changed")
            connection.sendall(b'{"action":"inventory"}\n')
            response = bytearray()
            while b"\n" not in response and len(response) <= 4 * 1024 * 1024:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                response.extend(chunk)
            value = json.loads(response.split(b"\n", 1)[0])
            if value.get("schema_version") != 1 or len(value.get("targets", [])) != 1:
                raise ValueError("Invalid restored native application reply")
            observed = value["targets"][0]
            if observed["process"] != record["process"]:
                raise ValueError("Restored native application incarnation changed")
            return observed
    raise ValueError("Restored native application receipt is not available")


def restored_applications(directory, saved, observed):
    proofs = []
    if observed["nested_targets"] != saved.get("nested_targets", {}):
        raise ValueError("Restored nested native attachment differs from its checkpoint")
    for pane, child in saved.get("nested_targets", {}).items():
        launch = read_private(directory / f"zellij-pane-launch-{saved['persistent_identity'][1]}-{pane}.json")
        wrapper = launch["wrapper_process"]
        if (observed["_activation"].get("terminal_processes", {}).get(pane) != wrapper["pid"]
                or launch["terminal_session_id"] != saved["persistent_identity"][1]
                or launch["pane_id"] != int(pane) or not process_alive(wrapper)
                or running_runtime(wrapper["pid"]) != immutable_runtime((Path.home() / ".local/bin/zellij").resolve())):
            raise ValueError("Restored nested native client differs from its one-time launcher")
    intents = restore_intents(directory, saved)
    for pane, intent in intents.items():
        launch = read_private(directory / f"zellij-pane-launch-{saved['persistent_identity'][1]}-{pane}.json")
        wrapper = launch["wrapper_process"]
        if (launch["run_id"] != saved["run_id"] or launch["session_id"] != intent["session"]["session_id"]
                or launch["terminal_session_id"] != saved["persistent_identity"][1]
                or launch["pane_id"] != pane):
            raise ValueError("Native application launcher binding changed")
        actual = application_snapshot(intent)
        expected_session = {key: intent["session"][key]
                            for key in ("session_id", "transcript_path", "branch_id", "cwd")}
        actual_session = next((value for value in actual["sessions"]
                               if value["session_id"] == expected_session["session_id"]), None)
        owner = actual.get("restoration_owner") or {}
        if (actual["process"]["pid"] != wrapper["pid"]
                or actual["process"]["start_identity"] != wrapper["start_identity"]
                or actual.get("restored_checkpoint") != {"run_id": saved["run_id"], "process": intent["process"]}
                or actual["running_identity"] != intent["replacement_identity"] or not actual["ready"]
                or actual_session is None or any(actual_session.get(key) != value for key, value in expected_session.items())
                or owner != {"project": "zellij", "target": saved["target"], "pane_id": pane}
                or not any(row["id"] == pane and not row.get("is_plugin")
                           for row in observed["_snapshot"]["panes"])):
            raise ValueError("Native restored application differs from its one-time launcher and checkpoint")
        proofs.append({"project": intent["project"], "target": intent["target"],
                       "original_process": intent["process"], "process": actual["process"],
                       "session": expected_session, "terminal_session_id": saved["persistent_identity"][1],
                       "pane_id": pane, "wrapper_process": wrapper})
    return proofs


def artifacts():
    installed = Path.home() / ".local/bin/zellij"
    stamp = Path.home() / ".local/.dotfiles-zellij-install"
    if not installed.is_file() or not stamp.is_file():
        raise ValueError("Selected Zellij runtime has not been installed")
    paths = [installed]
    for plugins in (Path.home() / ".config/zellij/plugins",
                    Path.home() / ".local/share/zellij/plugins"):
        if plugins.is_dir():
            paths.extend(sorted(plugins.glob("*.wasm")))
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def receipt_path():
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "dotfiles/zellij-activation/installed.json"


def expected_identity():
    path = receipt_path()
    if not path.exists():
        return None
    record = read_private(path)
    return record["identity"] if record["artifacts"] == artifacts() else None


def immutable_runtime(path):
    root = (Path.home() / ".local/lib/zellij/runtimes").resolve()
    path = path.resolve()
    if path.parent.parent != root or path.name != "zellij":
        return None
    before = path.stat()
    image = hashlib.sha256(path.read_bytes()).hexdigest()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or before.st_mode & 0o222 or path.parent.name != image:
        raise ValueError("Immutable runtime artifact changed during inspection")
    return image


def running_runtime(pid):
    if platform.system() == "Linux":
        image = Path(f"/proc/{pid}/exe")
        path = image.resolve()
        selected = immutable_runtime(path)
        return selected if selected == hashlib.sha256(image.read_bytes()).hexdigest() else None
    libc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    libc.proc_pidpath.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    libc.proc_pidpath.restype = ctypes.c_int
    buffer = ctypes.create_string_buffer(4096)
    if libc.proc_pidpath(pid, buffer, len(buffer)) <= 0:
        raise OSError(ctypes.get_errno(), "Mapped runtime path inspection unavailable")
    path = Path(os.fsdecode(buffer.value)).resolve()
    image = immutable_runtime(path)
    if image is None:
        return None
    expected = path.stat()
    text = run(["/usr/sbin/lsof", "-a", "-p", str(pid), "-d", "txt", "-F", "Din"])
    device, inode = None, None
    for line in text.splitlines():
        if line.startswith("D"):
            device = int(line[1:], 16)
        elif line.startswith("i"):
            inode = int(line[1:])
        elif line.startswith("n") and line[1:] == str(path):
            if device == expected.st_dev and inode == expected.st_ino:
                return image
    raise ValueError("The mapped immutable executable vnode was not verified")


def artifact_identity(runtime, plugins, clients=None):
    return hashlib.sha256(json.dumps({"runtime": runtime, "plugins": plugins, "clients": clients or {}},
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def client_directory():
    return receipt_path().parent / "clients"


def client_request(native_id, action="inventory", **request):
    if not isinstance(native_id, str) or str(uuid.UUID(native_id)) != native_id:
        raise ValueError("Native terminal client identity is unavailable")
    record = read_private(client_directory() / f"{native_id}.json")
    endpoint = Path(record["socket"])
    info = endpoint.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Native terminal client endpoint is not private and owned")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(str(endpoint))
        pid, started = peer(connection)
        if (pid != record["process"]["pid"] or started != record["process"]["start_identity"]
                or record["process"]["native_id"] != native_id):
            raise ValueError("Native terminal client incarnation changed")
        connection.sendall((json.dumps({"action": action, **request}) + "\n").encode())
        response = bytearray()
        while b"\n" not in response and len(response) <= 4 * 1024 * 1024:
            chunk = connection.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
    result = json.loads(response.split(b"\n", 1)[0])
    if result.get("error"):
        raise ValueError(result["error"])
    if result.get("process") != record["process"] or result.get("schema_version") != 1:
        raise ValueError("Native terminal client reply differs from its endpoint")
    if running_runtime(pid) != result["image_sha256"]:
        raise ValueError("Native terminal client mapped image differs")
    return result


def observe_clients(clients, server):
    if not isinstance(clients, list):
        raise ValueError("Native terminal connection inventory is unavailable")
    result, seen = [], set()
    for client in clients:
        if not isinstance(client, dict) or type(client.get("client_id")) is not int:
            raise ValueError("Native terminal connection contract changed")
        native_id = client.get("activation_id")
        observed = {**client, "managed": False}
        if native_id:
            if native_id in seen:
                raise ValueError("Native terminal client identity is duplicated")
            seen.add(native_id)
            actual = client_request(native_id)
            if actual.get("input_retention_error") or actual.get("raw_io_error"):
                raise ValueError("Native terminal client input durability remains unconfirmed")
            authority = actual.get("input_authority") or {}
            if (actual.get("raw_input_checkpoint") is not True
                    or authority.get("reader_verified") is not True or authority.get("reader_stopped")):
                raise ValueError("Native terminal raw-reader checkpoint authority is unavailable")
            if (actual["connected"] is not True or actual["session"] != server["target"]
                    or actual["process"]["pid"] != client.get("peer_pid")
                    or actual["server_identity"] != json.loads(server["process"]["native_id"])
                    or not isinstance(client.get("focus"), dict)):
                raise ValueError("Native terminal client connection binding changed")
            observed.update(actual, managed=True)
        result.append(observed)
    result.sort(key=lambda client: (client.get("activation_id") or "", client["client_id"]))
    return result


def client_image_key(client):
    if client.get("restoration_owner"):
        return json.dumps(client["restoration_owner"], sort_keys=True, separators=(",", ":"))
    return json.dumps([client["process"]["pid"], client["process"]["start_identity"], client["tty"]],
                      sort_keys=True, separators=(",", ":"))


def checkpoint_clients(directory, saved, target, original):
    clients = target["connections"]
    if any(not client["managed"] for client in clients):
        raise ValueError("native-user-terminal-reconnect-checkpoint-unavailable")
    if clients != original["connections"]:
        raise ValueError("Native terminal connection or focus changed after inventory")
    if any(client["focus"].get("pane_id", [None, True])[1] is not False for client in clients):
        raise ValueError("Native plugin-focus restoration requires a persistent plugin pane binding")
    runtime = (Path.home() / ".local/bin/zellij").resolve()
    image = immutable_runtime(runtime)
    saved["clients"] = []
    declared_parents = {client["restoration_owner"]["target"] for client in clients
                        if client.get("restoration_owner")}
    if len(declared_parents) > 1:
        raise ValueError("Nested connections with multiple parent servers require a shared native handoff")
    # Retain intent before each endpoint call; uncertain calls are reconciled without resubmission.
    for client in clients:
        client = dict(client)
        owner = client.get("restoration_owner") or {}
        parent = next((row for row in read_private(directory / "zellij-inventory.json")["targets"]
                       if row.get("native_session_id") == owner.get("target")), None)
        client["defer_to_parent"] = parent is not None and parent["expected_identity"] != parent["running_identity"]
        if client["defer_to_parent"]:
            actual_parent = next((row for row in sessions(expected_identity()) if row["target"] == parent["target"]), None)
            if (actual_parent is None or actual_parent["process"] != parent["process"]
                    or actual_parent["nested_targets"].get(str(owner["pane_id"])) != target["target"]
                    or actual_parent["_activation"].get("terminal_processes", {}).get(str(owner["pane_id"])) != client["process"]["pid"]):
                raise ValueError("Native nested client is not owned by its frozen parent pane")
        saved["clients"].append(client)
        saved["state"] = "pending"
        save(checkpoint_path(original), saved)
        response = client_request(client["activation_id"], "checkpoint",
                                  expected_process=client["process"], run_id=saved["run_id"],
                                  server_identity=json.loads(saved["process"]["native_id"]),
                                  server_process=saved["process"],
                                  baseline_display=saved["environment_baseline"]["display"],
                                  operation_directory=str(directory), replacement_path=str(runtime),
                                  replacement_sha256=image, focus=client["focus"],
                                  defer_to_parent=client["defer_to_parent"])
        if response.get("checkpoint") != {"state": "confirmed", "run_id": saved["run_id"]}:
            raise ValueError("Native terminal client checkpoint remains unconfirmed")


def restored_clients(directory, saved, observed, *, deferred=False):
    original = [client for client in saved.get("clients", [])
                if not deferred or not client.get("defer_to_parent")]
    current = observed["connections"]
    if deferred:
        owners = [client["restoration_owner"] for client in saved.get("clients", []) if client.get("defer_to_parent")]
        current = [client for client in current if client.get("restoration_owner") not in owners]
    if len(current) != len(original) or any(not client.get("managed") for client in current):
        raise ValueError("Restored native terminal connections are incomplete")
    proofs = []
    for before in original:
        if before.get("defer_to_parent"):
            owner = before["restoration_owner"]
            client = next((value for value in current if value.get("restoration_owner") == owner), None)
            launch = read_private(directory / f"zellij-pane-launch-{owner['target']}-{owner['pane_id']}.json")
            if (client is None or process_alive(before["process"])
                    or launch["run_id"] != saved["run_id"] or launch["terminal_session_id"] != owner["target"]
                    or launch["pane_id"] != owner["pane_id"]
                    or any(client["process"][key] != launch["wrapper_process"][key] for key in ("pid", "start_identity"))):
                raise ValueError("Restored nested native client differs from its parent one-time launcher")
        else:
            client = next((value for value in current if value["process"]["pid"] == before["process"]["pid"]
                           and value["process"]["start_identity"] == before["process"]["start_identity"]
                           and value["tty"] == before["tty"]), None)
        path = directory / f"zellij-client-{before['process']['native_id']}.json"
        if (client is None or client["process"] == before["process"]
                or client.get("focus") != before["focus"]
                or client.get("restored_checkpoint") != {
                    "run_id": saved["run_id"], "process": before["process"], "tty": before["tty"],
                    "focus": before["focus"], "input_recovery_path": str(path)}):
            raise ValueError("Restored native terminal TTY or focus differs from its checkpoint")
        proofs.append({"original_process": before["process"], "process": client["process"],
                       "tty": client["tty"], "focus": client["focus"],
                       "input_recovery_path": str(path), "terminal_session_id": saved["persistent_identity"][1]})
    return proofs


def release_clients(directory, saved, observed):
    if observed["process"] != saved["process"]:
        raise ValueError("Original native terminal server changed before releasing clients")
    for client in saved.get("clients", []):
        actual = client_request(client["activation_id"])
        if actual["process"] != client["process"]:
            raise ValueError("Original native terminal client changed before release")
        if actual.get("checkpoint") is None:
            continue
        journal = directory / f"zellij-client-release-{client['process']['native_id']}.json"
        if journal.exists():
            raise ValueError("Native client release outcome is unconfirmed; no repeat sent")
        save(journal, {"state": "requested", "run_id": saved["run_id"], "process": client["process"]})
        client_request(client["activation_id"], "release_original",
                       expected_process=client["process"], run_id=saved["run_id"])


def server_control(directory, target, action, run_id):
    key = hashlib.sha256(target["process"]["native_id"].encode()).hexdigest()
    request = {"schema_version": 1, "action": action, "run_id": run_id,
               "expected_process": target["process"]}
    path = directory / "server-control" / f"{action}-{key}.json"
    intent = directory / "server-control" / f"intent-{action}-{key}.json"
    if action != "inventory" and intent.exists():
        recorded = read_private(intent)
        if recorded["request"] != request:
            raise ValueError("Retained native server control belongs to another operation")
        return server_control(directory, target, "inventory", run_id)
    save(path, request)
    if action != "inventory":
        save(intent, {"state": "requested", "request": request})
    result = subprocess.run([str((Path.home() / ".local/bin/zellij").resolve()),
                             "--activation-server-control", str(path), "--session", target["target"]],
                            capture_output=True, text=True, timeout=10)
    reply = json.loads(result.stdout)
    if reply.get("schema_version") != 1 or reply.get("error"):
        raise ValueError(reply.get("error", "Native server control contract changed"))
    if reply.get("process") != target["process"]:
        raise ValueError("Native server control incarnation differs")
    if result.returncode:
        raise ValueError("Native server control was not confirmed")
    if action != "inventory":
        save(intent, {"state": "observed", "request": request, "response": reply})
    return reply


def checkpoint_server(directory, target, run_id):
    server_control(directory, target, "checkpoint", run_id)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        reply = server_control(directory, target, "inventory", run_id)
        if (reply.get("run_id") != run_id or not reply.get("fenced")
                or reply.get("uncertain_authority") or reply.get("stop_accepted")):
            raise ValueError("Native server mutation authority cannot reach a safe checkpoint: "
                             + json.dumps({key: reply.get(key) for key in
                                           ("pending_authority", "uncertain_authority", "held_output_bytes", "unknown_clients")}))
        if reply.get("checkpoint") == {"state": "confirmed", "run_id": run_id} and reply.get("pending_authority") == 0:
            return reply
        time.sleep(0.05)
    raise ValueError("Native server mutation drain remains pending; no checkpoint repeat sent: "
                     + json.dumps({key: reply.get(key) for key in
                                   ("pending_authority", "uncertain_authority", "held_output_bytes", "unknown_clients")}))


def confirmed_server_fence(name, process):
    """Only an exact native operation checkpoint can replace plugin callbacks with readonly image inspection."""
    operation, run_id = os.environ.get("PROJECT_UPDATE_OPERATION_DIR"), os.environ.get("PROJECT_UPDATE_RUN_ID")
    if not operation or not run_id:
        return False
    directory = Path(operation)
    key = hashlib.sha256(process["native_id"].encode()).hexdigest()
    intent = directory / "server-control" / f"intent-checkpoint-{key}.json"
    if not intent.exists():
        return False
    reply = server_control(directory, {"target": name, "process": process}, "inventory", run_id)
    return (reply.get("run_id") == run_id and reply.get("fenced") is True
            and reply.get("checkpoint") == {"state": "confirmed", "run_id": run_id}
            and reply.get("pending_authority") == 0 and not reply.get("uncertain_authority")
            and not reply.get("stop_accepted"))


def native_activation(name):
    runtime = Path.home() / ".local/bin/zellij"
    result = subprocess.run([str(runtime), "--session", name, "action", "dump-layout",
                             "--activation-ids"], capture_output=True, text=True, timeout=10)
    if result.returncode:
        return None
    try:
        value = json.loads(result.stdout)
    except ValueError:
        return None  # Legacy servers ignore the additive activation query field.
    if value.get("schema_version") != 1 or not isinstance(value.get("layout"), str):
        raise ValueError("Native activation layout contract changed")
    return value


def location():
    override = os.environ.get("ZELLIJ_SOCKET_DIR")
    if override and not Path(override).is_absolute():
        raise ValueError("Zellij socket directory must be absolute")
    linux = platform.system() == "Linux"
    if not linux and platform.system() != "Darwin":
        raise ValueError("Native Zellij inventory supports macOS and Linux")
    if override:
        sockets = Path(override) / "contract_version_1"
    else:
        runtime = os.environ.get("XDG_RUNTIME_DIR") if linux else None
        sockets = (Path(runtime) / "zellij" if runtime else Path(tempfile.gettempdir()) / f"zellij-{os.getuid()}") / "contract_version_1"
    cache = (Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "zellij" if linux else
             Path.home() / "Library/Caches/org.Zellij-Contributors.Zellij")
    index = ("session_index-" + hashlib.sha256(os.fsencode(sockets)).hexdigest()[:12] + ".sqlite") if override else "session_index.sqlite"
    return sockets, cache / "contract_version_1" / index


def peer(sock):
    if platform.system() == "Linux":
        pid, uid, _gid = struct.unpack("3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    else:
        # Darwin's documented local socket options; getpeereid verifies UID.
        pid = sock.getsockopt(0, 2)
        libc = ctypes.CDLL(None, use_errno=True)
        libc.getpeereid.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
        libc.getpeereid.restype = ctypes.c_int
        uid_value, gid_value = ctypes.c_uint(), ctypes.c_uint()
        if libc.getpeereid(sock.fileno(), ctypes.byref(uid_value), ctypes.byref(gid_value)) != 0:
            raise OSError(ctypes.get_errno(), "Cannot verify the Zellij server owner")
        uid = uid_value.value
    if pid <= 0 or uid != os.getuid():
        raise ValueError("The Zellij server is not owned by this user")
    started = run(["ps", "-p", str(pid), "-o", "lstart="]).strip()
    if not started:
        raise ValueError("Zellij server start identity is unavailable")
    return pid, started


def sessions(expected):
    sockets, index = location()
    if not index.is_file():
        # A missing native index is unknown when an unindexed server exists.
        if sockets.is_dir() and any(path.is_socket() for path in sockets.iterdir()):
            raise ValueError("Live Zellij sockets have no trustworthy native index")
        return []
    with sqlite3.connect(f"file:{index}?mode=ro", uri=True) as connection:
        rows = connection.execute("SELECT name, COALESCE(id,name), created_at FROM sessions ORDER BY created_at").fetchall()
    result = []
    helper = shutil.which("zellij-context")
    for name, native_id, created in rows:
        if not isinstance(native_id, str) or "/" in native_id or native_id in (".", ".."):
            raise ValueError("Invalid native Zellij session identifier")
        path = sockets / native_id
        try:
            before = path.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISSOCK(before.st_mode) or before.st_uid != os.getuid():
            raise ValueError("Preserving unexpected Zellij session endpoint")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            try:
                client.connect(str(path))
            except ConnectionRefusedError:
                continue  # Only refusal establishes an exited native session.
            pid, started = peer(client)
        after = path.lstat()
        if (before.st_dev, before.st_ino, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_ctime_ns):
            raise ValueError("Zellij server incarnation changed during inventory")
        identity = json.dumps([str(path), str(before.st_dev), str(before.st_ino), str(before.st_ctime_ns)], separators=(",", ":"))
        process = {"pid": pid, "start_identity": started, "native_id": identity, "owner_verified": True}
        snapshot = json.loads(run([helper, "inspect", "--session", name, "--json"])) if helper else None
        available = isinstance(snapshot, dict) and snapshot.get("status") == "available"
        panes = snapshot.get("panes", []) if available else []
        blocked = [pane for pane in panes if not pane.get("is_plugin") and not pane.get("exited")]
        activation = native_activation(name) if available else None
        loaded, selected_plugins, loaded_plugins = None, {}, {}
        reason = "legacy-zellij-loaded-runtime-and-plugin-identities-unavailable"
        if activation is not None:
            runtime = running_runtime(pid)
            selected_runtime = immutable_runtime((Path.home() / ".local/bin/zellij").resolve())
            hashes = activation.get("loaded_images", {})
            fenced = confirmed_server_fence(name, process)
            for pane in panes:
                if not pane.get("is_plugin"):
                    continue
                url = pane.get("plugin_url")
                if isinstance(url, str) and url.startswith("zellij:"):
                    continue  # Built-ins belong to the verified immutable runtime.
                if not isinstance(url, str) or not url.startswith("file:"):
                    raise ValueError("Loaded external plugin image has no verifiable file identity")
                file = Path(url[5:])
                selected_plugins[url] = hashlib.sha256(file.read_bytes()).hexdigest()
                image = hashes.get(str(pane["id"]))
                if not isinstance(image, str) or len(image) != 64:
                    raise ValueError("Native loaded plugin hash is unavailable")
                if url in loaded_plugins and loaded_plugins[url] != image:
                    raise ValueError("Plugin client clones loaded different images")
                loaded_plugins[url] = image
                if file.name in ("lane-status.wasm", "copy-hop.wasm") and helper and not fenced:
                    replies = json.loads(run([helper, "activation-image", "--session", name,
                                              "--plugin", str(pane["id"])]))
                    if not replies or any(not reply.get("ready") for reply in replies):
                        raise ValueError("Loaded plugin is not ready for activation")
            if selected_runtime is not None and expected is not None:
                expected_target = artifact_identity(selected_runtime, selected_plugins)
            else:
                expected_target = expected
            if runtime is not None:
                loaded = artifact_identity(runtime, loaded_plugins)
                reason = None if loaded == expected_target else "selected-zellij-images-not-running"
        else:
            expected_target = expected
        clients = activation.get("clients") if activation is not None else None
        row = {
            "target": name, "native_session_id": native_id, "persistent_identity": [str(index), native_id, created],
            "expected_identity": expected_target, "running_identity": loaded,
            "ready": False,
            "native_ready": available,
            "connections": clients,
            "process": process,
            "sessions": [{"session_id": native_id, "restoration": "unchanged" if loaded is not None else "blocked",
                          "layout_identity": hashlib.sha256(json.dumps(snapshot.get("tabs", []) if available else [], sort_keys=True).encode()).hexdigest()}],
            "reason": reason,
            "uncheckpointed_panes": [{"pane_id": pane["id"], "cwd": pane.get("pane_cwd"),
                                     "reason": "native-application-checkpoint-unavailable"} for pane in blocked],
            "nested_targets": {str(pane["id"]): pane["nested_session_name"] for pane in panes
                               if pane.get("nested_session_name")},
            "_snapshot": snapshot,
            "_activation": activation,
        }
        if activation is not None:
            try:
                row["connections"] = observe_clients(clients, row)
                managed = all(client["managed"] for client in row["connections"])
                if managed and runtime is not None and selected_runtime is not None:
                    selected_connections = row["connections"]
                    operation = os.environ.get("PROJECT_UPDATE_OPERATION_DIR")
                    if operation:
                        frozen_path = Path(operation) / "zellij-inventory.json"
                        if frozen_path.exists():
                            frozen = next((value for value in read_private(frozen_path)["targets"]
                                           if value["target"] == name), None)
                            if frozen is not None and frozen.get("process") is not None:
                                path = checkpoint_path(frozen)
                                if path.exists():
                                    confirmed = read_private(path)
                                    if confirmed["state"] == "confirmed" and confirmed["run_id"] == os.environ.get("PROJECT_UPDATE_RUN_ID"):
                                        selected_connections = confirmed.get("clients", selected_connections)
                    selected_clients = {client_image_key(client): selected_runtime for client in selected_connections}
                    loaded_clients = {client_image_key(client): client["image_sha256"] for client in row["connections"]}
                    row["expected_identity"] = artifact_identity(selected_runtime, selected_plugins, selected_clients)
                    row["running_identity"] = artifact_identity(runtime, loaded_plugins, loaded_clients)
                    row["ready"] = available and row["running_identity"] == row["expected_identity"]
                    row["reason"] = None if row["ready"] else "selected-zellij-images-not-running"
                else:
                    row["running_identity"] = None
                    row["reason"] = "native-user-terminal-loaded-image-and-reconnect-checkpoint-unavailable"
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                row.update(ready=False, running_identity=None, reason=str(error))
        operation = os.environ.get("PROJECT_UPDATE_OPERATION_DIR")
        if operation:
            restored = Path(operation) / ("zellij-restored-" + hashlib.sha256(name.encode()).hexdigest() + ".json")
            if restored.exists():
                saved = read_private(restored)
                if saved["process"] == row["process"] and saved["persistent_identity"] == row["persistent_identity"]:
                    if activation is None or helper_input("activation-shape", activation["layout"]).strip() != saved["shape"]:
                        row.update(ready=False, reason="restored-native-layout-differs")
                    else:
                        row["sessions"][0].update(restoration="restored", layout_identity=saved["layout_identity"])
                        try:
                            checkpoint_saved = read_private(Path(operation) / saved["checkpoint_path"])
                            proofs = restored_applications(Path(operation), checkpoint_saved, row)
                            if proofs != saved.get("restored_applications"):
                                raise ValueError("Restored application process changed after terminal receipt")
                            row["restored_applications"] = proofs
                            clients = restored_clients(Path(operation), checkpoint_saved, row)
                            if clients != saved.get("restored_clients", []):
                                raise ValueError("Restored native terminal client changed after terminal receipt")
                            row["restored_clients"] = clients
                        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                            row.update(ready=False, reason=str(error))
        result.append(row)
    return result


def helper_input(operation, value):
    helper = shutil.which("zellij-context")
    if helper is None:
        raise ValueError("Native Zellij activation helper is not installed")
    result = subprocess.run([helper, operation], input=value, capture_output=True,
                            text=True, timeout=10)
    if result.returncode:
        raise ValueError(result.stderr.strip()[-1000:])
    return result.stdout


def checkpoint_path(target):
    key = hashlib.sha256(target["process"]["native_id"].encode()).hexdigest()
    return Path(os.environ["PROJECT_UPDATE_CHECKPOINT_DIR"]) / f"zellij-{key}.json"


def operation_bindings(directory, terminal):
    bindings = {}
    for file in directory.glob("*-inventory.json"):
        if file.name == "zellij-inventory.json":
            continue
        project = file.name.removesuffix("-inventory.json")
        for original in read_private(file).get("targets", []):
            for session in original.get("sessions", []):
                owner = session.get("restoration_owner", original.get("restoration_owner")) or {}
                if owner.get("project") != "zellij" or owner.get("target") not in (
                        terminal["target"], terminal["native_session_id"]):
                    continue
                pane = owner.get("pane_id")
                if type(pane) is not int or pane < 0 or pane in bindings:
                    raise ValueError("A native terminal pane must have one restoration owner")
                summary = directory / "checkpoints" / (
                    project + "-" + hashlib.sha256(original["target"].encode()).hexdigest() + ".json")
                confirmed = read_private(summary)[0]
                if confirmed.get("process") != original["process"] or confirmed.get("checkpoint") != {
                        "state": "confirmed", "run_id": os.environ["PROJECT_UPDATE_RUN_ID"]}:
                    raise ValueError("Native application checkpoint has not been confirmed")
                selected = next((saved for saved in confirmed["sessions"]
                                 if saved["session_id"] == session["session_id"]), None)
                if selected is None or selected.get("cwd") != session.get("cwd"):
                    raise ValueError("Native checkpoint application binding changed")
                bindings[pane] = {"project": project, "target": original["target"],
                                  "process": original["process"], "session": selected}
    return bindings


def checkpoint(target, original, directory, run_id):
    path = checkpoint_path(original)
    if path.exists():
        retained = read_private(path)
        if retained["run_id"] != run_id or retained["process"] != original["process"]:
            raise ValueError("An earlier terminal checkpoint still owns this server")
        target["checkpoint"] = {"state": retained["state"], "run_id": run_id}
        return target
    saved = {"schema_version": 1, "run_id": run_id, "target": target["target"],
             "process": target["process"], "persistent_identity": target["persistent_identity"],
             "snapshot": target["_snapshot"], "state": "refused",
             "layout_identity": target["sessions"][0]["layout_identity"]}
    try:
        if target["_activation"] is None or target["running_identity"] is None:
            raise ValueError("legacy-native-Zellij-activation-images-unavailable")
        capabilities = target["_activation"].get("activation_capabilities") or {}
        if any(capabilities.get(key) is not True for key in
               ("mutation_fence", "drain", "operation_bound_stop", "no_forced_children")):
            raise ValueError("Native Zellij server mutation checkpoint authority is unavailable")
        if not isinstance(target["connections"], list) or any(not client.get("managed") for client in target["connections"]):
            raise ValueError("native-user-terminal-reconnect-checkpoint-unavailable")
        saved["environment_baseline"] = baseline.request(sys.modules[__name__], "verify")
        saved["bindings"] = operation_bindings(directory, target)
        graph = {row["target"]: list(row.get("nested_targets", {}).values())
                 for row in read_private(directory / "zellij-inventory.json")["targets"]}
        def acyclic(name, visiting):
            if name in visiting or name not in graph:
                raise ValueError("Nested session graph is cyclic or has an unverified native target")
            for child in graph[name]:
                acyclic(child, visiting | {name})
        acyclic(target["target"], set())
        saved["nested_targets"] = target["nested_targets"]
        saved["nested_clients"] = {}
        for pane in target["_snapshot"]["panes"]:
            if pane.get("is_plugin") or pane.get("exited"):
                continue
            if pane.get("nested_session_name"):
                pid = target["_activation"].get("terminal_processes", {}).get(str(pane["id"]))
                if type(pid) is not int or running_runtime(pid) is None:
                    raise ValueError("Nested pane has no verified immutable native client owner")
                child = next((row for row in read_private(directory / "zellij-inventory.json")["targets"]
                              if row["target"] == pane["nested_session_name"]), None)
                if child is None or child.get("process") is None:
                    raise ValueError("Nested native server is absent from the frozen operation")
                saved["nested_clients"][str(pane["id"])] = {
                    "pid": pid, "start_identity": run(["ps", "-p", str(pid), "-o", "lstart="]).strip(),
                    "native_session_id": child["native_session_id"]}
                child_checkpoint = read_private(checkpoint_path(child))
                owner = {"project": "zellij", "target": target["native_session_id"], "pane_id": pane["id"]}
                client = next((row for row in child_checkpoint.get("clients", [])
                               if row.get("restoration_owner") == owner and row["process"]["pid"] == pid
                               and row.get("defer_to_parent")), None)
                if child_checkpoint["state"] != "confirmed" or child_checkpoint["run_id"] != run_id or client is None:
                    raise ValueError("Nested native client has no confirmed parent-pane handoff")
                saved["nested_clients"][str(pane["id"])]["process"] = client["process"]
                saved["nested_clients"][str(pane["id"])]["restoration_owner"] = owner
                continue
            if pane.get("is_held") and str(pane["id"]) not in target["_activation"].get("terminal_processes", {}):
                continue  # Native allocator owns this suspended pane; no process was launched.
            if pane["id"] not in saved["bindings"]:
                raise ValueError("native-application-checkpoint-unavailable")
        saved["layout"] = target["_activation"]["layout"]
        saved["shape"] = helper_input("activation-shape", saved["layout"]).strip()
        checkpoint_clients(directory, saved, target, original)
        saved["server_checkpoint"] = checkpoint_server(directory, target, run_id)
        final = next((row for row in sessions(expected_identity()) if row["target"] == target["target"]), None)
        if (final is None or final["process"] != target["process"]
                or final["persistent_identity"] != target["persistent_identity"]
                or final["expected_identity"] != original["expected_identity"]
                or final["nested_targets"] != saved["nested_targets"]
                or helper_input("activation-shape", final["_activation"]["layout"]).strip() != saved["shape"]
                or [client["process"] for client in final["connections"]] != [client["process"] for client in target["connections"]]
                or [client["focus"] for client in final["connections"]] != [client["focus"] for client in target["connections"]]):
            raise ValueError("Native terminal or client snapshot drifted before mutation authority fenced")
        saved["snapshot"] = final["_snapshot"]
        saved["layout"] = final["_activation"]["layout"]
        saved["state"] = "confirmed"
        target["sessions"][0]["restoration"] = "unchanged"
        target["reason"] = None
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        saved["reason"] = str(error)
        saved["state"] = "refused"
        saved.setdefault("layout", run([str(Path.home() / ".local/bin/zellij"),
                                        "--session", target["target"], "action", "dump-layout"])
                         if target["_snapshot"] else None)
        target["reason"] = str(error)
    save(path, saved)
    target["checkpoint"] = {"state": saved["state"], "run_id": run_id}
    return target


def process_alive(binding):
    result = subprocess.run(["ps", "-p", str(binding["pid"]), "-o", "lstart="],
                            capture_output=True, text=True, timeout=5,
                            env={**os.environ, "LC_ALL": "C", "TZ": "UTC"})
    if result.returncode:
        try:
            os.kill(binding["pid"], 0)
        except ProcessLookupError:
            return False
        raise ValueError("Native owner inspection failed; absence is unproven")
    observed = result.stdout.strip()
    if observed == binding["start_identity"]:
        return True
    if not re.fullmatch(r"[A-Z][a-z]{2} [A-Z][a-z]{2} [ \d]\d \d{2}:\d{2}:\d{2} \d{4}",
                        binding["start_identity"]):
        raise ValueError("Foreign native process identity requires authoritative retirement evidence")
    return False


def restore_intents(directory, saved):
    intents = {}
    for file in (directory / "checkpoints").glob("*-restore-*.json"):
        value = read_private(file)
        owner = value.get("restoration_owner") or {}
        if owner.get("project") != "zellij" or owner.get("target") not in (
                saved["target"], saved["persistent_identity"][1]):
            continue
        pane = owner.get("pane_id")
        binding = saved["bindings"].get(str(pane))
        if binding is None or pane in intents:
            raise ValueError("Unexpected or duplicate application restoration owner")
        if (value.get("state") != "confirmed" or value.get("run_id") != saved["run_id"]
                or value.get("process") != binding["process"]
                or value.get("session", {}).get("session_id") != binding["session"]["session_id"]
                or any(value["session"].get(key) != binding["session"].get(key)
                       for key in ("transcript_path", "branch_id", "cwd"))):
            raise ValueError("Native restoration intent differs from its frozen checkpoint")
        argv = value.get("restore_argv")
        environment = value.get("restore_env", {})
        if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
            raise ValueError("Native application launcher argv is unavailable")
        if not Path(argv[0]).is_absolute() or not all(isinstance(key, str) and isinstance(val, str)
                and key.replace("_", "").isalnum() and
                (key.endswith(("_CHECKPOINT", "_STATE_DIR", "_CONFIG", "_ATTEMPT", "_AGENT_DIR"))
                 or key == "PI_CODING_AGENT_DIR") for key, val in environment.items()):
            raise ValueError("Application restore environment is not restricted to nonsecret native bindings")
        if process_alive(value["process"]):
            raise ValueError("Application owner has not exited; terminal replacement is blocked")
        intents[pane] = value
        intents[pane]["project"] = binding["project"]
    if set(map(int, saved["bindings"])) != set(intents):
        raise ValueError("Native consumer restoration intents are incomplete")
    return intents


def prepare_layout(directory, saved):
    intents = restore_intents(directory, saved)
    panes = []
    for pane in saved["snapshot"]["panes"]:
        key = pane["id"]
        command = None
        nested = saved.get("nested_targets", {}).get(str(key))
        if not pane.get("is_plugin") and (key in intents or nested):
            if key in intents:
                intent = intents[key]
            else:
                client = saved["nested_clients"][str(key)]["process"]
                client_checkpoint = directory / f"zellij-client-{client['native_id']}.json"
                confirmed = read_private(client_checkpoint)
                if confirmed["run_id"] != saved["run_id"] or confirmed["process"] != client or not confirmed["defer_to_parent"]:
                    raise ValueError("Nested native restoration checkpoint differs")
                intent = {
                    "session": {"session_id": "zellij:" + nested, "cwd": pane.get("pane_cwd") or str(Path.home())},
                    "restore_argv": ["/usr/bin/env", "-u", "ZELLIJ",
                                     str((Path.home() / ".local/bin/zellij").resolve()), "--activation-client",
                                     "--activation-client-owner-restoration", str(client_checkpoint), "attach", nested],
                    "restore_env": {}}
            command = directory / f"zellij-pane-{saved['persistent_identity'][1]}-{key}.py"
            receipt = directory / f"zellij-pane-launch-{saved['persistent_identity'][1]}-{key}.json"
            source = ("#!"+sys.executable+"\nimport json, os, sys, subprocess\n"
                      f"path={str(receipt)!r}\n"
                      "try: fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)\n"
                      "except FileExistsError: sys.exit('Retained native launch intent: reconcile without replay')\n"
                      "started=subprocess.check_output(['ps','-p',str(os.getpid()),'-o','lstart='],text=True,env={**os.environ,'LC_ALL':'C','TZ':'UTC'}).strip()\n"
                      "wrapper={'pid':os.getpid(),'start_identity':started}\n"
                      "with os.fdopen(fd,'w') as out:\n"
                      f" out.write(json.dumps({{'run_id':{saved['run_id']!r},'session_id':{intent['session']['session_id']!r},'terminal_session_id':{saved['persistent_identity'][1]!r},'pane_id':int(os.environ['ZELLIJ_PANE_ID']),'wrapper_process':wrapper,'state':'requested'}})+'\\n');out.flush();os.fsync(out.fileno())\n"
                      "directory=os.open(os.path.dirname(path),os.O_RDONLY)\nos.fsync(directory)\nos.close(directory)\n"
                      f"for key,value in {intent.get('restore_env',{})!r}.items(): os.environ[key]=value\n"
                      f"argv={intent['restore_argv']!r}\nos.execv(argv[0],argv)\n")
            if command.exists() and command.read_text() != source:
                raise ValueError("Preserving a changed native application launcher")
            if not command.exists():
                command.write_text(source)
                command.chmod(0o700)
        if pane.get("is_suppressed"):
            if not pane.get("is_plugin"):
                raise ValueError("Suppressed terminal layouts require a native suppression checkpoint")
            continue  # Suppressed startup plugins are owned by native configuration.
        panes.append({"pane_id": key, "is_plugin": bool(pane.get("is_plugin")),
                      "title": pane.get("title", ""), "command": str(command) if command else None,
                      "cwd": intents[key]["session"]["cwd"] if key in intents else pane.get("pane_cwd")})
    layout = helper_input("activation-layout", json.dumps({"layout": saved["layout"], "panes": panes}))
    path = directory / f"zellij-layout-{saved['persistent_identity'][1]}.kdl"
    if path.exists() and path.read_text() != layout:
        raise ValueError("Preserving a changed retained terminal layout")
    if not path.exists():
        path.write_text(layout)
        path.chmod(0o600)
    return path


def finalize_nested(directory, parent):
    originals = {row["target"]: row for row in read_private(directory / "zellij-inventory.json")["targets"]}
    for name in parent.get("nested_targets", {}).values():
        original = originals[name]
        saved = read_private(checkpoint_path(original))
        key = hashlib.sha256(name.encode()).hexdigest()
        ready = read_private(directory / f"zellij-server-ready-{key}.json")
        deadline = time.monotonic() + 25
        failure = None
        while time.monotonic() < deadline:
            try:
                observed = next(row for row in sessions(expected_identity()) if row["target"] == name)
                if (observed["process"] != ready["process"] or ready["original_process"] != original["process"]
                        or observed["persistent_identity"] != original["persistent_identity"]
                        or not observed["ready"] or observed["expected_identity"] != original["expected_identity"]
                        or helper_input("activation-shape", observed["_activation"]["layout"]).strip() != saved["shape"]
                        or observed["_activation"].get("environment") != saved["environment_baseline"]["display"]):
                    raise ValueError("Nested native server incarnation, layout, images or baseline differs")
                applications = restored_applications(directory, saved, observed)
                clients = restored_clients(directory, saved, observed)
                record = {"schema_version": 1, "process": observed["process"],
                          "persistent_identity": saved["persistent_identity"], "shape": saved["shape"],
                          "layout_identity": saved["layout_identity"], "baseline": saved["environment_baseline"]["process"],
                          "checkpoint_path": str(checkpoint_path(original).relative_to(directory)),
                          "restored_applications": applications, "restored_clients": clients}
                save(receipt_path().parent / f"server-{saved['persistent_identity'][1]}.json", record)
                save(directory / f"zellij-restored-{key}.json", record)
                finalize_nested(directory, saved)
                break
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                failure = error
                time.sleep(0.05)
        else:
            raise ValueError(f"Nested native restoration remains unconfirmed: {failure}")


def replacement(target, original, directory, run_id, visiting=None):
    visiting = visiting or set()
    saved = read_private(checkpoint_path(original))
    if saved["state"] != "confirmed" or saved["run_id"] != run_id or saved["process"] != original["process"]:
        raise ValueError("A confirmed native terminal checkpoint is required")
    if target is not None and target["expected_identity"] != original["expected_identity"]:
        raise ValueError("Selected terminal artifacts changed before replacement")
    originals = {row["target"]: row for row in read_private(directory / "zellij-inventory.json")["targets"]}
    for client in saved.get("clients", []):
        if not client.get("defer_to_parent"):
            continue
        parent = next((row for row in originals.values()
                       if row["native_session_id"] == client["restoration_owner"]["target"]), None)
        if parent is None:
            raise ValueError("Native nested parent is absent from this operation")
        if parent["target"] not in visiting:
            current_parent = next((row for row in sessions(expected_identity()) if row["target"] == parent["target"]), None)
            replacement(current_parent, parent, directory, run_id, visiting)
            return next(row for row in sessions(expected_identity()) if row["target"] == original["target"])
    visiting = visiting | {original["target"]}
    layout = prepare_layout(directory, saved)
    key = hashlib.sha256(saved["target"].encode()).hexdigest()
    journal = directory / f"zellij-stop-{key}.json"
    if not journal.exists():
        if target is None or target["process"] != original["process"]:
            raise ValueError("Native terminal owner changed before graceful stop")
        if (target["_activation"] is None
                or helper_input("activation-shape", target["_activation"]["layout"]).strip() != saved["shape"]):
            raise ValueError("Native terminal layout changed after checkpoint; no stop sent")
        for pane in target["_snapshot"]["panes"]:
            if not pane.get("is_plugin") and not pane.get("exited"):
                nested = saved.get("nested_clients", {}).get(str(pane["id"]))
                if nested is not None:
                    if target["_activation"].get("terminal_processes", {}).get(str(pane["id"])) != nested["pid"] and process_alive(nested):
                        raise ValueError("Nested native client owner changed after checkpoint")
                    retirement = directory / f"zellij-client-retire-{nested['process']['native_id']}.json"
                    if not retirement.exists():
                        save(retirement, {"state": "requested", "run_id": run_id, "process": nested["process"]})
                        client_request(nested["process"]["native_id"], "retire_owned",
                                       expected_process=nested["process"], run_id=run_id,
                                       restoration_owner=nested["restoration_owner"])
                    confirmed = read_private(directory / f"zellij-client-{nested['process']['native_id']}.json")
                    if not confirmed.get("retire_submitted"):
                        raise ValueError("Nested native retirement remains unconfirmed; no repeat sent")
                    deadline = time.monotonic() + 10
                    while process_alive(nested) and time.monotonic() < deadline:
                        time.sleep(0.05)
                    if process_alive(nested):
                        raise ValueError("Owned nested native client has not settled; no terminal stop sent")
                    continue
                if pane.get("is_held") and str(pane["id"]) not in target["_activation"].get("terminal_processes", {}):
                    continue
                raise ValueError("An active pane owner has not settled; no terminal stop sent")
        current_clients = target["connections"]
        saved_clients = saved.get("clients", [])
        present_saved = [client for client in saved_clients if not client.get("defer_to_parent") or process_alive(client["process"])]
        if len(current_clients) != len(present_saved):
            raise ValueError("A terminal connection changed after checkpoint; no stop sent")
        for before_client in saved_clients:
            if before_client.get("defer_to_parent") and not process_alive(before_client["process"]):
                confirmed = read_private(directory / f"zellij-client-{before_client['process']['native_id']}.json")
                if not confirmed.get("retire_submitted"):
                    raise ValueError("Nested native retirement has no authoritative receipt")
                continue
            current_client = next((client for client in current_clients
                                   if client.get("process") == before_client["process"]), None)
            if (current_client is None or current_client.get("focus") != before_client["focus"]
                    or current_client.get("tty") != before_client["tty"]
                    or current_client.get("checkpoint") != {"state": "confirmed", "run_id": run_id}):
                raise ValueError("An uncheckpointed terminal client is connected; no terminal stop sent")
        save(journal, {"schema_version": 1, "state": "requested", "process": original["process"],
                       "run_id": run_id})
        reply = server_control(directory, target, "stop", run_id)
        if not reply.get("stop_accepted"):
            raise ValueError("Native server guarded retirement was refused; no stop repeat sent")
    elif read_private(journal)["process"] != original["process"]:
        raise ValueError("A retained terminal stop belongs to another incarnation")
    deadline = time.monotonic() + 25
    while process_alive(original["process"]) and time.monotonic() < deadline:
        time.sleep(0.05)
    if process_alive(original["process"]):
        raise ValueError("Native terminal shutdown outcome is unconfirmed; no stop retry sent")
    # Outer owners stop first; child servers and layouts return before inner clients are launched.
    for child in saved.get("nested_targets", {}).values():
        if child in visiting or child not in originals:
            raise ValueError("Nested attachment graph cannot be safely restored")
        current = next((row for row in sessions(expected_identity()) if row["target"] == child), None)
        before = originals[child]
        if current is not None and current["ready"] and current["process"] == before["process"]:
            continue
        restored = directory / ("zellij-restored-" + hashlib.sha256(child.encode()).hexdigest() + ".json")
        if restored.exists() and current is not None and current["process"] == read_private(restored)["process"] and current["ready"]:
            continue
        replacement(current, before, directory, run_id, visiting)
    launch = directory / f"zellij-launch-{key}.json"
    if not launch.exists():
        baseline.request(sys.modules[__name__], "launch", operation_directory=str(directory),
                         layout=str(layout), target=saved["target"], run_id=run_id)
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        observed = next((row for row in sessions(expected_identity()) if row["target"] == saved["target"]), None)
        if observed is not None and observed["native_ready"]:
            if observed["persistent_identity"] != saved["persistent_identity"]:
                raise ValueError("Restored terminal persistent native identity changed")
            if observed["process"] == original["process"]:
                raise ValueError("Old terminal incarnation still owns the restored session")
            actual_shape = (helper_input("activation-shape", observed["_activation"]["layout"]).strip()
                            if observed["_activation"] is not None else None)
            if actual_shape != saved["shape"]:
                save(directory / f"zellij-layout-drift-{key}.json", {
                    "schema_version": 1, "run_id": run_id, "original_process": original["process"],
                    "observed_process": observed["process"], "persistent_identity": observed["persistent_identity"],
                    "expected_layout": saved["layout"], "observed_layout": (observed["_activation"] or {}).get("layout"),
                    "expected_shape": saved["shape"], "observed_shape": actual_shape,
                    "observed_connections": observed["connections"]})
                raise ValueError("Restored native terminal layout differs")
            if observed["_activation"].get("environment") != saved["environment_baseline"]["display"]:
                raise ValueError("Native server did not inherit the verified terminal display environment")
            observed["sessions"][0].update(restoration="restored", layout_identity=saved["layout_identity"])
            try:
                proofs = restored_applications(directory, saved, observed)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                time.sleep(0.05)
                continue  # Read-only reconciliation; never repeat a launch.
            observed["restored_applications"] = proofs
            ready_path = directory / f"zellij-server-ready-{key}.json"
            if not ready_path.exists():
                save(ready_path, {"schema_version": 1, "run_id": run_id,
                                  "original_process": original["process"], "process": observed["process"]})
            elif read_private(ready_path)["process"] != observed["process"]:
                raise ValueError("A retained native client handoff belongs to another server")
            try:
                clients = restored_clients(directory, saved, observed,
                                           deferred=any(client.get("defer_to_parent") for client in saved.get("clients", [])))
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                time.sleep(0.05)
                continue
            if any(client.get("defer_to_parent") for client in saved.get("clients", [])):
                observed["ready"] = False
                observed["sessions"][0]["restoration"] = "pending"
                return observed  # Its already-stopped parent owns the missing connection launch.
            if observed["expected_identity"] != original["expected_identity"] or not observed["ready"]:
                raise ValueError("Restored native runtime, plugin or client image differs from selected artifacts")
            observed["restored_clients"] = clients
            record = {"schema_version": 1, "process": observed["process"],
                      "persistent_identity": saved["persistent_identity"], "shape": saved["shape"],
                      "layout_identity": saved["layout_identity"], "baseline": saved["environment_baseline"]["process"],
                      "checkpoint_path": str(checkpoint_path(original).relative_to(directory)),
                      "restored_applications": proofs, "restored_clients": clients}
            save(receipt_path().parent / f"server-{saved['persistent_identity'][1]}.json", record)
            save(directory / f"zellij-restored-{key}.json", record)
            finalize_nested(directory, saved)
            return observed
        time.sleep(0.05)
    raise ValueError("Native terminal launch remains unconfirmed; no launch replay sent")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("stage", "baseline-serve", "inventory", "checkpoint", "restart", "restore", "verify"):
        raise ValueError("Usage: zellij-activation.py stage|baseline-serve|inventory|checkpoint|restart|restore|verify")
    action = sys.argv[1]
    if action == "baseline-serve":
        baseline.serve(sys.modules[__name__])
        return 0
    if action == "stage":
        files = artifacts()
        identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        save(receipt_path(), {"schema_version": 1, "identity": identity, "artifacts": files})
        return 0
    expected = expected_identity()
    targets = sessions(expected)
    if not targets:
        executable = shutil.which("zellij")
        correct = executable is not None and Path(executable).resolve() == (Path.home() / ".local/bin/zellij").resolve()
        targets = [{"target": "local", "expected_identity": expected, "running_identity": expected if correct else None,
                    "ready": expected is not None and correct, "process": None, "sessions": [],
                    "reason": "selected-zellij-executable-or-artifact-identity-unavailable" if expected is None or not correct else None}]
    selected = os.environ.get("PROJECT_UPDATE_TARGET")
    if selected:
        targets = [target for target in targets if target["target"] == selected]
    for target in targets:
        target["session_replacement_supported"] = False
    if action in ("checkpoint", "restart", "restore"):
        # Native mode/layout restoration is unfinished. Refuse before any
        # checkpoint, stop, exec, application launch, or recovery mutation.
        for target in targets:
            target.update(ready=False, reason="zellij-session-restoration-not-supported",
                          checkpoint={"state": "refused",
                                      "run_id": os.environ.get("PROJECT_UPDATE_RUN_ID")})
            target.pop("_snapshot", None)
            target.pop("_activation", None)
        print(json.dumps({"schema_version": 1, "targets": targets,
                          "reason": "zellij-session-restoration-not-supported"}))
        return 3
    if action in ("checkpoint", "restart", "restore"):
        run_id = os.environ.get("PROJECT_UPDATE_RUN_ID")
        if not run_id or str(uuid.UUID(run_id)) != run_id:
            raise ValueError("A detached activation operation is required")
        directory = Path(os.environ["PROJECT_UPDATE_OPERATION_DIR"])
        frozen = read_private(directory / "zellij-inventory.json")
        original = {target["target"]: target for target in frozen["targets"]}
        observed = {target["target"]: target for target in targets}
        selected_originals = [value for key, value in original.items() if not selected or key == selected]
        if action == "checkpoint" and len(selected_originals) != 1:
            raise ValueError("Checkpoint must select exactly one frozen terminal target")
        targets = []
        for before in selected_originals:
            target = observed.get(before["target"])
            try:
                if before["process"] is None:
                    target = {**before, "checkpoint": {"state": "confirmed", "run_id": run_id}}
                elif action == "checkpoint":
                    if target is None or before["process"] != target["process"] or before["expected_identity"] != target["expected_identity"]:
                        raise ValueError("zellij-process-or-selected-artifact-changed")
                    target = checkpoint(target, before, directory, run_id)
                elif os.environ.get("PROJECT_UPDATE_RECOVER_ORIGINAL") == "1":
                    if target is None or target["process"] != before["process"]:
                        raise ValueError("Original terminal incarnation is unavailable")
                    path = checkpoint_path(before)
                    if path.exists():
                        retained = read_private(path)
                        key = hashlib.sha256(before["process"]["native_id"].encode()).hexdigest()
                        server_intent = directory / "server-control" / f"intent-checkpoint-{key}.json"
                        if retained.get("server_checkpoint") or server_intent.exists():
                            reply = server_control(directory, target, "release_original", run_id)
                            if reply.get("fenced") or reply.get("stop_accepted"):
                                raise ValueError("Original native server admission could not be released")
                        release_clients(directory, retained, target)
                    target["sessions"][0]["restoration"] = "unchanged"
                else:
                    key = hashlib.sha256(before["target"].encode()).hexdigest()
                    restored = directory / f"zellij-restored-{key}.json"
                    if restored.exists():
                        record = read_private(restored)
                        expected_process = os.environ.get("PROJECT_UPDATE_EXPECTED_PROCESS")
                        if target is None or target["process"] != record["process"] or (
                                action == "restore" and expected_process and json.loads(expected_process) != target["process"]):
                            raise ValueError("Restored native terminal incarnation changed")
                    else:
                        target = replacement(target, before, directory, run_id)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                target = {**(target or before), "ready": False, "reason": str(error),
                          "checkpoint": {"state": "refused", "run_id": run_id}}
            targets.append(target)
    if not targets:
        raise ValueError("The inventoried Zellij target disappeared")
    for target in targets:
        target.pop("_snapshot", None)
        target.pop("_activation", None)
    print(json.dumps({"schema_version": 1, "targets": targets}))
    complete = all(target["ready"] and target["expected_identity"] is not None and
                   target["expected_identity"] == target["running_identity"] for target in targets)
    confirmed = action == "checkpoint" and all(target.get("checkpoint", {}).get("state") == "confirmed" for target in targets)
    if action == "checkpoint":
        return 0 if confirmed else 3
    return 0 if action == "inventory" or complete or confirmed else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
        print(f"Zellij activation: {error}", file=sys.stderr)
        print(json.dumps({"schema_version": 1, "targets": [{
            "target": "local", "expected_identity": None, "running_identity": None,
            "ready": False, "process": None, "sessions": [],
            "reason": f"native-zellij-inventory-unavailable: {error}",
        }]}))
        sys.exit(3)
