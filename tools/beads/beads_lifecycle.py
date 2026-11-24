"""Native Beads supervisor activation and process-bound checkpoints."""

import hashlib
import fcntl
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import threading
import uuid


def artifact_identity(home, program=None, binaries=None):
    share = home / ".local/share/beads-service"
    program = (share / "beads-service.py").resolve().parent if program is None else program
    manifest = program / "runtime.json"
    binaries = json.loads(manifest.read_text()) if binaries is None else binaries
    parts = {name: hashlib.sha256((program / name).read_bytes()).hexdigest()
             for name in ("beads-service.py", "beads_config.py", "beads_lifecycle.py", "runtime.json")}
    parts.update({name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name, path in binaries.items()})
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def process_identity(pid):
    if type(pid) is not int or pid <= 0:
        raise ValueError("Invalid native process PID")
    if Path("/proc").is_dir():
        path = Path(f"/proc/{pid}/stat")
        info = path.stat()
        if info.st_uid != os.getuid():
            raise ValueError("Process is not owned")
        fields = path.read_text().rsplit(")", 1)[1].split()
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return f"{boot}-{fields[19]}"
    result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "uid=", "-o", "lstart="],
                            capture_output=True, text=True, check=True,
                            env={**os.environ, "LC_ALL": "C", "TZ": "UTC"})
    owner, start = result.stdout.strip().split(maxsplit=1)
    if int(owner) != os.getuid():
        raise ValueError("Process is not owned")
    return start


