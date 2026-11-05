#!/usr/bin/env python3
"""Probe a shell-only agent updater on the pinned native Zellij runtime.

Run after installing the pinned runtime:
    python3 scripts/test-zellij-agent-update.py

Exercises the actual zellij-agent, fix-ssh, and zellij-attach entrypoints.
Sockets, configuration, and sessions are private temporary fixtures. No status
build, repository shell startup, or Python helper inside a pane is required.
"""

import json
import os
import re
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
Terminal = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))["Terminal"]


def main():
    binary, agent_binary = shutil.which("zellij"), shutil.which("ssh-agent")
    assert binary and agent_binary and shutil.which("ssh-add"), "Install pinned Zellij and OpenSSH"
    with tempfile.TemporaryDirectory(prefix="zj-agent-probe-", dir="/tmp") as directory:
        temporary = Path(directory).resolve()
        home, runtime, temp_files = (temporary / name for name in ("home", "run", "tmp"))
        for path in (home, runtime, temp_files):
            path.mkdir(mode=0o700)
        bindir = home / ".local/bin"
        bindir.mkdir(parents=True)
        for name in ("zellij-agent", "fix-ssh", "zellij-attach"):
            (bindir / name).symlink_to(ROOT / "bin" / name)
        shell = home / "pane-shell"
        shell.write_text('''#!/bin/sh
. "$HOME/.local/bin/fix-ssh" || exit
parent=$(ps -ww -p "$PPID" -o command=) || exit
case "$parent" in *' --server '*) ;; *) exit 72 ;; esac
server=${parent#* --server }
server=${server% --debug}
printf '%s\\n%s\\n%s\\n' "$parent" "$server" "$SSH_AUTH_SOCK" > "$HOME/.parent-identity-$$"
mv -f "$HOME/.parent-identity-$$" "$HOME/parent-identity"
export PS1='agent-probe-ready> '
exec /bin/sh -i
''')
        shell.chmod(0o700)
        config = home / ".config/zellij"
        (config / "layouts").mkdir(parents=True)
        (config / "layouts/probe.kdl").write_text(
            'layout {\n'
            '    pane split_direction="vertical" {\n'
            '        pane\n'
            '        pane focus=true\n'
            '    }\n'
            '}\n'
        )
        (config / "config.kdl").write_text(
            f'default_shell {json.dumps(str(shell))}\n'
            'default_layout "probe"\n'
            'show_startup_tips false\n'
            'show_release_notes false\n'
            'keybinds clear-defaults=true {\n'
            '    normal {\n'
            '        bind "Ctrl f" { Detach; }\n'
            '    }\n'
            '}\n'
        )
        env = {
            **os.environ, "HOME": str(home), "SHELL": "/bin/sh", "TERM": "xterm-256color",
            "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(temporary / "cache"),
            "XDG_DATA_HOME": str(temporary / "data"), "XDG_RUNTIME_DIR": str(runtime),
            "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temp_files),
            "SSH_CONNECTION": "127.0.0.1 2222 127.0.0.1 22",
            "PATH": str(bindir) + os.pathsep + os.environ["PATH"],
        }
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        clients, agents, names = [], [], []

        def command(args, check=True, **updates):
            with subprocess.Popen(args, env={**env, **updates}, stdout=subprocess.PIPE,
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
            floating_visible = {tab["tab_id"]: tab["are_floating_panes_visible"] for tab in tabs}

            def pane_state(pane):
                values = dict(pane)
                # Native add_client() restores a floating-layer focus entry even
                # while that layer is hidden. This is not visible keyboard focus.
                # Preserve every pane/geometry field and all visible focus bits.
                if pane["is_floating"] and not floating_visible[pane["tab_id"]]:
                    values["is_focused"] = False
                return tuple(values.get(key) for key in keys)

            return (sorted(pane_state(pane) for pane in panes),
                    sorted((t["tab_id"], t["name"], t["active"],
                            t["are_floating_panes_visible"])
                           for t in tabs))

        def assert_snapshot(name, expected, message):
            observed = snapshot(name)
            if observed != expected:
                print(message + ": " + json.dumps({
                    "expected": expected, "observed": observed,
                    "panes": json.loads(action(name, "list-panes", "--json")),
                    "tabs": json.loads(action(name, "list-tabs", "--json")),
                }), flush=True)
                raise AssertionError(message)

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

        def attach(name, raw):
            if name not in names:
                names.append(name)
            client = Terminal(binary, {**env, "SSH_AUTH_SOCK": raw}, name,
                              command=[str(bindir / "zellij-attach"), name],
                              install_navigation=False)
            clients.append(client)
            client.until("native shell is ready", lambda: b"agent-probe-ready>" in client.output)
            return client

        def prepare_tiled_workspace(client):
            # Establish the fixture only when creating a fresh session. Never
            # repair focus/layer state after an updater or after reconnecting.
            panes, tabs = client.panes(), client.tabs()
            print(f"Initial workspace {client.name}: " + json.dumps({"panes": panes, "tabs": tabs}), flush=True)
            tiled = [pane for pane in panes if not pane["is_plugin"] and not pane["is_floating"]]
            assert len(tiled) == 2, "Probe layout did not create two tiled shell panes"
            if any(tab["active"] and tab["are_floating_panes_visible"] for tab in tabs):
                client.action("toggle-floating-panes")
            target = max(tiled, key=lambda pane: pane["pane_x"])
            observed = {}

            def ready():
                current_panes, current_tabs = client.terminals(), client.tabs()
                screens = {str(pane["id"]): client.action(
                    "dump-screen", "--pane-id", f"terminal_{pane['id']}") for pane in tiled}
                checks = {
                    "right_tiled_pane_focused": any(pane["id"] == target["id"] and pane["is_focused"]
                                                   for pane in current_panes),
                    "floating_layer_hidden": not any(tab["are_floating_panes_visible"] for tab in current_tabs),
                    "both_shell_prompts_ready": all("agent-probe-ready>" in screen for screen in screens.values()),
                }
                observed.update(checks=checks, panes=current_panes, tabs=current_tabs, screens=screens)
                return all(checks.values())

            try:
                client.until("fixture has tiled focus and ready shells", ready)
            except AssertionError:
                print("Fixture readiness components and dump-screen output: " + json.dumps(observed), flush=True)
                raise
            print(f"Prepared workspace {client.name}: " + json.dumps({
                "panes": client.panes(), "tabs": client.tabs(),
            }), flush=True)

        def detach(client):
            # Close the transport like an SSH disconnect, without depending on
            # first-run UI/keybinding state or sending keys into a shell.
            client.close()
            clients.remove(client)
            deadline = time.monotonic() + 5
            while re.search(r"^\s*\d+\s", action(client.name, "list-clients"), re.MULTILINE):
                assert time.monotonic() < deadline, "Client remained connected after closing its PTY"
                time.sleep(0.02)

        def identity():
            parent, server, stable = (home / "parent-identity").read_text().splitlines()
            assert " --server " in parent and Path(server).is_socket(), parent
            return server, Path(stable)

        def update(name, raw, stable):
            before = snapshot(name)
            command([str(bindir / "zellij-agent"), "refresh", name], SSH_AUTH_SOCK=raw)
            deadline = time.monotonic() + 5
            while snapshot(name) != before:
                if time.monotonic() >= deadline:
                    assert_snapshot(name, before, "Updater changed pane IDs, visible focus, tabs, or geometry")
                    break
                time.sleep(0.02)
            assert stable.resolve() == Path(raw).resolve(), "Updater did not replace its own session's link"

        def prove_agent(path):
            result = subprocess.run(["ssh-add", "-l"], env={**env, "SSH_AUTH_SOCK": str(path)},
                                    capture_output=True, text=True, timeout=5)
            assert result.returncode == 1 and "no identities" in result.stdout.lower(), result

        try:
            raw1, raw2, raw3 = (start_agent(f"agent-{number}.sock") for number in (1, 2, 3))
            first = attach("probe-original", raw1)
            prepare_tiled_workspace(first)
            server1, stable1 = identity()
            first.send(b"probe_token=survived; printf '%s\\n' \"$SSH_AUTH_SOCK\" > \"$HOME/retained-socket\"\r")
            first.until("pane records its stable socket", lambda: (home / "retained-socket").exists())
            assert (home / "retained-socket").read_text().strip() == str(stable1)
            original_view = snapshot(first.name)
            update(first.name, raw2, stable1)
            agents[0].terminate()
            agents[0].wait(timeout=5)
            prove_agent(stable1)
            # Zellij inside tmux inherits TMUX, but must recover from its own
            # actual server rather than selecting the outer tmux agent.
            first.send((f"SSH_AUTH_SOCK={shlex.quote(raw1)}; TMUX=inherited; export TMUX SSH_AUTH_SOCK; "
                        '. "$HOME/.local/bin/fix-ssh"; '
                        'printf "%s\\n" "$SSH_AUTH_SOCK" > "$HOME/nested-socket"; unset TMUX\r').encode())
            first.until("nested Zellij retains its own agent", lambda:
                        (home / "nested-socket").exists()
                        and (home / "nested-socket").read_text().strip() == str(stable1))
            assert stable1.resolve() == Path(raw2).resolve(), "old pane republished its stale socket"
            print("PASS: native /bin/sh helper has the owning server parent; attached update preserves layout and focus.", flush=True)

            detach(first)
            first = attach("probe-original", raw3)
            assert stable1.resolve() == Path(raw3).resolve(), "Real launcher did not refresh the detached session"
            prove_agent(stable1)
            print("Reattached workspace: " + json.dumps({
                "panes": first.panes(), "tabs": first.tabs(),
            }), flush=True)
            assert_snapshot(first.name, original_view, "Detached update changed the original workspace")
            first.send(b"printf '%s|%s\\n' \"$probe_token\" \"$SSH_AUTH_SOCK\" > \"$HOME/surviving-pane\"\r")
            first.until("existing pane retains its shell and socket", lambda:
                        (home / "surviving-pane").exists()
                        and (home / "surviving-pane").read_text().strip() == f"survived|{stable1}")
            print("PASS: fully detached update refreshes the original pane's live agent without replacing its shell.", flush=True)

            first.action("rename-session", "probe-renamed")
            first.name = "probe-renamed"
            names.append(first.name)
            replacement = attach("probe-original", raw2)
            prepare_tiled_workspace(replacement)
            server2, stable2 = identity()
            assert server2 != server1 and stable2 != stable1, "Reused visible name inherited the renamed server identity"
            assert stable1.resolve() == Path(raw3).resolve()
            update(first.name, raw2, stable1)
            update(replacement.name, raw3, stable2)
            assert stable1.resolve() == Path(raw2).resolve() and stable2.resolve() == Path(raw3).resolve()
            prove_agent(stable1)
            prove_agent(stable2)
            print("PASS: rename keeps the owning identity; reuse of its old name gets an isolated agent link.", flush=True)

            before_failure = snapshot(first.name)
            missing_socket = str(home / "missing-agent.sock")
            failed = command([str(bindir / "zellij-agent"), "refresh", first.name],
                             check=False, SSH_AUTH_SOCK=missing_socket)
            assert failed.returncode != 0, "Refresh falsely accepted a missing socket"
            detach(first)
            first = attach("probe-renamed", missing_socket)
            assert_snapshot(first.name, before_failure, "Failed updater changed the existing workspace")
            assert stable1.resolve() == Path(raw2).resolve()
            print(f"PASS: actual refresh rejects a missing socket (status {failed.returncode}); actual launcher still attaches to existing panes.", flush=True)
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
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(f"Native CLI failed: {error.cmd}\nstdout:\n{error.stdout}\nstderr:\n{error.stderr}", flush=True)
        raise
