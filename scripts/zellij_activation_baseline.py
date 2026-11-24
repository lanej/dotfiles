#!/usr/bin/env python3
"""Launch interactive Zellij servers through independent terminal inheritance."""

import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import uuid


def serve(api):
    if not os.isatty(0) or os.environ.get("ZELLIJ"):
        raise ValueError("Baseline must originate in an unaffected user terminal")
    rows = api.run(["ps", "-axo", "pid=,ppid=,comm="]).splitlines()
    processes = {}
    for row in rows:
        fields = row.strip().split(None, 2)
        if len(fields) == 3:
            processes[int(fields[0])] = (int(fields[1]), Path(fields[2]).name)
    ancestry, current = [], os.getppid()
    while current > 1 and len(ancestry) < 64:
        parent, name = processes[current]
        ancestry.append({"pid": current, "name": name})
        current = parent
    fixture = os.environ.get("PROJECT_UPDATE_ALLOW_DISPOSABLE") == "1"
    if fixture and not any(Path.home().is_relative_to(Path(root).resolve())
                           for root in ("/tmp", "/private/tmp")):
        raise ValueError("A disposable baseline must have an isolated temporary HOME")
    if not fixture:
        if any(row["name"].lower() in ("zellij", "codex", "claude", "bun", "node")
               or "codex" in row["name"].lower() for row in ancestry):
            raise ValueError("Agent runners or affected session ancestors cannot supply a baseline")
        if not any(row["name"].lower() in ("kitty", "terminal", "iterm2", "alacritty", "wezterm-gui", "sshd")
                   for row in ancestry):
            raise ValueError("Independent terminal launcher ancestry was not verified")
        if not any(row["name"].lstrip("-") in ("zsh", "bash", "fish", "sh") for row in ancestry):
            raise ValueError("Independent user-shell ancestry was not verified")
    directory = api.receipt_path().parent
    api.private_directory(directory)
    native = str(uuid.uuid4())
    path = directory / f"baseline-{os.getpid()}.sock"
    started = api.run(["ps", "-p", str(os.getpid()), "-o", "lstart="]).strip()
    binding = {"pid": os.getpid(), "start_identity": started, "native_id": native,
               "owner_verified": True}
    record = {"schema_version": 1, "socket": str(path), "process": binding,
              "ancestry": ancestry, "disposable": fixture,
              "home": str(Path.home()), "socket_namespace": str(api.location()[0]),
              "display": {key: os.environ.get(key) for key in
                          ("TERM", "COLORTERM", "NO_COLOR", "GIT_PAGER")}}
    metadata = directory / "baseline.json"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        path.chmod(0o600)
        server.listen(4)
        api.save(metadata, record)
        def stop(_signal, _frame):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGHUP, stop)
        try:
            while True:
                connection, _address = server.accept()
                with connection:
                    connection.settimeout(10)
                    try:
                        api.peer(connection)
                        raw = bytearray()
                        while b"\n" not in raw and len(raw) <= 16_384:
                            chunk = connection.recv(4096)
                            if not chunk:
                                break
                            raw.extend(chunk)
                        request = json.loads(raw.split(b"\n", 1)[0])
                        if request.get("native_id") != native:
                            raise ValueError("Independent terminal baseline incarnation changed")
                        if request["action"] == "verify":
                            reply = record
                        elif request["action"] == "launch":
                            operation = Path(request["operation_directory"])
                            api.private_directory(operation)
                            layout = Path(request["layout"])
                            info = layout.lstat()
                            if layout.parent != operation or not info.st_mode & 0o400:
                                raise ValueError("Launch layout must belong to the private operation")
                            # The native client also rejects symlinks and public layout files.
                            runtime = Path.home() / ".local/bin/zellij"
                            if api.immutable_runtime(runtime.resolve()) is None:
                                raise ValueError("Selected runtime is not an immutable image")
                            target = request["target"]
                            key = api.hashlib.sha256(target.encode()).hexdigest()
                            journal = operation / f"zellij-launch-{key}.json"
                            if journal.exists():
                                raise ValueError("A retained launch intent must be reconciled without repeating launch")
                            intent = {"schema_version": 1, "run_id": request["run_id"],
                                      "target": target, "baseline": binding, "state": "requested",
                                      "layout": str(layout)}
                            api.save(journal, intent)
                            # env=None deliberately inherits the independent terminal's entire
                            # environment. No runner values or credential values are read.
                            process = subprocess.Popen([str(runtime), "attach", "--create-background",
                                                   target, "--activation-layout", str(layout)],
                                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                                  stderr=subprocess.DEVNULL)
                            try:
                                result = process.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                # Retain uncertainty. Do not signal or repeat a native launch.
                                reply = {**intent, "state": "unknown"}
                            else:
                                reply = {**intent, "state": "started" if result == 0 else "failed",
                                         "exit_code": result}
                                api.save(journal, reply)
                        else:
                            raise ValueError("Unsupported independent terminal request")
                        connection.sendall((json.dumps(reply) + "\n").encode())
                    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                        connection.sendall((json.dumps({"error": str(error)}) + "\n").encode())
        except KeyboardInterrupt:
            pass
        finally:
            path.unlink(missing_ok=True)
            if metadata.exists() and api.read_private(metadata).get("process") == binding:
                metadata.unlink()


def request(api, action, **values):
    record = api.read_private(api.receipt_path().parent / "baseline.json")
    if record["home"] != str(Path.home()) or record["socket_namespace"] != str(api.location()[0]):
        raise ValueError("Terminal baseline belongs to another user or socket namespace")
    if record.get("disposable") and os.environ.get("PROJECT_UPDATE_ALLOW_DISPOSABLE") != "1":
        raise ValueError("A disposable fixture is not a user-terminal baseline")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(35)
        connection.connect(record["socket"])
        pid, started = api.peer(connection)
        if pid != record["process"]["pid"] or started != record["process"]["start_identity"]:
            raise ValueError("Independent terminal baseline owner changed")
        connection.sendall((json.dumps({"action": action,
                                       "native_id": record["process"]["native_id"],
                                       **values}) + "\n").encode())
        raw = bytearray()
        while b"\n" not in raw and len(raw) <= 64 * 1024:
            chunk = connection.recv(4096)
            if not chunk:
                break
            raw.extend(chunk)
        reply = json.loads(raw.split(b"\n", 1)[0])
        if "error" in reply:
            raise ValueError(reply["error"])
        return reply
