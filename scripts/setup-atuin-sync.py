#!/usr/bin/env python3
"""Configure shared Atuin history on a Mac and its Linux sync server."""
import argparse
import base64
from contextlib import closing
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

MIN_VERSION = "18.21.0"
ACCOUNT_FILE = "self-hosted-account.json"


def call(args, env=None, allow_failure=False):
    result = subprocess.run(args, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode and not allow_failure:
        # Never include argv: login and registration carry private credentials.
        raise RuntimeError("{} failed: {}".format(Path(args[0]).name, result.stderr.strip()))
    return result


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".atuin-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(content)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def data_dir():
    return Path.home() / ".local/share/atuin"


def backup(names=("history.db", "records.db", "shared-records.db", "meta.db")):
    source = data_dir()
    if not source.exists():
        return
    parent = source / "backups"
    parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="setup-" + time.strftime("%Y%m%d-%H%M%S") + "-",
                                      dir=str(parent)))
    for name in names:
        if not (source / name).exists():
            continue
        if hasattr(sqlite3.Connection, "backup"):
            with closing(sqlite3.connect(str(source / name))) as original:
                with closing(sqlite3.connect(str(destination / name))) as saved:
                    original.backup(saved)
        else:
            call(["sqlite3", str(source / name),
                  ".backup '{}'".format(str(destination / name).replace("'", "''"))])
        os.chmod(str(destination / name), 0o600)
    for name in ("key", "shared-key", "session", ACCOUNT_FILE):
        if (source / name).exists():
            shutil.copy2(str(source / name), str(destination / name))
    return destination


