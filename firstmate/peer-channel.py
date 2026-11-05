#!/usr/bin/env python3
"""One explicitly authenticated SSH channel per boat, shared through a private socket."""

import fcntl
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import tempfile


home, boat, alias = sys.argv[1:4]
root = Path(home) / "state/peers/channels"
root.mkdir(parents=True, exist_ok=True, mode=0o700)
path = root / (boat + ".sock")
child = None
server = None
os.umask(0o077)
with open(str(root / (boat + ".lock")), "a") as lock:
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit("This boat already has a peer channel; reuse it or inspect the existing connection.")
    ssh_config = root / (boat + ".ssh-config")
    # WHY: ProxyJump opens another SSH process; destination-only flags cannot constrain that hop.
    ssh_config.write_text('Host *\n ControlMaster no\n ControlPath none\n ControlPersist no\n ClearAllForwardings yes\n ConnectionAttempts 1\n ConnectTimeout 15\n ServerAliveInterval 15\n ServerAliveCountMax 2\n Include "{}"\n'.format(str(Path.home() / ".ssh/config").replace('"', '\\"')))
    os.chmod(str(ssh_config), 0o600)
    launcher = """import base64,json,os,pathlib,runpy,sys
p=pathlib.Path.home()/'.local/share/firstmate-peer'
p.mkdir(parents=True,exist_ok=True,mode=0o700)
for name,data in json.loads(sys.stdin.readline()).items():
 f=p/name; t=p/(name+'.install'); t.write_bytes(base64.b64decode(data)); t.chmod(0o600); os.replace(str(t),str(f))
sys.argv=[str(p/'helper.py'),'serve']
runpy.run_path(str(p/'helper.py'),run_name='__main__')
"""
    sources = Path(__file__).resolve().parent
    import base64
    files = {name: base64.b64encode((sources / source).read_bytes()).decode()
             for name, source in (("helper.py", "peer-helper.py"), ("paseo.mjs", "peer-paseo.mjs"))}
    log = open(str(root / (boat + ".ssh.log")), "a")
    try:
        child = subprocess.Popen(["ssh", "-F", str(ssh_config), "-T", alias, "python3 -u -c " + shlex.quote(launcher)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                 universal_newlines=True, bufsize=1)
        child.stdin.write(json.dumps(files) + "\n")
        child.stdin.flush()
        ready = child.stdout.readline()
        if ready.strip() != '{"ready": true}':
            sys.exit("Peer connection failed (SSH exit {}, startup response {} bytes); inspect {}. Authentication is never retried automatically.".format(
                child.poll(), len(ready.encode()), root / (boat + ".ssh.log")))
        if path.exists():
            path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path))
        os.chmod(str(path), 0o600)
        server.listen(4)
        server.settimeout(1)
        print("Connected {}. Peer helper installed; leave this connection running.".format(boat), flush=True)
        def stop(_signum, _frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while child.poll() is None:
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            with connection:
                connection.settimeout(30)
                input_file = connection.makefile("r")
                line = input_file.readline(100000)
                if not line.endswith("\n"):
                    continue
                request = json.loads(line)
                if request.get("action") not in ("list", "send", "status"):
                    connection.sendall(b'{"error":"Unsupported peer channel action"}\n')
                    continue
                child.stdin.write(json.dumps(request) + "\n")
                child.stdin.flush()
                response = child.stdout.readline()
                if not response:
                    break
                try:
                    connection.sendall(response.encode())
                except (BrokenPipeError, ConnectionResetError):
                    pass
        sys.exit("Peer SSH channel ended. Pending requests remain durable; reconnect this boat explicitly.")
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.close()
            path.unlink(missing_ok=True)
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        log.close()
        ssh_config.unlink(missing_ok=True)
