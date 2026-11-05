#!/usr/bin/env python3
"""Probe a shell-only agent updater on the pinned native Zellij runtime.

Run after installing the pinned runtime and pane-navigation fixture:
    python3 scripts/test-zellij-agent-update.py

This is an evaluation, not a production updater. All shell helpers, sockets,
configuration, and sessions are private temporary fixtures. No status build,
repository shell startup, or Python helper inside a pane is required.
"""

import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
Terminal = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))["Terminal"]
MARKER = b"AGENT_UPDATER_MUST_REMAIN_HIDDEN"

# Both startup and the transient updater identify their direct server parent.
# The full server socket is recorded so CI can establish the actual contract.
SHELL_HELPER = r'''
publish() {
    raw=$1
    mode=$2
    parent=$(ps -ww -p "$PPID" -o command=) || return 71
    case "$parent" in *' --server '*) ;; *) printf 'No server parent: %s\n' "$parent" >&2; return 72 ;; esac
    executable=${parent%% --server *}
    [ "${executable##*/}" = zellij ] || return 73
    server=${parent#* --server }
    case "$server" in /*) ;; *) return 74 ;; esac
    [ -S "$server" ] && [ -O "$server" ] || return 75
    key=${server##*/}
    case "$key" in ''|*[!a-zA-Z0-9_.-]*) return 76 ;; esac
    state="$HOME/agent-probe"
    umask 077
    mkdir -p "$state" || return 77
    stable="$state/$key.sock"
    printf '%s\n%s\n%s\n' "$parent" "$server" "$stable" > "$HOME/parent-identity"
    if [ ! -S "$raw" ] || [ -L "$raw" ] || [ ! -O "$raw" ]; then
        printf '%s\n' 'invalid raw socket' > "$HOME/updater-failed"
        return 78
    fi
    if [ "$mode" = publish ] || [ ! -L "$stable" ]; then
        temporary="$state/.refresh-$$"
        ln -s "$raw" "$temporary" && mv -f "$temporary" "$stable" || return 79
    fi
    if [ "$mode" = publish ]; then
        printf '%s\n' 'AGENT_UPDATER_MUST_REMAIN_HIDDEN'
        sleep 0.15
    fi
}
'''


