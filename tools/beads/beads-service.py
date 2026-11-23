#!/usr/bin/env python3
"""Manage one loopback Beads HTTP endpoint and its private Dolt SQL server."""

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import urllib.error
import urllib.request

from beads_config import load, location, seed, write_record
from beads_lifecycle import Control, inspect, process_identity

ROOT = Path(__file__).resolve().parents[2]
LABEL = "com.lanej.beads"


class ActivationIncomplete(ValueError):
    """A refused native replacement must preserve its current owner."""


def require_activation_checkpoint(home):
    try:
        target = inspect(home, "inventory")["targets"][0]
        expected = json.loads(os.environ.get("PROJECT_UPDATE_EXPECTED_PROCESS", "null"))
    except (OSError, ValueError, KeyError) as error:
        raise ActivationIncomplete("Native checkpoint unavailable; preserve this Beads owner") from error
    if (target["process"] != expected or expected is None
            or process_identity(expected["pid"]) != expected["start_identity"]
            or target.get("checkpoint", {}).get("state") != "confirmed"
            or target["checkpoint"].get("run_id") != os.environ.get("PROJECT_UPDATE_RUN_ID")
            or not target["checkpoint"].get("run_id")
            or target.get("retirement_policy") != "successful-exit"):
        raise ActivationIncomplete("Beads checkpoint or process incarnation differs")
    return expected


def retire_owner(home, expected, manager_pid):
    """Confirm normal native exit before letting an OS manager change the job."""
    result = inspect(home, "stop")["targets"][0]
    if result["process"] != expected or not result.get("stop_accepted"):
        raise ActivationIncomplete("Beads retirement outcome unknown; do not repeat stop")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        observed = manager_pid()
        if observed not in (None, expected["pid"]):
            raise ActivationIncomplete("Service manager launched another Beads owner; preserve it")
        try:
            os.kill(expected["pid"], 0)
        except ProcessLookupError:
            if observed is None:
                return
        time.sleep(0.1)
    raise ActivationIncomplete("Native Beads retirement unconfirmed after 60 seconds; no forced termination")


