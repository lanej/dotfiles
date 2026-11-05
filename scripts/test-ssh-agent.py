#!/usr/bin/env python3
"""Check local-agent preservation, tmux selection, and fail-open attachment.

The multiplexer CLI is controlled; ssh-add uses real temporary agent sockets.
Native reconnect behavior is covered by test-zellij-agent-update.py.
"""
from pathlib import Path
import json
import os
import shutil
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
        # A failed or unavailable native updater must never block attachment.
        zellij = bindir / "zellij"
        zellij.write_text(f"#!{sys.executable}\n" + '''
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
if args[:1] == ["--session"]:
    raise SystemExit(17)
assert args[:2] == ["attach", "--create"], args
Path(os.environ["ATTACHED"]).write_text(json.dumps({
    "args": args, "socket": os.environ.get("SSH_AUTH_SOCK", ""),
}))
''')
        zellij.chmod(0o755)
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

        def assert_live(socket):
            result = subprocess.run([ssh_add, "-l"], env={**env, "SSH_AUTH_SOCK": socket},
                                    capture_output=True, text=True)
            assert result.returncode == 1 and "no identities" in result.stdout.lower(), result

        try:
            first, _ = start("first.sock")
            other, _ = start("other.sock")
            local = home / ".1password/agent.sock"
            local.parent.mkdir()
            local.symlink_to(first)
            assert shell(SSH_CONNECTION="", SSH_AUTH_SOCK=str(local)) == str(local)
            local_pane = attach("local", SSH_CONNECTION="", SSH_AUTH_SOCK=str(local))
            assert local_pane["socket"] == str(local), "local 1Password-style socket was changed"
            assert not (home / ".ssh/dotfiles-agent").exists(), "local launch published an SSH agent"

            failed_update = attach("work", SSH_AUTH_SOCK=first)
            assert failed_update["socket"] == first, "failed recovery replaced the incoming socket"
            assert failed_update["args"] == ["attach", "--create", "work"]
            assert_live(first)
            assert attach(SSH_AUTH_SOCK=other)["args"] == ["attach", "--create", "main"]
            assert attach("work")["socket"] == "", "unforwarded attachment borrowed an agent"
            assert shell(ZELLIJ="0", SSH_AUTH_SOCK="") == "", "unforwarded pane borrowed an agent"
            # Local 1Password sockets may be symlinks and must not be republished
            # even if someone exports one in a remote environment.
            assert attach("work", SSH_AUTH_SOCK=str(local))["socket"] == str(local)
            assert not (home / ".ssh/dotfiles-agent").exists()
            assert shell(SSH_AUTH_SOCK=first, ZELLIJ="0", TMUX="fixture",
                         TMUX_SESSION_SOCKET=other) == other, "inherited ZELLIJ blocked tmux recovery"
            (bindir / "zellij-agent").unlink()
            assert attach("work", SSH_AUTH_SOCK=first)["socket"] == first, "missing helper blocked attach"
            assert shell(SSH_AUTH_SOCK="", ZELLIJ="0", TMUX="fixture",
                         TMUX_SESSION_SOCKET=other) == other, "missing helper or socket blocked tmux recovery"

            tmux_pane = shell(SSH_AUTH_SOCK=first, TMUX="fixture", TMUX_SESSION_SOCKET=other)
            assert tmux_pane == other, "tmux ignored its session's show-environment socket"
            assert_live(tmux_pane)
            assert shell(SSH_CONNECTION="", SSH_AUTH_SOCK=str(local), TMUX="fixture",
                         TMUX_SESSION_SOCKET=other) == str(local), "local tmux changed its agent"
            print("PASS: local agents and tmux selection are preserved; failed recovery never blocks attachment.")
        finally:
            for agent in processes:
                if agent.poll() is None:
                    agent.terminate()
                agent.wait(timeout=5)
                if agent.stderr is not None:
                    agent.stderr.close()


if __name__ == "__main__":
    main()
