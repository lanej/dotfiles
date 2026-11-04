#!/usr/bin/env python3
"""A forwarded agent reconnects while a shell retains its old mux environment."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="dotfiles-agent-", dir="/tmp") as directory:
        home = Path(directory)
        (home / ".local/bin").mkdir(parents=True)
        (home / ".local/bin/fix-ssh").symlink_to(ROOT / "bin/fix-ssh")
        env = {"HOME": str(home), "PATH": os.environ["PATH"],
               "SSH_CONNECTION": "127.0.0.1 1111 127.0.0.1 22"}
        processes = []

        def start(name):
            socket = home / name
            agent = subprocess.Popen([shutil.which("ssh-agent"), "-D", "-a", str(socket)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            processes.append(agent)
            deadline = time.monotonic() + 5
            while not socket.is_socket() and agent.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            assert socket.is_socket(), "agent socket missing"
            return str(socket), agent

        def shell(script, **updates):
            return subprocess.run(["/bin/bash", "-c", script], env={**env, **updates},
                                  check=True, capture_output=True, text=True).stdout.strip()

        try:
            first, agent = start("first.sock")
            stable = shell('. "$HOME/.local/bin/fix-ssh"; printf "%s" "$SSH_AUTH_SOCK"',
                           SSH_AUTH_SOCK=first)
            assert Path(stable).is_symlink() and Path(stable).resolve() == Path(first)
            agent.terminate()
            agent.wait(timeout=5)
            second, _ = start("second.sock")
            shell('. "$HOME/.local/bin/fix-ssh"', SSH_AUTH_SOCK=second)
            assert Path(stable).resolve() == Path(second), "fresh login did not refresh link"
            unforwarded = shell('. "$HOME/.local/bin/fix-ssh"; printf "%s" "${SSH_AUTH_SOCK:-}"')
            assert not unforwarded, "unforwarded login borrowed another login's agent"
            # Existing panes must not publish their inherited old socket back over the new login.
            observed = shell('. "$HOME/.local/bin/fix-ssh"; printf "%s" "$SSH_AUTH_SOCK"',
                             SSH_AUTH_SOCK=first, TMUX="fixture", ZELLIJ="0")
            assert observed == stable
            result = subprocess.run(["ssh-add", "-l"], env={**env, "SSH_AUTH_SOCK": observed},
                                    capture_output=True, text=True)
            assert result.returncode == 1 and "no identities" in result.stdout.lower(), result
            print("PASS: reconnect refreshes a stable forwarded socket for surviving mux panes.")
        finally:
            for agent in processes:
                if agent.poll() is None:
                    agent.terminate()
                agent.wait(timeout=5)


if __name__ == "__main__":
    main()