@contextmanager
def installation_lock(home, inherited=None):
    share, _, _ = paths(home)
    share.mkdir(parents=True, mode=0o700, exist_ok=True)
    path = share / "install.lock"
    if inherited is not None:
        descriptor, target = os.fstat(inherited), path.stat()
        if (descriptor.st_dev, descriptor.st_ino) != (target.st_dev, target.st_ino):
            raise ValueError("Inherited deployment lock does not identify this installation")
        # The parent retains this same open file description through receipt capture or activation.
        fcntl.flock(inherited, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
        return
    with path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another Beads installation or service operation is in progress") from error
        yield


def run(argv, **kwargs):
    return subprocess.run([str(arg) for arg in argv], check=True, text=True,
                          stdout=subprocess.PIPE, **kwargs).stdout.strip()


def paths(home):
    return (home / ".local/share/beads-service", home / ".local/state/beads-service",
            location(home))


def settings(home):
    share, state, _ = paths(home)
    value = load(home)
    return share, state, {**value["service"], **value["workspace"], "history": value["history"]}


def fetch_json(url):
    # Ignore ambient HTTP proxies for this strictly loopback interface.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=2) as response:
        return json.load(response)


def probe(home):
    _, state, config = settings(home)
    url = f"http://127.0.0.1:{config['http_port']}"
    live, ready = False, False
    context = None
    try:
        fetch_json(url + "/healthz")
        live = True
        context = fetch_json(url + "/v0/beads/context")
        if not isinstance(context, dict):
            raise ValueError("Expected a Beads context object")
        fetch_json(url + "/v0/beads/ready?limit=1")
        ready = (context.get("database") == config["database"] and context.get("dolt_mode") == "server"
                 and context.get("beads_dir") == str(state / "workspace/.beads"))
    except (OSError, ValueError, urllib.error.HTTPError):
        pass
    history_path = state / "history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else {"state": "never_run"}
    return {"url": url, "live": live, "ready": ready,
            "database": context.get("database") if isinstance(context, dict) else None,
            "workspace": context.get("repo_root") if isinstance(context, dict) else None,
            "history": {"mode": config["history"]["mode"], **history}}


def install(home, *, start=True):
    share, state, config_path = paths(home)
    target = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine())
    if target is None or arch is None:
        raise ValueError("Beads service supports macOS and Linux on arm64 and amd64")
    catalog = tomllib.loads((ROOT / "bootstrap/tools.toml").read_text())["tools"]["beads"]
    for directory in (share, state, config_path.parent):
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    seed(home, ROOT / "config/beads/trial.toml")
    settings(home)
    binaries = {}
    for name, repo, version, asset in (
        ("bd", "gastownhall/beads", catalog["version"],
         f"beads_{catalog['version']}_{target}_{arch}.tar.gz"),
        ("dolt", "dolthub/dolt", catalog["dolt_version"], f"dolt-{target}-{arch}.tar.gz"),
    ):
        directory = share / "runtime" / f"{name}-{version}-{target}-{arch}"
        directory.mkdir(parents=True, exist_ok=True)
        binary = directory / name
        receipt = directory / "sha256"
        digest = catalog["sha256"][f"{name}_{target}_{arch}"]
        if binary.exists():
            if not receipt.exists() or hashlib.sha256(binary.read_bytes()).hexdigest() != receipt.read_text().strip():
                raise ValueError(f"Preserve unverified runtime: {binary}")
        else:
            with tempfile.TemporaryDirectory(prefix=".download-", dir=directory) as temporary:
                archive = Path(temporary) / asset
                run(["curl", "--fail", "--location", "--retry", "3", "--output", archive,
                     f"https://github.com/{repo}/releases/download/v{version}/{asset}"])
                if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
                    raise ValueError(f"Checksum mismatch for {asset}")
                with tarfile.open(archive) as bundle:
                    members = [member for member in bundle.getmembers()
                               if member.isfile() and Path(member.name).name == name]
                    if len(members) != 1:
                        raise ValueError(f"Expected one {name} executable in {asset}")
                    stream = bundle.extractfile(members[0])
                    candidate = Path(temporary) / name
                    with candidate.open("wb") as output:
                        shutil.copyfileobj(stream, output)
                candidate.chmod(0o755)
                run([candidate, "version"])
                candidate.replace(binary)
                receipt.write_text(hashlib.sha256(binary.read_bytes()).hexdigest() + "\n")
        binaries[name] = str(binary)
        binary.chmod(0o500)
    payloads = {name: Path(__file__).with_name(name).read_bytes()
                for name in ("beads-service.py", "beads_config.py", "beads_lifecycle.py")}
    payloads["runtime.json"] = (json.dumps(binaries) + "\n").encode()
    release_id = hashlib.sha256(b"".join(name.encode() + b"\0" + value
                                        for name, value in sorted(payloads.items()))).hexdigest()
    release = share / "releases" / release_id
    release.mkdir(parents=True, mode=0o700, exist_ok=True)
    for name, data in payloads.items():
        path = release / name
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("Preserve modified immutable Beads release")
        else:
            path.write_bytes(data)
            path.chmod(0o500 if name == "beads-service.py" else 0o400)
    for name in payloads:
        link = share / f".{name}-{os.getpid()}"
        try:
            link.symlink_to(release / name)
            link.replace(share / name)
        finally:
            link.unlink(missing_ok=True)
    controller = share / "beads-service.py"
    launcher = home / ".local/bin/beads-service"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    # The installed copy keeps the service independent of its source worktree.
    launcher.write_text(f"#!{sys.executable}\nimport os, sys\nos.execv(sys.executable, [sys.executable, {str(controller.resolve())!r}, *sys.argv[1:]])\n")
    launcher.chmod(0o755)
    definition(home)
    if start:
        manage(home, "start")
    else:
        print(json.dumps({"staged": True, "started": False, "runtime": binaries}))


