#!/usr/bin/env python3
"""Check session-scoped reconnects through the launcher with real agent sockets.

The Zellij CLI is simulated; this checks launcher and shell behavior, not Zellij's
terminal integration. ssh-add talks to real ssh-agent processes through the links.
"""
from pathlib import Path
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    ssh_agent, ssh_add = shutil.which("ssh-agent"), shutil.which("ssh-add")
    assert ssh_agent and ssh_add, "ssh-agent and ssh-add are required"
    with tempfile.TemporaryDirectory(prefix="dotfiles-agent-", dir="/tmp") as directory:
        home = Path(directory)
        bindir = home / ".local/bin"
        bindir.mkdir(parents=True)
        for name in ("fix-ssh", "zellij-agent", "zellij-attach"):
            (bindir / name).symlink_to(ROOT / "bin" / name)
        attached = home / "attached.json"
        # A new pane inherits the launcher environment and then sources fix-ssh.
        # Running this on every attach also detects an old pane republishing a
        # stale socket instead of keeping the latest login's session link.
        zellij = bindir / "zellij"
        zellij.write_text(f"#!{sys.executable}\n" + '''
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

args = sys.argv[1:]
cache = Path(os.environ["HOME"]) / "zellij-cache"
if args == ["setup", "--check"]:
    print("[CACHE DIR]: " + str(cache))
else:
    if args[:2] == ["attach", "--create"]:
        session = args[2]
    else:
        raise AssertionError(args)
    index = cache / "contract_version_1/session_index.sqlite"
    index.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(index) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS sessions (name TEXT PRIMARY KEY, id TEXT)")
        connection.execute("INSERT OR IGNORE INTO sessions (name, id) VALUES (?, ?)",
                           (session, str(uuid.uuid4())))
    connection.close()
    pane = subprocess.run(
        ["/bin/bash", "-c", '. "$HOME/.local/bin/fix-ssh" || exit; '
         'printf "%s" "${SSH_AUTH_SOCK:-}"'],
        env={**os.environ, "ZELLIJ": "0", "ZELLIJ_SESSION_NAME": session},
        check=True, capture_output=True, text=True,
    )
    Path(os.environ["ATTACHED"]).write_text(json.dumps({
        "args": args, "session": session, "socket": pane.stdout,
        "launcher_socket": os.environ.get("SSH_AUTH_SOCK", ""),
    }))
''')
        zellij.chmod(0o755)
        ssh = bindir / "ssh"
        ssh.write_text(f"#!{sys.executable}\n" + '''
import os
import sys

assert len(sys.argv) == 4 and sys.argv[1:3] == ["-t", "fixture-host"], sys.argv
# SSH starts a noninteractive shell; zssh then selects its login shell.
# Isolate HOME, SHELL, and PATH from the developer machine's startup files.
env = dict(os.environ)
env["SHELL"] = os.path.join(env["HOME"], ".local/bin/remote-shell")
os.execve("/bin/bash", ["/bin/bash", "--noprofile", "--norc", "-c", sys.argv[3]], env)
''')
        ssh.chmod(0o755)
        remote_shell = bindir / "remote-shell"
        remote_shell.write_text(f"#!{sys.executable}\n" + '''
import os
import sys

assert sys.argv[1] == "-lic", sys.argv
# Exercise the real interactive login command with controlled startup. The
# separate attach detector covers repository rc files and remote PATH setup.
os.execv("/bin/bash", ["/bin/bash", "--noprofile", "--norc", *sys.argv[1:]])
''')
        remote_shell.chmod(0o755)
        tmux = bindir / "tmux"
        tmux.write_text(f"#!{sys.executable}\n" + '''
import os
import sys

assert len(sys.argv) == 3 and sys.argv[1] == "show-environment", sys.argv
values = {
    "SSH_AUTH_SOCK": os.environ["TMUX_SESSION_SOCKET"],
    "SSH_CONNECTION": "127.0.0.1 2222 127.0.0.1 22",
    "SSH_CLIENT": "127.0.0.1 2222 22",
}
print(sys.argv[2] + "=" + values[sys.argv[2]])
''')
        tmux.chmod(0o755)
        env = {
            "HOME": str(home),
            "PATH": os.pathsep.join((str(bindir), os.environ["PATH"])),
            "SSH_CONNECTION": "127.0.0.1 1111 127.0.0.1 22",
            "ATTACHED": str(attached),
        }
        processes = []

        def start(name):
            socket = home / name
            agent = subprocess.Popen([ssh_agent, "-D", "-a", str(socket)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            processes.append(agent)
            deadline = time.monotonic() + 5
            while not socket.is_socket() and agent.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            if not socket.is_socket():
                detail = agent.stderr.read().decode() if agent.poll() is not None else "agent startup timed out"
                raise AssertionError(f"agent socket missing: {detail}")
            return str(socket), agent

        def shell(**updates):
            return subprocess.run(
                ["/bin/bash", "-c", '. "$HOME/.local/bin/fix-ssh" || exit; '
                 'printf "%s" "${SSH_AUTH_SOCK:-}"'],
                env={**env, **updates}, check=True, capture_output=True, text=True,
            ).stdout

        def attach(*args, **updates):
            attached.unlink(missing_ok=True)
            subprocess.run([str(bindir / "zellij-attach"), *args],
                           env={**env, **updates}, check=True, capture_output=True, text=True)
            return json.loads(attached.read_text())

        def remote_attach(session, **updates):
            attached.unlink(missing_ok=True)
            subprocess.run(
                ["/bin/bash", "-c", 'source "$1"; zssh fixture-host "$2"',
                 "zssh-check", str(ROOT / "sh/functions"), session],
                env={**env, **updates}, check=True, capture_output=True, text=True,
            )
            return json.loads(attached.read_text())

        def assert_live(socket):
            result = subprocess.run([ssh_add, "-l"], env={**env, "SSH_AUTH_SOCK": socket},
                                    capture_output=True, text=True)
            assert result.returncode == 1 and "no identities" in result.stdout.lower(), result

        try:
            first, first_agent = start("first.sock")
            other, _ = start("other.sock")
            local = home / ".1password/agent.sock"
            local.parent.mkdir()
            local.symlink_to(first)
            assert shell(SSH_CONNECTION="", SSH_AUTH_SOCK=str(local)) == str(local)
            local_pane = attach("local", SSH_CONNECTION="", SSH_AUTH_SOCK=str(local))
            assert local_pane["socket"] == str(local), "local 1Password-style socket was changed"
            assert not (home / ".ssh/dotfiles-agent").exists(), "local launch published an SSH agent"

            session, other_session = "project 'alpha'", "project-alpha"
            initial = remote_attach(session, SSH_AUTH_SOCK=first)
            stable = initial["socket"]
            assert initial["args"] == ["attach", "--create", session], initial
            assert initial["launcher_socket"] == first, "new session published before it had an identity"
            assert Path(stable).is_symlink() and Path(stable).resolve() == Path(first).resolve()
            assert stat.S_IMODE(Path(stable).parent.stat().st_mode) == 0o700
            another = attach(other_session, SSH_AUTH_SOCK=other)
            other_stable = another["socket"]
            assert stable != other_stable, "different sessions shared one agent link"
            assert Path(other_stable).resolve() == Path(other).resolve()
            # Retain the environment from the original pane, as a running shell
            # does across detach/reconnect. It must work without another source.
            retained_socket = stable
            first_agent.terminate()
            first_agent.wait(timeout=5)
            replacement, _ = start("replacement.sock")
            reattached = attach(session, SSH_AUTH_SOCK=replacement)
            assert reattached["args"] == ["attach", "--create", session], reattached
            assert reattached["launcher_socket"] == replacement, "attach replaced the client's raw agent with a session link"
            client_created = attach("client-created", SSH_AUTH_SOCK=reattached["launcher_socket"])
            assert client_created["socket"] != retained_socket, "session created from the client inherited another session's link"
            assert Path(client_created["socket"]).resolve() == Path(replacement).resolve()
            assert reattached["socket"] == retained_socket, "reconnect changed the pane's stable path"
            assert Path(retained_socket).resolve() == Path(replacement).resolve(), "attach did not refresh its session"
            assert_live(retained_socket)
            assert Path(other_stable).resolve() == Path(other).resolve(), "reconnect replaced another session's agent"
            assert_live(other_stable)

            previous = replacement
            replacement, _ = start("remote-replacement.sock")
            remote = remote_attach(session, SSH_AUTH_SOCK=replacement)
            assert remote["args"] == ["attach", "--create", session], remote
            assert remote["socket"] == retained_socket
            assert Path(retained_socket).resolve() == Path(replacement).resolve(), "noninteractive zssh did not refresh its session"
            assert_live(retained_socket)
            assert Path(other_stable).resolve() == Path(other).resolve()

            old_live_pane = shell(SSH_AUTH_SOCK=previous, ZELLIJ="0", ZELLIJ_SESSION_NAME=session)
            assert old_live_pane == stable
            assert Path(stable).resolve() == Path(replacement).resolve(), "old pane republished its still-live previous socket"
            stale_pane = shell(SSH_AUTH_SOCK=first, ZELLIJ="0", ZELLIJ_SESSION_NAME=session)
            assert stale_pane == stable, "old pane did not recover its session's current socket"
            assert Path(stable).resolve() == Path(replacement).resolve(), "old pane republished its stale socket"
            other_pane = shell(SSH_AUTH_SOCK=other, ZELLIJ="0", ZELLIJ_SESSION_NAME=other_session)
            assert other_pane == other_stable, "another session adopted the reconnecting session's socket"

            unforwarded = attach(session)
            assert not unforwarded["socket"], "unforwarded attach borrowed an existing session's agent"
            assert not shell(ZELLIJ="0", ZELLIJ_SESSION_NAME="unforwarded"), "unforwarded pane borrowed another session's agent"
            assert Path(stable).resolve() == Path(replacement).resolve()
            assert Path(other_stable).resolve() == Path(other).resolve()

            # Renaming retains the immutable ID, while reuse of its old name
            # creates a different session. A surviving pane still has the old
            # ZELLIJ_SESSION_NAME, but must keep its own stable socket.
            renamed = "renamed alpha"
            index = home / "zellij-cache/contract_version_1/session_index.sqlite"
            with sqlite3.connect(index) as connection:
                connection.execute("UPDATE sessions SET name = ? WHERE name = ?", (renamed, session))
            connection.close()
            reused = attach(session, SSH_AUTH_SOCK=other)
            reused_socket = reused["socket"]
            assert reused_socket not in (retained_socket, other_stable), "reused name inherited an existing session's agent link"
            assert Path(reused_socket).resolve() == Path(other).resolve()
            assert Path(retained_socket).resolve() == Path(replacement).resolve(), "name reuse repointed the renamed session's panes"
            retained_pane = shell(SSH_AUTH_SOCK=retained_socket, ZELLIJ="0", ZELLIJ_SESSION_NAME=session)
            assert retained_pane == retained_socket, "stale pane name redirected to the replacement session"
            renamed_agent, _ = start("renamed.sock")
            renamed_attach = remote_attach(renamed, SSH_AUTH_SOCK=renamed_agent)
            assert renamed_attach["socket"] == retained_socket, "rename changed the existing pane's stable path"
            assert Path(retained_socket).resolve() == Path(renamed_agent).resolve(), "renamed reconnect left existing panes stale"
            assert_live(retained_socket)
            assert Path(reused_socket).resolve() == Path(other).resolve(), "renamed reconnect replaced the reused session's agent"
            assert Path(other_stable).resolve() == Path(other).resolve()

            created = attach(SSH_AUTH_SOCK=replacement)
            assert created["args"] == ["attach", "--create", "main"], "unnamed attach did not use main"
            assert created["socket"] not in (stable, other_stable)
            assert Path(created["socket"]).is_symlink()
            assert Path(created["socket"]).resolve() == Path(replacement).resolve(), "first pane did not initialize its session"
            assert_live(created["socket"])
            main_reconnected = attach(SSH_AUTH_SOCK=renamed_agent)
            assert main_reconnected["args"] == ["attach", "--create", "main"]
            assert main_reconnected["socket"] == created["socket"], "default main reconnect changed its stable link"
            assert Path(created["socket"]).resolve() == Path(renamed_agent).resolve(), "default main reconnect did not refresh its agent"

            tmux_pane = shell(SSH_AUTH_SOCK=first, TMUX="fixture", TMUX_SESSION_SOCKET=other)
            assert tmux_pane == other, "tmux ignored its session's show-environment socket"
            assert_live(tmux_pane)
            assert shell(SSH_CONNECTION="", SSH_AUTH_SOCK=str(local), TMUX="fixture",
                         TMUX_SESSION_SOCKET=other) == str(local), "local tmux changed its agent"
            print("PASS: session-scoped reconnects preserve panes across rename/name reuse, other sessions, local agents, and tmux recovery.")
        finally:
            for agent in processes:
                if agent.poll() is None:
                    agent.terminate()
                agent.wait(timeout=5)
                if agent.stderr is not None:
                    agent.stderr.close()


if __name__ == "__main__":
    main()
