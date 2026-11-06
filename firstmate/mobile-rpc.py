#!/usr/bin/env python3
"""Serialize mobile captain launches while Pi retains the RPC streams."""

import fcntl
import hashlib
import os
from pathlib import Path
import pty
import select
import signal
import shutil
import struct
import subprocess
import sys
import termios
import threading
import time


def hold_lease(command):
    """Keep the inherited launch lease until the actual Pi child exits."""
    child = None
    pending = None
    shutdown_deadline = None
    def forward(signum, _frame):
        nonlocal pending, shutdown_deadline
        pending = signum
        if shutdown_deadline is None:
            shutdown_deadline = time.monotonic() + 15
        if child is not None and child.poll() is None:
            child.send_signal(signum)
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, forward)
    try:
        child = subprocess.Popen(command)
        if pending:
            child.send_signal(pending)
        while child.poll() is None:
            remaining = None if shutdown_deadline is None else shutdown_deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                child.kill()
                return child.wait()
            try:
                return child.wait(timeout=0.25 if remaining is None else remaining)
            except subprocess.TimeoutExpired:
                pass
        return child.returncode
    finally:
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if len(sys.argv) > 1 and sys.argv[1] == "--hold-lease":
    # WHY: Retain the lease independently of Pi's descriptor handling.
    os.set_inheritable(int(sys.argv[2]), False)
    sys.exit(hold_lease(sys.argv[3:]))


def crew_client(session, create=True):
    """Keep a private viewport for background tabs; no Paseo terminal is created."""
    environment = dict(os.environ, TERM="xterm-256color")
    for name in ("TMUX", "TMUX_PANE", "ZELLIJ", "ZELLIJ_PANE_ID", "ZELLIJ_SESSION_NAME"):
        environment.pop(name, None)
    if create:
        sessions = subprocess.run(["zellij", "list-sessions", "--short", "--no-formatting"],
                                  env=environment, capture_output=True, text=True, timeout=5)
        if session not in sessions.stdout.splitlines():
            # WHY: A background server survives losing the attached client's controlling terminal.
            subprocess.run(["zellij", "attach", "--create-background", session, "--", "sleep", "2147483647"],
                           env=environment, stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=10)
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 160, 0, 0))
    client = subprocess.Popen(
        ["zellij", "attach", session, "options", "--on-force-close", "detach"],
        stdin=slave, stdout=slave, stderr=slave, env=environment, start_new_session=True,
        preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0),
    )
    os.close(slave)
    stopped = threading.Event()

    def drain():
        while not stopped.is_set():
            try:
                if select.select([master], [], [], 0.1)[0] and not os.read(master, 65536):
                    break
            except OSError:
                break

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()

    def close():
        client.terminate()
        try:
            client.wait(timeout=2)
        except subprocess.TimeoutExpired:
            client.kill()
            client.wait()
        stopped.set()
        reader.join(timeout=1)
        os.close(master)

    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if client.poll() is not None:
                raise RuntimeError("The Firstmate crew client exited during startup")
            clients = subprocess.run(["zellij", "--session", session, "action", "list-clients"],
                                     capture_output=True, text=True, timeout=2)
            if len(clients.stdout.strip().splitlines()) >= 2:
                return close, lambda: client.poll() is None and reader.is_alive()
            time.sleep(0.1)
        raise RuntimeError("The Firstmate crew viewport did not become ready")
    except BaseException:
        close()
        raise


home = Path(os.environ["FIRSTMATE_HOME"])
state = home / "state"
state.mkdir(parents=True, exist_ok=True)
with open(str(state / ".mobile-rpc.lock"), "a") as lock:
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("A mobile Firstmate captain is already running. Resume its existing Paseo conversation.")
    adapter = Path(__file__).resolve().parent.parent / "scripts/firstmate-feedback-native.sh"
    subprocess.run(["bash", str(adapter), str(home), "primary-available"], check=True)
    session = os.environ.get("FM_ZELLIJ_SESSION") or "firstmate-crew-" + hashlib.sha256(str(home).encode()).hexdigest()[:12]
    os.environ["FM_ZELLIJ_SESSION"] = session
    if not session or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for char in session):
        sys.exit("Invalid Zellij crew session name")
    # WHY: Zellij 0.46 creates zero-sized new tabs without an attached viewport.
    close_crew, crew_healthy = crew_client(session)
    child = awake = None
    pending_signal = None
    def forward(signum, _frame):
        global pending_signal
        if child is None:
            pending_signal = signum
        elif child.poll() is None:
            child.send_signal(signum)
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, forward)
    try:
        # WHY: The lease parent survives wrapper loss and waits for its own Pi child.
        child = subprocess.Popen([sys.executable, __file__, "--hold-lease", str(lock.fileno()), *sys.argv[1:]],
                                 cwd=str(home), pass_fds=(lock.fileno(),))
        if pending_signal:
            child.send_signal(pending_signal)
        awake = subprocess.Popen(["caffeinate", "-i", "-s", "-w", str(child.pid)]) if sys.platform == "darwin" and shutil.which("caffeinate") else None
        while child.poll() is None:
            try:
                child.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                if not crew_healthy():
                    close_crew()
                    close_crew = lambda: None
                    try:
                        close_crew, crew_healthy = crew_client(session, create=False)
                    except Exception as error:
                        print("Firstmate crew viewport lost: {}. Resume this persisted captain after reconciling its crew session.".format(error), file=sys.stderr)
                        sys.exit(1)
        sys.exit(child.returncode)
    finally:
        try:
            if child and child.poll() is None:
                child.terminate()
                child.wait(timeout=20)
        finally:
            try:
                if awake and awake.poll() is None:
                    awake.terminate()
                    awake.wait(timeout=5)
            finally:
                close_crew()
