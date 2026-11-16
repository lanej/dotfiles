#!/usr/bin/env python3
"""Check stable forwarded agents through real shell startup and temporary agents.

Zellij is controlled here; native reconnects use test-zellij-agent-update.py.
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
        (home / ".ssh").mkdir(mode=0o700)
        (home / ".ssh/rc").symlink_to(ROOT / "sh/ssh-rc")
        (home / ".zshenv").symlink_to(ROOT / "zsh/zshenv")
        attached = home / "attached.json"
        zellij = bindir / "zellij"
        zellij.write_text(f"#!{sys.executable}\n" + '''
import json
import os
from pathlib import Path
import sys
assert sys.argv[1:3] == ["attach", "--create"], sys.argv
Path(os.environ["ATTACHED"]).write_text(json.dumps({
    "args": sys.argv[1:], "socket": os.environ.get("SSH_AUTH_SOCK", ""),
}))
''')
        zellij.chmod(0o755)
        env = {
            "HOME": str(home),
            "PATH": os.pathsep.join((str(bindir), os.environ["PATH"])),
            "SSH_CONNECTION": "127.0.0.1 1111 127.0.0.1 22",
            "ATTACHED": str(attached),
        }
        stable = home / ".ssh/dotfiles-agent/forwarded.sock"
        processes = []

        def start(name):
            socket = home / name
            agent = subprocess.Popen([ssh_agent, "-D", "-a", str(socket)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            processes.append(agent)
            deadline = time.monotonic() + 5
            while not socket.is_socket() and agent.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            assert socket.is_socket(), "Temporary agent did not start"
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
                           env={**env, **updates}, check=True, capture_output=True, text=True,
                           timeout=5)
            return json.loads(attached.read_text())

        def login(socket):
            subprocess.run([shutil.which("zsh"), "-c", '/bin/sh "$HOME/.ssh/rc"'],
                           env={**env, "SSH_AUTH_SOCK": socket},
                           check=True, capture_output=True, text=True)

        def assert_live(socket):
            result = subprocess.run([ssh_add, "-l"], env={**env, "SSH_AUTH_SOCK": str(socket)},
                                    capture_output=True, text=True, timeout=5)
            assert result.returncode == 1 and "no identities" in result.stdout.lower(), result

        try:
            first, old_agent = start("first.sock")
            other, _ = start("other.sock")
            local = home / ".1password/agent.sock"
            local.parent.mkdir()
            local.symlink_to(first)
            assert shell(SSH_CONNECTION="", SSH_AUTH_SOCK=str(local)) == str(local)
            assert attach("local", SSH_CONNECTION="", SSH_AUTH_SOCK=str(local))["socket"] == str(local)
            assert not stable.parent.exists(), "Local launch published an SSH agent"

            # A remote shell selects the path even before the first forwarded login.
            assert shell(SSH_AUTH_SOCK="") == str(stable)
            assert not stable.exists()
            legacy = stable.parent / "zellij-0123456789ab.sock"
            legacy.symlink_to(first)
            login(first)
            assert shell(SSH_AUTH_SOCK=first) == str(stable)
            assert stable.readlink() == Path(first)
            assert_live(stable)
            assert stable.parent.stat().st_mode & 0o077 == 0

            # The attach boundary also normalizes direct callers before starting
            # Zellij, so command panes do not depend on an interactive shell.
            login(other)
            original = attach("work", SSH_AUTH_SOCK=other)
            assert original == {"args": ["attach", "--create", "work"], "socket": str(stable)}
            assert stable.readlink() == Path(other)
            assert legacy.readlink() == Path(first), "Migration replaced an old consumer's link"
            # Even an old non-mux caller selects without republishing its raw
            # socket, while that socket still exists and after it disappears.
            assert shell(SSH_AUTH_SOCK=first) == str(stable)
            assert stable.readlink() == Path(other)
            old_agent.terminate()
            old_agent.wait(timeout=5)
            assert_live(stable)
            assert shell(SSH_AUTH_SOCK=first) == str(stable)
            assert stable.readlink() == Path(other)
            assert shell(SSH_AUTH_SOCK=first, ZELLIJ="0", TMUX="inherited") == str(stable)
            assert stable.readlink() == Path(other), "Mux child republished its stale socket"
            assert shell(SSH_AUTH_SOCK=first, TMUX="fixture") == str(stable)
            assert attach(SSH_AUTH_SOCK="")["socket"] == str(stable)
            assert_live(stable)

            zsh = shutil.which("zsh")
            assert zsh, "zsh is required to verify noninteractive startup"
            selected = subprocess.run([zsh, "-c", 'printf "%s" "$SSH_AUTH_SOCK"'],
                                      env={**env, "SSH_AUTH_SOCK": other}, check=True,
                                      capture_output=True, text=True)
            assert selected.stdout == str(stable), selected

            if not Path("/etc/ssh/sshrc").exists():
                xauth = bindir / "xauth"
                xauth.write_text(f"#!{sys.executable}\n" + '''
import json
import os
from pathlib import Path
import sys
Path(os.environ["HOME"]).joinpath("xauth.json").write_text(json.dumps({
    "args": sys.argv[1:], "input": sys.stdin.read(),
}))
''')
                xauth.chmod(0o755)
                hook = subprocess.run(
                    [zsh, "-c", '/bin/sh "$HOME/.ssh/rc"'],
                    env={**env, "SSH_AUTH_SOCK": other, "DISPLAY": "localhost:10.0"},
                    input="MIT-MAGIC-COOKIE-1 deadbeef\n", check=True,
                    capture_output=True, text=True,
                )
                assert hook.stdout == "", "SSH hook must not write to stdout"
                assert json.loads((home / "xauth.json").read_text()) == {
                    "args": ["-q", "-"],
                    "input": "add unix:10.0 MIT-MAGIC-COOKIE-1 deadbeef\n",
                }, "X11 cookie must travel over stdin, never through process arguments"

            for incoming in (str(home / "missing.sock"), str(local)):
                rejected = subprocess.run([str(bindir / "zellij-agent"), "publish-login"],
                                          env={**env, "SSH_AUTH_SOCK": incoming},
                                          capture_output=True, text=True)
                assert rejected.returncode != 0 and rejected.stderr
                assert stable.readlink() == Path(other), "Rejected login changed the agent"

            stable.unlink()
            stable.write_text("preserve unmanaged file")
            rejected = subprocess.run([str(bindir / "zellij-agent"), "publish-login"],
                                      env={**env, "SSH_AUTH_SOCK": other}, capture_output=True)
            assert rejected.returncode != 0
            assert stable.read_text() == "preserve unmanaged file"
            print("PASS: local agents are preserved; remote shells and direct attachments inherit one stable socket.")
            print("PASS: reconnects refresh existing consumers; stale mux children and unsafe sources cannot replace it.")
        finally:
            for agent in processes:
                if agent.poll() is None:
                    agent.terminate()
                agent.wait(timeout=5)
                agent.stderr.close()


if __name__ == "__main__":
    main()