def definition(home):
    share, state, _ = paths(home)
    argv = [sys.executable, str((share / "beads-service.py").resolve()), "run", "--home", str(home)]
    if platform.system() == "Darwin":
        destination = home / "Library/LaunchAgents" / f"{LABEL}.plist"
        environment = {"HOME": str(home), "PROJECT_UPDATE_RETIREMENT_POLICY": "successful-exit"}
        if "XDG_CONFIG_HOME" in os.environ:
            environment["XDG_CONFIG_HOME"] = os.environ["XDG_CONFIG_HOME"]
        payload = plistlib.dumps({"Label": LABEL, "ProgramArguments": argv,
                                 "RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False}, "ThrottleInterval": 10,
                                 "ExitTimeOut": 35, "EnvironmentVariables": environment,
                                 "StandardOutPath": str(state / "service.log"),
                                 "StandardErrorPath": str(state / "service.log")})
    else:
        destination = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "systemd/user/beads.service"
        # systemd quoting is not shell quoting; escape its specifiers as well.
        def quote(value):
            return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$") + '"'
        environment = ""
        if "XDG_CONFIG_HOME" in os.environ:
            environment = "Environment=" + quote("XDG_CONFIG_HOME=" + os.environ["XDG_CONFIG_HOME"]) + "\n"
        payload = ("[Unit]\nDescription=Shared Beads API and Dolt database\n"
                   "[Service]\nType=simple\nExecStart=" + " ".join(map(quote, argv)) +
                   "\nRestart=on-failure\nRestartSec=10\nTimeoutStopSec=35\nKillMode=mixed\n"
                   "Environment=PROJECT_UPDATE_RETIREMENT_POLICY=successful-exit\n"
                   + environment + "[Install]\nWantedBy=default.target\n").encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return destination


def manage(home, action):
    expected = require_activation_checkpoint(home) if action == "restart" else None
    if platform.system() == "Darwin":
        domain = f"gui/{os.getuid()}"
        target = f"{domain}/{LABEL}"
        observed = subprocess.run(["launchctl", "print", target], capture_output=True, text=True)
        loaded = observed.returncode == 0
        if expected is not None:
            match = re.search(r"(?m)^\tpid = (\d+)$", observed.stdout)
            if not loaded or match is None or int(match[1]) != expected["pid"]:
                raise ActivationIncomplete("Registered Beads service owner differs")
            def manager_pid():
                current = subprocess.run(["launchctl", "print", target], capture_output=True, text=True)
                if current.returncode not in (0, 3, 113):
                    raise ActivationIncomplete("Cannot verify the registered Beads owner")
                match = re.search(r"(?m)^\tpid = (\d+)$", current.stdout)
                return int(match[1]) if match else None
            retire_owner(home, expected, manager_pid)
        if action == "stop":
            if loaded:
                run(["launchctl", "bootout", target])
            run(["launchctl", "disable", target])
        else:
            run(["launchctl", "enable", target])
            if not loaded:
                run(["launchctl", "bootstrap", domain, home / "Library/LaunchAgents" / f"{LABEL}.plist"])
            elif action == "restart":
                if manager_pid() is not None:
                    raise ActivationIncomplete("A Beads owner appeared before OS job replacement; preserve it")
                run(["launchctl", "bootout", target])
                # bootout returns before launchd has finished removing a running job.
                deadline = time.monotonic() + 35
                while subprocess.run(["launchctl", "print", target], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL).returncode == 0:
                    if time.monotonic() >= deadline:
                        raise ValueError("launchd did not finish stopping Beads within 35 seconds")
                    time.sleep(0.1)
                run(["launchctl", "bootstrap", domain, home / "Library/LaunchAgents" / f"{LABEL}.plist"])
    elif platform.system() == "Linux":
        if expected is not None:
            observed = subprocess.run(["systemctl", "--user", "show", "beads.service",
                                       "--property=MainPID", "--value"], capture_output=True, text=True)
            if observed.returncode or observed.stdout.strip() != str(expected["pid"]):
                raise ActivationIncomplete("Registered Beads service owner differs")
            def manager_pid():
                current = subprocess.run(["systemctl", "--user", "show", "beads.service",
                                          "--property=MainPID", "--value"], capture_output=True, text=True)
                if current.returncode or not current.stdout.strip().isdigit():
                    raise ActivationIncomplete("Cannot verify the registered Beads owner")
                return int(current.stdout.strip()) or None
            retire_owner(home, expected, manager_pid)
        run(["systemctl", "--user", "daemon-reload"])
        if action == "stop":
            run(["systemctl", "--user", "disable", "--now", "beads.service"])
        else:
            run(["systemctl", "--user", "enable", "beads.service"])
            run(["systemctl", "--user", "start", "beads.service"])
    else:
        raise ValueError("Unsupported service manager")
    if action != "stop":
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            status = probe(home)
            if status["ready"]:
                print(json.dumps(status))
                return
            time.sleep(0.5)
        raise ValueError(f"Beads did not become ready; inspect {paths(home)[1] / 'service.log'}")