def install(program, version, bootstrap):
    canonical = (Path.home() / ".local/bin/atuin-server" if program == "atuin-server"
                 else Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo")) / "bin/atuin")
    found = str(canonical) if canonical.exists() else (shutil.which(program) if program == "atuin" else None)
    if found and not Path(found).is_file():
        found = None
    if found:
        current = call([found, "--version"]).stdout.split()[1]
        current_tuple = tuple(map(int, current.split(".")))
        requested_tuple = tuple(map(int, version.split(".")))
        if current_tuple > requested_tuple:
            raise RuntimeError("{} is newer than {}; update the Mac client first.".format(program, version))
        if current_tuple == requested_tuple:
            return found
    call(["bash", "-c", 'source "$1"; install_atuin_from_release "$2" "$3"',
          "bash", str(bootstrap), version, program])
    if program == "atuin":
        return str(Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo")) / "bin/atuin")
    return str(Path.home() / ".local/bin/atuin-server")


def configure_client(root, key, config_seed, enroll=False, atuin=None):
    shared_key = data_dir() / "shared-key"
    if shared_key.exists() and shared_key.read_bytes() != key:
        if not enroll or (data_dir() / ACCOUNT_FILE).exists():
            raise RuntimeError("The existing shared key differs; refusing to replace it or its history store.")
        # Shell startup may create a key/store before a fresh host is enrolled.
        # Archive that store intact; rebuild shared records from plaintext history.
        verify(atuin, env=dict(os.environ, ATUIN_KEY_PATH=str(shared_key),
                              ATUIN_RECORD_STORE_PATH=str(data_dir() / "shared-records.db")))
        saved = backup()
        for name in ("shared-key", "shared-records.db", "shared-records.db-wal", "shared-records.db-shm"):
            path = data_dir() / name
            if path.exists():
                path.rename(saved / ("original-" + name))
    fresh_store = not (data_dir() / "shared-records.db").exists()
    if not shared_key.exists() and not fresh_store:
        raise RuntimeError("A shared record store exists without its key; restore the key before setup.")
    if fresh_store:
        backup()
    if not shared_key.exists():
        private_write(shared_key, key)
    config = root / "sh/atuin.toml"
    text = config.read_text() if config.exists() else config_seed
    settings = {
        "key_path": '"~/.local/share/atuin/shared-key"',
        "record_store_path": '"~/.local/share/atuin/shared-records.db"',
        "auto_sync": "true", "sync_address": '"http://127.0.0.1:8888"',
        "sync_frequency": '"1m"', "filter_mode": '"global"',
    }
    for name, value in settings.items():
        text, count = re.subn(r"(?m)^" + name + r"\s*=.*$", name + " = " + value, text)
        if not count:
            text = name + " = " + value + "\n" + text
    config.parent.mkdir(parents=True, exist_ok=True)
    private_write(config, text.encode())
    link = Path.home() / ".config/atuin/config.toml"
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() and link.resolve() == config.resolve():
        return
    if link.exists() or link.is_symlink():
        parent = data_dir() / "backups"
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup_path = Path(tempfile.mkdtemp(prefix="config-", dir=str(parent)))
        link.rename(backup_path / "config.toml")
    link.symlink_to(config)


def verify(atuin, env=None):
    if "Local store encryption verified OK" not in call([atuin, "store", "verify"], env=env).stdout:
        raise RuntimeError("Atuin did not confirm that the history store decrypts.")


def authenticate(atuin, account, mnemonic, allow_failure=False):
    backup(names=("meta.db",))
    call([atuin, "logout"])
    return call([atuin, "login", "-u", account["username"], "-p", account["password"],
                 "-k", mnemonic], allow_failure=allow_failure)


def wait_for_server():
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8888/", timeout=1) as response:
                if "version" in json.load(response):
                    return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise RuntimeError("The Atuin server is unreachable on localhost:8888; check the service or SSH tunnel.")


def server(request):
    root = Path.home() / ".files"
    if not (root / "bootstrap.sh").exists():
        raise RuntimeError("Install current dotfiles in ~/.files on the SSH host first.")
    if request["action"] == "inspect":
        path = data_dir() / ACCOUNT_FILE
        if not path.exists():
            return None
        return {"account": json.loads(path.read_text()),
                "key": base64.b64encode((data_dir() / "shared-key").read_bytes()).decode()}
    if request["action"] == "sync":
        atuin = install("atuin", request["version"], root / "bootstrap.sh")
        env = dict(os.environ)
        env["ATUIN_SESSION"] = call([atuin, "uuid"]).stdout.strip()
        call([atuin, "sync"], env=env)
        verify(atuin)
        return {"ready": True}
    atuin = install("atuin", request["version"], root / "bootstrap.sh")
    install("atuin-server", request["version"], root / "bootstrap.sh")
    configure_client(root, base64.b64decode(request["key"]), request["config"],
                     enroll=request.get("enroll", False), atuin=atuin)
    directory = Path.home() / ".local/share/atuin-server"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(str(directory), 0o700)
    config = Path.home() / ".config/atuin/server.toml"
    closed = request["server_config"].replace("__HOME__", str(Path.home()))
    config.write_text(closed)
    unit = Path.home() / ".config/systemd/user/atuin-server.service"
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(request["unit"])
    call(["systemctl", "--user", "daemon-reload"])
    call(["systemctl", "--user", "enable", "--now", "atuin-server"])
    call(["systemctl", "--user", "restart", "atuin-server"])
    wait_for_server()
    account = request["account"]
    if authenticate(atuin, account, request["mnemonic"], allow_failure=True).returncode:
        try:
            config.write_text(closed.replace("open_registration = false", "open_registration = true"))
            call(["systemctl", "--user", "restart", "atuin-server"])
            wait_for_server()
            call([atuin, "register", "-u", account["username"], "-p", account["password"],
                  "-e", account["email"]])
            private_write(data_dir() / ACCOUNT_FILE, json.dumps(account).encode())
        finally:
            config.write_text(closed)
            call(["systemctl", "--user", "restart", "atuin-server"])
            wait_for_server()
    private_write(data_dir() / ACCOUNT_FILE, json.dumps(account).encode())
    env = dict(os.environ)
    env["ATUIN_SESSION"] = call([atuin, "uuid"]).stdout.strip()
    call([atuin, "history", "init-store"], env=env)
    verify(atuin)
    call([atuin, "sync"], env=env)
    if "Linger=yes" not in call(["loginctl", "show-user", os.environ["USER"], "-p", "Linger"]).stdout:
        if call(["loginctl", "enable-linger", os.environ["USER"]], allow_failure=True).returncode:
            call(["sudo", "-n", "loginctl", "enable-linger", os.environ["USER"]])
    return {"ready": True}


def connection_settings(host):
    settings = {}
    identities = []
    for line in call(["ssh", "-G", host]).stdout.splitlines():
        name, _, value = line.partition(" ")
        settings[name] = value
        if name == "identityfile":
            identities.append(value)
    return settings, identities


def jump_settings(settings):
    if settings.get("proxycommand", "none") != "none":
        raise RuntimeError("Unattended Atuin SSH requires ProxyJump instead of a custom ProxyCommand.")
    jumps = settings.get("proxyjump", "none")
    if jumps == "none":
        return None
    hops = jumps.split(",")
    original = ["ssh", "-G"]
    if len(hops) > 1:
        original += ["-J", ",".join(hops[:-1])]
    original += [hops[-1]]
    hop_settings = dict(line.split(" ", 1) for line in call(original).stdout.splitlines())
    control = hop_settings.get("controlpath", "none")
    if control == "none":
        control = str(Path.home() / ".local/state/atuin-sync/jump-control")
    return hops, control


def prepare_jump(settings):
    jump = jump_settings(settings)
    if not jump:
        return
    hops, control = jump
    # A foreground setup may authenticate once. The generated background proxy
    # only reuses this master and cannot fall back to a new Duo connection.
    if not call(["ssh", "-S", control, "-O", "check", hops[-1]], allow_failure=True).returncode:
        return
    Path(control).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args = ["ssh", "-M", "-S", control, "-fNT",
            "-o", "ClearAllForwardings=yes", "-o", "ConnectTimeout=10",
            "-o", "ControlPersist=no", "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3"]
    if len(hops) > 1:
        args += ["-J", ",".join(hops[:-1])]
    args += [hops[-1]]
    call(args)


def unattended_proxy(settings):
    jump = jump_settings(settings)
    if not jump:
        return None
    hops, control = jump
    # Reuse the final hop's authenticated master. If it is absent or stale,
    # false replaces the network fallback, so background jobs cannot attempt Duo.
    # Pin the original path: a %C socket hash includes the original jump chain.
    command = ["/usr/bin/ssh", "-S", control, "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes",
               "-o", "ProxyCommand=/usr/bin/false", "-W", "%h:%p", hops[-1]]
    return " ".join(map(shlex.quote, command))


def tunnel(root, host):
    settings, identities = connection_settings(host)
    proxy = unattended_proxy(settings)
    args = ["/usr/bin/ssh", "-N", "-T", "-F", "/dev/null",
            "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
            "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3"]
    agent = settings.get("identityagent", "none")
    if agent != "none":
        args += ["-o", 'IdentityAgent="' + agent.replace("\\", "\\\\").replace('"', '\\"') + '"']
    for identity in identities:
        args += ["-i", identity]
    if proxy:
        args += ["-o", "ProxyCommand=" + proxy]
    args += ["-p", settings["port"], "-L", "127.0.0.1:8888:127.0.0.1:8888",
             settings["user"] + "@" + settings["hostname"]]
    tree = ET.parse(str(root / "rc/launchd/com.joshlane.atuin-sync-tunnel.plist.template"))
    dictionary = tree.getroot().find("dict")
    children = list(dictionary)
    array = children[children.index(next(e for e in children if e.text == "ProgramArguments")) + 1]
    array.clear()
    for argument in args:
        ET.SubElement(array, "string").text = argument
    for element in tree.iter("string"):
        if element.text:
            element.text = element.text.replace("__HOME__", str(Path.home()))
    (Path.home() / ".local/state/atuin-sync").mkdir(parents=True, exist_ok=True)
    plist = Path.home() / "Library/LaunchAgents/com.joshlane.atuin-sync-tunnel.plist"
    plist.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(plist), encoding="utf-8", xml_declaration=True)
    domain = "gui/" + str(os.getuid())
    call(["launchctl", "bootout", domain + "/com.joshlane.atuin-sync-tunnel"], allow_failure=True)
    call(["launchctl", "enable", domain + "/com.joshlane.atuin-sync-tunnel"])
    call(["launchctl", "bootstrap", domain, str(plist)])
    wait_for_server()


def setup(args):
    root = Path(__file__).resolve().parent.parent
    if platform.system() == "Linux":
        path = data_dir() / ACCOUNT_FILE
        key = data_dir() / "shared-key"
        if not path.exists() or not key.exists():
            raise RuntimeError("This Linux host is not enrolled in shared history. From your Mac, run "
                               "'make atuin-sync ATUIN_SYNC_HOST=<this-host>' once, then rerun bootstrap.")
        atuin = shutil.which("atuin")
        if not atuin:
            raise RuntimeError("Install Atuin before configuring sync.")
        server({"action": "setup", "account": json.loads(path.read_text()),
                "key": base64.b64encode(key.read_bytes()).decode(),
                "mnemonic": call([atuin, "key"]).stdout.strip(),
                "version": call([atuin, "--version"]).stdout.split()[1],
                "config": (root / "sh/atuin.toml").read_text(),
                "server_config": (root / "sh/atuin-server.toml.template").read_text(),
                "unit": (root / "rc/systemd/atuin-server.service").read_text()})
        print("Atuin sync server is ready; shared history is synchronized.")
        return
    if platform.system() != "Darwin":
        raise RuntimeError("Atuin sync setup supports macOS clients and Linux servers.")
    selected_host = Path.home() / ".local/state/atuin-sync/host"
    args.host = args.host or (selected_host.read_text().strip() if selected_host.exists() else "dev")
    settings, _ = connection_settings(args.host)
    prepare_jump(settings)
    if args.tunnel_only:
        tunnel(root, args.host)
        private_write(selected_host, (args.host + "\n").encode())
        return
    proxy = unattended_proxy(settings)
    local = shutil.which("atuin")
    version = call([local, "--version"]).stdout.split()[1] if local else MIN_VERSION
    if tuple(map(int, version.split("."))) < tuple(map(int, MIN_VERSION.split("."))):
        version = MIN_VERSION
    atuin = install("atuin", version, root / "bootstrap.sh")
    with tempfile.TemporaryDirectory(prefix="atuin-ssh-", dir="/tmp") as temporary:
        ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes",
               "-o", "ConnectTimeout=10", "-o", "ControlMaster=auto",
               "-o", "ControlPath=" + temporary + "/control", "-o", "ControlPersist=300"]
        if proxy:
            ssh += ["-o", "ProxyCommand=" + proxy]
        ssh += [args.host]
        source = Path(__file__).read_text()
        def remote(request):
            result = subprocess.run(ssh + ["python3 -c " + shlex.quote(source) + " --remote"],
                                    input=json.dumps(request), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=True)
            if result.returncode:
                raise RuntimeError("SSH setup failed: " + result.stderr.strip())
            return json.loads(result.stdout)
        try:
            existing = remote({"action": "inspect"})
            path = data_dir() / ACCOUNT_FILE
            account = json.loads(path.read_text()) if path.exists() else None
            if existing:
                if account and (account["username"], account["password"]) != (
                        existing["account"]["username"], existing["account"]["password"]):
                    raise RuntimeError("Local and remote recovery accounts differ; refusing to replace either.")
                account = existing["account"]
                key = base64.b64decode(existing["key"])
            else:
                account = account or {"username": os.environ.get("USER", "joshlane"),
                                      "email": call(["git", "config", "user.email"]).stdout.strip(),
                                      "password": secrets.token_urlsafe(40),
                                      "sync_address": "http://127.0.0.1:8888"}
                key_path = data_dir() / "shared-key"
                original_key = data_dir() / "key"
                if key_path.exists():
                    key = key_path.read_bytes()
                elif original_key.exists():
                    key = original_key.read_bytes()
                else:
                    # Atuin's decoder accepts a base64-encoded 32-byte key.
                    key = base64.b64encode(secrets.token_bytes(32))
            configure_client(root, key, (root / "sh/atuin.toml").read_text(), atuin=atuin)
            mnemonic = call([atuin, "key"]).stdout.strip()
            request = {"action": "setup", "account": account, "key": base64.b64encode(key).decode(),
                       "mnemonic": mnemonic, "version": version,
                       "enroll": existing is None,
                       "config": (root / "sh/atuin.toml").read_text(),
                       "server_config": (root / "sh/atuin-server.toml.template").read_text(),
                       "unit": (root / "rc/systemd/atuin-server.service").read_text()}
            remote(request)
            tunnel(root, args.host)
            env = dict(os.environ)
            env["ATUIN_SESSION"] = call([atuin, "uuid"]).stdout.strip()
            authenticate(atuin, account, mnemonic)
            private_write(path, json.dumps(account).encode())
            call([atuin, "history", "init-store"], env=env)
            verify(atuin)
            call([atuin, "sync"], env=env)
            remote(dict(request, action="sync"))
        finally:
            call(ssh[:-1] + ["-O", "exit", args.host], allow_failure=True)
    private_write(selected_host, (args.host + "\n").encode())
    print("Atuin history is shared with {}. Automatic sync: 1m. Recovery details: {}".format(args.host, path))


if __name__ == "__main__":
    try:
        if "--remote" in sys.argv:
            print(json.dumps(server(json.load(sys.stdin))))
        else:
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument("--host", help="SSH alias for the Linux server (default: last selected host, or dev)")
            parser.add_argument("--tunnel-only", action="store_true")
            setup(parser.parse_args())
    except (OSError, ValueError, RuntimeError) as error:
        print("Atuin setup failed: " + str(error), file=sys.stderr)
        sys.exit(1)
