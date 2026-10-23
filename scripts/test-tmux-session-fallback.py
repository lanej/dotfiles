"""Close windows and sessions through a real tmux server with popup clients."""

from pathlib import Path
import os
import subprocess
import tempfile
import time


def main():
    root = Path(__file__).resolve().parents[1]
    binary = os.environ.get("TMUX_TEST_BINARY", "tmux")
    env = {key: value for key, value in os.environ.items() if key not in ("TMUX", "TMUX_PANE")}
    clients = []
    with tempfile.TemporaryDirectory(prefix="tmux-fallback-") as directory:
        socket = str(Path(directory) / "socket")
        command = [binary, "-S", socket]

        def tmux(*args):
            return subprocess.run(command + list(args), env=env, text=True,
                                  capture_output=True, check=True).stdout.strip()

        def wait_for(predicate, description):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(0.02)
            raise AssertionError(description)

        def attach(session):
            client = subprocess.Popen(command + ["-C", "attach-session", "-t", session],
                                      env=env, stdin=subprocess.PIPE,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            clients.append(client)
            wait_for(lambda: str(client.pid) in tmux("list-clients", "-F", "#{client_pid}"),
                     f"Client failed to attach to {session}")
            return client

        def client_session(client):
            rows = tmux("list-clients", "-F", "#{client_pid}|#{session_name}").splitlines()
            return next((row.split("|", 1)[1] for row in rows
                         if row.split("|", 1)[0] == str(client.pid)), None)

        try:
            tmux("-f", str(root / "rc/tmux-session-fallback.conf"),
                 "new-session", "-d", "-s", "first", "exec /bin/sh")
            tmux("new-window", "-t", "first:", "-n", "extra", "exec /bin/sh")
            tmux("new-session", "-d", "-s", "second", "exec /bin/sh")
            tmux("new-session", "-d", "-s", "popup", "exec /bin/sh")
            regular = attach("first")
            popup = attach("popup")
            # Wait until both client hooks have established their attachments.
            wait_for(lambda: tmux("show-options", "-g").count("@fallback-session-") == 2,
                     "Client tracking was not established")

            tmux("kill-window", "-t", "first:extra")
            assert client_session(regular) == "first", "Closing one window detached the client"
            tmux("send-keys", "-t", "first:", "exit", "Enter")
            wait_for(lambda: client_session(regular) == "second",
                     "Closing the first session did not switch to the remaining regular session")
            assert client_session(popup) == "popup", "An intentional popup client was moved"

            # Closing the intentional popup returns to its parent terminal.
            tmux("send-keys", "-t", "popup:", "exit", "Enter")
            popup.wait(timeout=5)
            assert client_session(regular) == "second", "Closing popup disturbed the regular client"
            tmux("new-session", "-d", "-s", "popup", "exec /bin/sh")
            tmux("send-keys", "-t", "second:", "exit", "Enter")
            regular.wait(timeout=5)
            assert tmux("list-sessions", "-F", "#{session_name}") == "popup"
            assert not tmux("list-clients"), "The final regular client stayed attached to popup"
            print("PASS: window/session closure preserves regular clients and excludes popup.")
        finally:
            subprocess.run(command + ["kill-server"], env=env, capture_output=True)
            for client in clients:
                if client.poll() is None:
                    client.terminate()
                client.wait(timeout=5)
                client.stdin.close()
                client.stderr.close()


if __name__ == "__main__":
    main()