def loaded_binary_identity(pid, path):
    """Bind the child image to an immutable installed executable, not its name."""
    path = Path(path).resolve()
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o222:
        raise ValueError("Child executable must be an immutable installed binary")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if Path("/proc").is_dir():
        loaded = Path(f"/proc/{pid}/exe")
        image = loaded.stat()
        if (image.st_dev, image.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("Executed child image differs from the selected binary")
        if hashlib.sha256(loaded.read_bytes()).hexdigest() != digest:
            raise ValueError("Executed child image changed")
    else:
        result = subprocess.run(
            ["/usr/sbin/lsof", "-a", "-p", str(pid), "-d", "txt", "-F", "Dfin"],
            capture_output=True, text=True, check=True)
        images, item = [], {}
        for line in result.stdout.splitlines():
            if line.startswith("f"):
                if item:
                    images.append(item)
                item = {}
            elif line[:1] in ("D", "i", "n"):
                item[line[0]] = line[1:]
        images.append(item)
        if not any(int(image.get("D", "0"), 16) == before.st_dev
                   and int(image.get("i", "0")) == before.st_ino for image in images):
            raise ValueError("Executed child vnode differs from the selected binary")
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("Selected executable changed while binding the child")
    return digest


def socket_path(home):
    path = home / ".local/state/beads-service/lifecycle/control.sock"
    if len(str(path).encode()) >= 100:
        key = hashlib.sha256(str(home.resolve()).encode()).hexdigest()[:24]
        path = Path("/tmp") / f"beads-lifecycle-{os.getuid()}" / f"{key}.sock"
    return path


class Control:
    """Only the supervisor owning the Popen children may request their stop."""

    def __init__(self, home, ready, program=None, binaries=None):
        self.home, self.ready = home, ready
        self.artifact = (artifact_identity(home, program, binaries)
                         if program is not None and program.parent.name == "releases" else None)
        self.process = {"pid": os.getpid(), "start_identity": process_identity(os.getpid()),
                        "native_id": str(uuid.uuid4()), "owner_verified": True}
        self.lock = threading.Lock()
        self.run_id = None
        self.checkpoint = None
        self.children = []
        self.children_bound = False
        self.history_lock = None
        self.requested = threading.Event()
        self.finished = threading.Event()
        self.closed = threading.Event()
        self.cancelled_pids = set()
        self.retirement_policy = (self.artifact is not None and
                                  os.environ.get("PROJECT_UPDATE_RETIREMENT_POLICY") == "successful-exit")
        self.stop_accepted = False
        self.retired = threading.Event()
        path = socket_path(home)
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = path.parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Beads lifecycle directory must be private and owned")
        if path.exists():
            info = path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError("Preserve unexpected Beads lifecycle endpoint")
            with socket.socket(socket.AF_UNIX) as probe:
                try:
                    probe.connect(str(path))
                except ConnectionRefusedError:
                    if path.lstat().st_ino != info.st_ino:
                        raise ValueError("Beads lifecycle endpoint changed") from None
                    path.unlink()
                else:
                    raise ValueError("Preserve live Beads lifecycle endpoint")
        self.listener = socket.socket(socket.AF_UNIX)
        self.listener.bind(str(path))
        path.chmod(0o600)
        self.socket_identity = path.lstat()
        self.listener.listen()
        self.listener.settimeout(0.2)
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def snapshot(self, expected=None):
        if expected is None:
            try:
                expected = artifact_identity(self.home)
            except (OSError, ValueError):
                pass
        with self.lock:
            target = {"target": "local", "expected_identity": expected,
                      "running_identity": self.artifact if self.children_bound else None,
                      "ready": self.run_id is None and self.ready(),
                      "process": self.process, "sessions": [], "children": self.children,
                      "retirement_policy": "successful-exit" if self.retirement_policy else "unknown",
                      "stop_accepted": self.stop_accepted}
            if self.checkpoint is not None:
                target["checkpoint"] = self.checkpoint
            if self.run_id is not None:
                target["reason"] = "beads-checkpointed"
            if self.artifact is None:
                target["reason"] = "executed-beads-controller-is-not-an-immutable-release"
            return {"schema_version": 1, "targets": [target]}

    def bind_children(self, children, binaries):
        records = []
        try:
            for child, name in zip(children, ("dolt", "bd"), strict=True):
                records.append({"pid": child.pid, "start_identity": process_identity(child.pid),
                                "artifact_identity": loaded_binary_identity(child.pid, binaries[name])})
        except (OSError, ValueError, subprocess.SubprocessError):
            # Development scripts and legacy mutable binaries remain usable,
            # but never gain authority to checkpoint as a managed release.
            self.artifact = None
            records = [{"pid": child.pid, "start_identity": process_identity(child.pid)}
                       for child in children]
        with self.lock:
            self.children = records
            self.children_bound = self.artifact is not None

    def serve(self):
        while not self.closed.is_set():
            try:
                conn, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self.handle, args=(conn,), daemon=True).start()

    def handle(self, conn):
        with conn:
            conn.settimeout(60)
            request = {}
            try:
                with conn.makefile("r") as stream:
                    line = stream.readline(16385)
                    if len(line) > 16384:
                        return
                    request = json.loads(line)
                action = request.get("action")
                if action not in ("inventory", "verify", "checkpoint", "stop"):
                    raise ValueError("Unsupported Beads lifecycle action")
                if action == "checkpoint":
                    with self.lock:
                        if not self.retirement_policy:
                            raise ValueError("Loaded retirement policy unknown; preserve this Beads owner")
                        if self.stop_accepted:
                            raise ValueError("Beads retirement is irrevocable")
                        if self.artifact is None or not self.children_bound:
                            raise ValueError("Unverified controller artifact; preserve this process")
                        if request.get("process") != self.process:
                            raise ValueError("Beads process incarnation changed")
                        run_id = request.get("run_id")
                        if not isinstance(run_id, str) or str(uuid.UUID(run_id)) != run_id:
                            raise ValueError("Invalid operation identity")
                        if self.run_id is not None and self.run_id != run_id:
                            raise ValueError("Another update owns this Beads checkpoint")
                        if self.run_id is None:
                            history = self.home / ".local/state/beads-service/history.lock"
                            lock = history.open("a")
                            try:
                                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            except BlockingIOError:
                                lock.close()
                                raise ValueError("Preserve the active Beads history operation") from None
                            self.history_lock = lock
                            self.run_id = run_id
                            self.checkpoint = {"state": "pending", "run_id": run_id,
                                               "effect_disposition": "interrupted-or-unknown; never replay"}
                            self.requested.set()
                    self.finished.wait(59)
                elif action == "stop":
                    with self.lock:
                        if (request.get("process") != self.process or not self.retirement_policy
                                or not self.finished.is_set() or self.run_id is None
                                or request.get("run_id") != self.run_id):
                            raise ValueError("Confirmed native checkpoint and retirement policy required")
                        # Fence before replying; duplicate requests only observe this decision.
                        self.stop_accepted = True
                conn.sendall((json.dumps(self.snapshot()) + "\n").encode())
            except (OSError, ValueError, KeyError) as error:
                # A refused control request must carry no authority to stop.
                target = self.snapshot()["targets"][0]
                target.update(reason=str(error), checkpoint={"state": "refused", "run_id": request.get("run_id")})
                try:
                    conn.sendall((json.dumps({"schema_version": 1, "targets": [target]}) + "\n").encode())
                except OSError:
                    pass
            finally:
                if request.get("action") == "stop" and self.stop_accepted:
                    self.retired.set()

    def checkpoint_children(self, children):
        if not self.requested.is_set() or self.finished.is_set():
            return
        for child in reversed(children):
            if child.poll() is None:
                if child.pid not in self.cancelled_pids:
                    child.terminate()
                    self.cancelled_pids.add(child.pid)
                # A subsequent tick only observes this pending cancellation.
                # The database is preserved until HTTP exit is confirmed.
                return
        with self.lock:
            self.checkpoint["state"] = "confirmed"
        self.finished.set()

    def close(self):
        self.closed.set()
        self.listener.close()
        self.thread.join(timeout=1)
        path = socket_path(self.home)
        try:
            current = path.lstat()
            if (current.st_dev, current.st_ino) == (self.socket_identity.st_dev, self.socket_identity.st_ino):
                path.unlink()
        except FileNotFoundError:
            pass
        if self.history_lock is not None:
            self.history_lock.close()


def inspect(home, action):
    try:
        expected = artifact_identity(home)
    except (OSError, ValueError):
        expected = None
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(60 if action == "checkpoint" else 3)
        conn.connect(str(socket_path(home)))
        request = {"action": action}
        if action in ("checkpoint", "stop"):
            request.update(run_id=os.environ.get("PROJECT_UPDATE_RUN_ID"),
                           process=json.loads(os.environ.get("PROJECT_UPDATE_EXPECTED_PROCESS", "null")))
        conn.sendall((json.dumps(request) + "\n").encode())
        with conn.makefile("r") as stream:
            response = json.loads(stream.readline(1 << 20))
    response["targets"][0]["expected_identity"] = expected
    return response