def serve(home):
    share, state, config = settings(home)
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (state / "service.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("A Beads service already owns this workspace") from error
        supervise(home, share, state, config)


def supervise(home, share, state, config):
    program = Path(__file__).resolve().parent
    manifest = program / "runtime.json" if (program / "runtime.json").is_file() else share / "runtime.json"
    binaries = json.loads(manifest.read_text())
    workspace, data = state / "workspace", state / "dolt"
    for directory in (workspace, data):
        directory.mkdir(mode=0o700, exist_ok=True)
    if not (workspace / ".git").exists():
        run(["git", "-c", "core.hooksPath=/dev/null", "init", "--quiet", workspace])
    for port in (config["http_port"], config["sql_port"]):
        with socket.socket() as listener:
            # Closed connections in TIME_WAIT must not masquerade as a live listener after restart.
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", port))
    endpoint = state / "endpoint.json"
    endpoint.unlink(missing_ok=True)
    children = []
    control = Control(home, lambda: probe(home)["ready"], program, binaries)
    stopped = False

    def stop(_number, _frame):
        nonlocal stopped
        stopped = True

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("BEADS_", "BD_", "DOLT_"))}
    env.update(HOME=str(home), PATH=f"{Path(binaries['dolt']).parent}:{os.environ.get('PATH', '')}",
               DOLT_ROOT_PATH=str(state / "dolt-home"), DOLT_CLI_NO_UPDATE_CHECK="1")
    bd = [binaries["bd"], "-C", str(workspace)]
    try:
        children.append(subprocess.Popen([binaries["dolt"], "sql-server", "--host", "127.0.0.1",
                                          "--port", str(config["sql_port"]), "--data-dir", str(data)],
                                         cwd=data, env=env))
        deadline = time.monotonic() + 45
        while True:
            if stopped or children[0].poll() is not None:
                raise ValueError("Dolt stopped before initialization")
            try:
                with socket.create_connection(("127.0.0.1", config["sql_port"]), timeout=0.2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError("Dolt did not start within 45 seconds") from None
                time.sleep(0.1)
        metadata = workspace / ".beads/metadata.json"
        if not metadata.exists():
            # Only initialize an empty dedicated workspace; never migrate an existing database implicitly.
            if (workspace / ".beads").exists():
                raise ValueError("Incomplete Beads workspace; inspect it before retrying initialization")
            initializer = subprocess.Popen(
                [binaries["bd"], "init", "--server", "--external", "--server-host", "127.0.0.1",
                 "--server-port", str(config["sql_port"]), "--database", config["database"], "--prefix", config["prefix"],
                 "--skip-agents", "--skip-hooks", "--non-interactive"], env=env, cwd=workspace)
            children.append(initializer)
            deadline = time.monotonic() + 45
            while initializer.poll() is None:
                if stopped:
                    return
                if children[0].poll() is not None or time.monotonic() >= deadline:
                    raise ValueError("Beads initialization failed to complete within the startup window")
                time.sleep(0.1)
            if initializer.returncode != 0:
                raise ValueError(f"Beads initialization failed with exit code {initializer.returncode}")
            children.remove(initializer)
        # Fail rather than silently selecting embedded mode or another database.
        configured = json.loads(metadata.read_text())
        if (configured.get("dolt_mode") != "server" or configured.get("dolt_database") != config["database"]
                or configured.get("dolt_server_host") != "127.0.0.1"
                or configured.get("dolt_server_port") != config["sql_port"]):
            raise ValueError(f"Workspace configuration differs from the managed database: {metadata}")
        if stopped:
            return
        observed = json.loads(run([*bd, "--sandbox", "--readonly", "sql", "SELECT ACTIVE_BRANCH() AS branch", "--json"],
                                  cwd=workspace, env=env, timeout=15))
        if observed != [{"branch": config["branch"]}]:
            raise ValueError("Beads is on a different Dolt branch than the trial profile")
        children.append(subprocess.Popen([*bd, "serve", "--addr", f"127.0.0.1:{config['http_port']}"],
                                         cwd=workspace, env=env))
        control.bind_children(children, binaries)
        deadline = time.monotonic() + 45
        while not stopped:
            if control.retired.is_set():
                break
            if control.requested.is_set():
                control.checkpoint_children(children)
                time.sleep(0.1)
                continue
            if any(child.poll() is not None for child in children):
                raise ValueError("Beads or Dolt exited; restarting the complete service is required")
            if not endpoint.exists():
                status = probe(home)
                if status["ready"]:
                    endpoint.write_text(json.dumps(status) + "\n")
                    print(json.dumps(status), flush=True)
                elif time.monotonic() >= deadline:
                    raise ValueError("Beads did not become database-ready within 45 seconds")
            time.sleep(0.2)
    finally:
        control.close()
        endpoint.unlink(missing_ok=True)
        # Drain HTTP requests before stopping their database. Never kill by port or process name.
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    print("Beads child has not acknowledged termination; waiting without forced termination", file=sys.stderr)
                    child.wait()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def checkpoint(home):
    share, state, config = settings(home)
    workspace = state / "workspace"
    if not probe(home)["ready"]:
        raise ValueError("The configured Beads workspace is not database-ready")
    with (state / "history.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another history push is already in progress") from error
        history_path = state / "history.json"
        previous = json.loads(history_path.read_text()) if history_path.exists() else {}
        record = {"state": "running", "attemptedAt": int(time.time() * 1000),
                  "lastSuccess": previous.get("lastSuccess"), "pushAttempted": False}
        write_record(history_path, record)
        try:
            binaries = json.loads((share / "runtime.json").read_text())
            metadata = json.loads((workspace / ".beads/metadata.json").read_text())
            if (metadata.get("dolt_mode") != "server" or metadata.get("dolt_database") != config["database"]
                    or metadata.get("dolt_server_host") != "127.0.0.1"
                    or metadata.get("dolt_server_port") != config["sql_port"]):
                raise ValueError("Workspace metadata differs from the configured trial database")
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("BEADS_", "BD_", "DOLT_"))}
            env.update(BEADS_DIR=str(workspace / ".beads"), BEADS_DOLT_SERVER_MODE="1",
                       BEADS_DOLT_SERVER_HOST="127.0.0.1", BEADS_DOLT_SERVER_PORT=str(config["sql_port"]),
                       DOLT_ROOT_PATH=str(state / "dolt-home"), GIT_TERMINAL_PROMPT="0",
                       PATH=f"{Path(binaries['dolt']).parent}:{os.environ.get('PATH', '')}")
            gh = shutil.which("gh")
            if gh is None:
                raise ValueError("History pushes require the authenticated GitHub CLI")
            # Use the existing GitHub login for these child processes, without rewriting Git configuration.
            env.update(GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="credential.helper", GIT_CONFIG_VALUE_0="",
                       GIT_CONFIG_KEY_1="credential.helper", GIT_CONFIG_VALUE_1=f"!{shlex.quote(gh)} auth git-credential")
            bd = [binaries["bd"], "--sandbox"]
            def native(*args):
                return run([*bd, *args], cwd=workspace, env=env, timeout=180)
            branch = json.loads(native("--readonly", "sql", "SELECT ACTIVE_BRANCH() AS branch", "--json"))
            if branch != [{"branch": config["branch"]}]:
                raise ValueError("Refusing history push from a different Dolt branch")
            target = config["history"]
            remotes = json.loads(native("dolt", "remote", "list", "--json"))
            matches = [item for item in remotes if item["name"] == target["remote"]]
            if len(matches) != 1 or matches[0]["url"] != target["url"]:
                raise ValueError("Configured history remote differs from Beads; reconcile it explicitly before pushing")
            repository = target["url"].removeprefix("git+https://github.com/").removesuffix(".git")
            privacy = json.loads(run(["gh", "repo", "view", f"https://github.com/{repository}", "--json", "visibility"],
                                     env=env, timeout=30))
            if privacy.get("visibility") != "PRIVATE":
                raise ValueError("The trial history repository must be private")
            native("dolt", "commit", "--message", "Checkpoint shared Beads trial history")
            head = json.loads(native("--readonly", "sql", "SELECT DOLT_HASHOF('HEAD') AS hash", "--json"))
            record.update(state="pushing", pushAttempted=True)
            write_record(history_path, record)
            native("dolt", "push", "--remote", target["remote"], "--no-adopt")
            ref = run(["git", "ls-remote", "--exit-code", target["url"].removeprefix("git+"), "refs/dolt/data"],
                      env=env, timeout=60).split()
            if len(ref) != 2 or ref[1] != "refs/dolt/data" or not re.fullmatch(r"[a-f0-9]{40,64}", ref[0]):
                raise ValueError("Push returned but the Git data ref could not be confirmed")
            success = {"at": int(time.time() * 1000), "sourceHeadAtPush": head,
                       "gitDataRef": ref[0], "remote": target["url"]}
            record.update(state="succeeded", lastSuccess=success)
            write_record(history_path, record)
            print(json.dumps(record))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            record.update(state="unconfirmed" if record["pushAttempted"] else "failed", error=str(error))
            write_record(history_path, record)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "start", "restart", "stop", "status", "run", "config", "backup",
                                          "inventory", "checkpoint", "retire", "restore", "verify"))
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--no-start", action="store_true", help="stage installation without starting or restarting the service")
    parser.add_argument("--install-lock-fd", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.no_start and args.action != "install":
        parser.error("--no-start applies only to install")
    if args.install_lock_fd is not None and args.action not in ("install", "start", "restart", "stop"):
        parser.error("--install-lock-fd applies only to installation and service controls")
    home = args.home.expanduser().resolve()
    if args.action in ("install", "start", "restart", "stop"):
        with installation_lock(home, args.install_lock_fd):
            if args.action == "install":
                install(home, start=not args.no_start)
            else:
                manage(home, args.action)
    elif args.action == "run":
        serve(home)
    elif args.action in ("inventory", "checkpoint", "retire", "restore", "verify"):
        native_action = {"restore": "verify", "retire": "stop"}.get(args.action, args.action)
        value = inspect(home, native_action)
        print(json.dumps(value))
        target = value["targets"][0]
        if args.action == "inventory":
            return 0
        if args.action == "checkpoint":
            return 0 if target.get("checkpoint", {}).get("state") == "confirmed" else 3
        if args.action == "retire":
            return 0 if target.get("stop_accepted") else 3
        return 0 if target["ready"] and target["expected_identity"] and target["expected_identity"] == target["running_identity"] else 3
    elif args.action == "status":
        status = probe(home)
        print(json.dumps(status))
        return 0 if status["ready"] else 1
    elif args.action == "config":
        print(json.dumps({"path": str(location(home)), **load(home)}))
    elif args.action == "backup":
        checkpoint(home)
    else:
        manage(home, args.action)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ActivationIncomplete as error:
        print(f"beads-service: {error}", file=sys.stderr)
        sys.exit(3)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(f"beads-service: {error}")