def main():
    binary, agent_binary = shutil.which("zellij"), shutil.which("ssh-agent")
    assert binary and agent_binary and shutil.which("ssh-add"), "Install pinned Zellij and OpenSSH"
    with tempfile.TemporaryDirectory(prefix="zj-agent-probe-", dir="/tmp") as directory:
        temporary = Path(directory).resolve()
        home, runtime, temp_files = (temporary / name for name in ("home", "run", "tmp"))
        for path in (home, runtime, temp_files):
            path.mkdir(mode=0o700)
        updater, shell, launcher = (home / name for name in ("update-agent", "pane-shell", "attach-after-update"))
        updater.write_text("#!/bin/sh\n" + SHELL_HELPER + '\npublish "$1" publish\n')
        shell.write_text("#!/bin/sh\n" + SHELL_HELPER + '''
publish "$SSH_AUTH_SOCK" init || exit
export SSH_AUTH_SOCK="$stable"
export PS1='agent-probe-ready> '
exec /bin/sh -i
''')
        # A failed updater must not prevent the actual client from attaching.
        # The bounded Python observer detects a blocking native run operation.
        launcher.write_text('''#!/bin/sh
if "$PROBE_ZELLIJ" --session "$1" run --floating --no-focus --close-on-exit --blocking -- /bin/sh "$HOME/update-agent" "$2"; then
    status=0
else
    status=$?
fi
printf '%s\n' "$status" > "$HOME/updater-exit-status"
exec "$PROBE_ZELLIJ" attach "$1"
''')
        for path in (updater, shell, launcher):
            path.chmod(0o700)
        config = home / ".config/zellij"
        (config / "layouts").mkdir(parents=True)
        (config / "layouts/probe.kdl").write_text('layout { pane; }\n')
        (config / "config.kdl").write_text(
            f'default_shell {json.dumps(str(shell))}\n'
            'default_layout "probe"\n'
            'keybinds clear-defaults=true { normal { bind "Ctrl f" { Detach; } } }\n'
        )
        env = {
            **os.environ, "HOME": str(home), "SHELL": "/bin/sh", "TERM": "xterm-256color",
            "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(temporary / "cache"),
            "XDG_DATA_HOME": str(temporary / "data"), "XDG_RUNTIME_DIR": str(runtime),
            "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temp_files),
            "SSH_CONNECTION": "127.0.0.1 2222 127.0.0.1 22", "PROBE_ZELLIJ": binary,
        }
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        clients, agents, names = [], [], []

        def command(args, check=True):
            with subprocess.Popen(args, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True) as process:
                deadline = time.monotonic() + 10
                while True:
                    for client in clients:
                        client.drain(0.01)
                    if time.monotonic() >= deadline:
                        process.kill()
                        output, error = process.communicate()
                        raise AssertionError(f"Native command blocked: {args}\n{output}\n{error}")
                    try:
                        output, error = process.communicate(timeout=0.05)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                result = subprocess.CompletedProcess(args, process.returncode, output, error)
                if check:
                    result.check_returncode()
                return result

        def action(name, *args):
            return command([binary, "--session", name, "action", *args]).stdout

        def snapshot(name):
            panes = json.loads(action(name, "list-panes", "--json"))
            tabs = json.loads(action(name, "list-tabs", "--json"))
            keys = ("id", "tab_id", "is_plugin", "is_floating", "is_suppressed", "is_focused",
                    "is_fullscreen", "pane_x", "pane_y", "pane_columns", "pane_rows")
            return (sorted(tuple(p.get(key) for key in keys) for p in panes),
                    sorted((t["tab_id"], t["name"], t["active"]) for t in tabs))

        def start_agent(name):
            path = temporary / name
            process = subprocess.Popen([agent_binary, "-D", "-a", str(path)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            agents.append(process)
            deadline = time.monotonic() + 5
            while not path.is_socket() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            assert path.is_socket(), f"ssh-agent did not create {path}"
            return str(path)

        def attach(name, raw, failed_update=False):
            if name not in names:
                names.append(name)
            client = Terminal(binary, {**env, "SSH_AUTH_SOCK": raw}, name,
                              command=["/bin/sh", str(launcher), name, raw] if failed_update else None)
            clients.append(client)
            client.until("native shell is ready", lambda: b"agent-probe-ready> " in client.output)
            return client

        def detach(client):
            client.send(b"\x06")
            client.until("all clients detached", lambda:
                         not action(client.name, "list-clients").strip().splitlines()[1:])
            client.close()
            clients.remove(client)

        def identity():
            parent, server, stable = (home / "parent-identity").read_text().splitlines()
            assert " --server " in parent and Path(server).is_socket(), parent
            return server, Path(stable)

        def update(name, raw):
            before = snapshot(name)
            offsets = [(client, len(client.output)) for client in clients]
            command([binary, "--session", name, "run", "--floating", "--no-focus",
                     "--close-on-exit", "--blocking", "--", "/bin/sh", str(updater), raw])
            deadline = time.monotonic() + 5
            while snapshot(name) != before:
                assert time.monotonic() < deadline, "Updater changed pane IDs, focus, tabs, or geometry"
                time.sleep(0.02)
            for client, offset in offsets:
                client.drain(0.2)
                assert MARKER not in client.output[offset:], "Hidden updater rendered into the user's terminal"
            server, stable = identity()
            assert stable.resolve() == Path(raw).resolve(), "Updater did not replace its own session's link"
            return server, stable

        def prove_agent(path):
            result = subprocess.run(["ssh-add", "-l"], env={**env, "SSH_AUTH_SOCK": str(path)},
                                    capture_output=True, text=True, timeout=5)
            assert result.returncode == 1 and "no identities" in result.stdout.lower(), result

        try:
            raw1, raw2, raw3 = (start_agent(f"agent-{number}.sock") for number in (1, 2, 3))
            first = attach("probe-original", raw1)
            server1, stable1 = identity()
            first.action("new-pane", "--direction", "right")
            first.until("two original panes", lambda: len(first.terminals()) == 2)
            first.send(b"probe_token=survived; printf '%s\\n' \"$SSH_AUTH_SOCK\" > \"$HOME/retained-socket\"\r")
            first.until("pane records its stable socket", lambda: (home / "retained-socket").exists())
            assert (home / "retained-socket").read_text().strip() == str(stable1)
            original_view = snapshot(first.name)
            assert update(first.name, raw2) == (server1, stable1)
            agents[0].terminate()
            agents[0].wait(timeout=5)
            prove_agent(stable1)
            print("PASS: native /bin/sh helper has the owning server parent; attached update preserves layout and focus.", flush=True)

            detach(first)
            assert update("probe-original", raw3) == (server1, stable1)
            prove_agent(stable1)
            first = attach("probe-original", raw3)
            assert snapshot(first.name) == original_view, "Detached update changed the original workspace"
            first.send(b"printf '%s|%s\\n' \"$probe_token\" \"$SSH_AUTH_SOCK\" > \"$HOME/surviving-pane\"\r")
            first.until("existing pane retains its shell and socket", lambda:
                        (home / "surviving-pane").exists()
                        and (home / "surviving-pane").read_text().strip() == f"survived|{stable1}")
            print("PASS: fully detached update refreshes the original pane's live agent without replacing its shell.", flush=True)

            first.action("rename-session", "probe-renamed")
            first.name = "probe-renamed"
            names.append(first.name)
            replacement = attach("probe-original", raw2)
            server2, stable2 = identity()
            assert server2 != server1 and stable2 != stable1, "Reused visible name inherited the renamed server identity"
            assert stable1.resolve() == Path(raw3).resolve()
            assert update(first.name, raw2) == (server1, stable1)
            assert update(replacement.name, raw3) == (server2, stable2)
            assert stable1.resolve() == Path(raw2).resolve() and stable2.resolve() == Path(raw3).resolve()
            prove_agent(stable1)
            prove_agent(stable2)
            print("PASS: rename keeps the owning identity; reuse of its old name gets an isolated agent link.", flush=True)

            before_failure = snapshot(first.name)
            detach(first)
            first = attach("probe-renamed", str(home / "missing-agent.sock"), failed_update=True)
            assert (home / "updater-failed").read_text().strip() == "invalid raw socket"
            assert snapshot(first.name) == before_failure, "Failed updater changed the existing workspace"
            assert stable1.resolve() == Path(raw2).resolve()
            status = (home / "updater-exit-status").read_text().strip()
            print(f"PASS: failing helper returns through native run (status {status}); attachment still reaches existing panes.", flush=True)
        finally:
            for name in names:
                try:
                    subprocess.run([binary, "kill-session", "--", name], env=env,
                                   capture_output=True, timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            for client in clients:
                client.close()
            for agent in agents:
                if agent.poll() is None:
                    agent.terminate()
                agent.wait(timeout=5)
                agent.stderr.close()


if __name__ == "__main__":
    main()
