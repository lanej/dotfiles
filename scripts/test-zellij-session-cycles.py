#!/usr/bin/env python3
"""Reject recursive switches, renames, and direct attachments in a private PTY."""

import argparse
import os
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
Terminal = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))["Terminal"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default=shutil.which("zellij"))
    args = parser.parse_args()
    assert args.binary, "Install the pinned Zellij runtime first"
    binary = str(Path(args.binary).resolve())
    with tempfile.TemporaryDirectory(prefix="zj-cycle-", dir="/tmp") as directory:
        temporary = Path(directory)
        home = temporary / "home"
        config = home / ".config/zellij"
        config.mkdir(parents=True)
        runtime = temporary / "run"
        runtime.mkdir(mode=0o700)
        temp_files = temporary / "tmp"
        temp_files.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": "cycle-ready> ",
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(temporary / "cache"), "XDG_DATA_HOME": str(temporary / "data"),
               "XDG_STATE_HOME": str(temporary / "state"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temp_files),
               "ZELLIJ_PEER_SCAN_INTERVAL_MS": "50"}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_NESTED_ATTACH", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "SSH_CONNECTION", "SSH_TTY",
                    "ENV", "BASH_ENV"):
            env.pop(key, None)
        data = (home / "Library/Application Support/org.Zellij-Contributors.Zellij"
                if sys.platform == "darwin" else temporary / "data/zellij")
        data.mkdir(parents=True)
        (data / "desktop_integration.json").write_text('{"flags":["SetupNeverShow"]}\n')
        host, guest, unrelated = "cycle-host", "cycle-guest", "cycle-unrelated"
        owned_names = {host, guest, unrelated}
        common = ('default_mode "locked"\ndefault_shell "/bin/sh"\n'
                  'session_serialization false\nnested_session_handling "descend"\n'
                  'attention { idle_rule "watched"; }\n'
                  f'layout_dir "{config / "layouts"}"\n'
                  'default_layout "bare"\nshow_startup_tips false\nshow_release_notes false\n')
        (config / "config.kdl").write_text(common)
        layouts = config / "layouts"
        layouts.mkdir()
        (layouts / "bare.kdl").write_text('layout { pane command="/bin/sh"; }\n')
        guest_config = temporary / "guest.kdl"
        guest_config.write_text(common + 'keybinds { locked {\n'
                                f'bind "Ctrl y" {{ SwitchSession name="{host}"; }}\n'
                                f'bind "Ctrl u" {{ SwitchSession name="{host}" close_current=true; }}\n'
                                f'bind "Ctrl t" {{ SwitchSession name="{guest}" close_current=true; }}\n'
                                f'bind "Ctrl r" {{ SwitchSession name="{unrelated}"; }}\n'
                                '}\n}\n')
        terminal = Terminal(binary, env, host, install_navigation=False)
        try:
            terminal.until("outer shell starts", lambda: b"cycle-ready> " in terminal.output)
            outer = terminal.terminals()[0]
            child = ["env", "-u", "ZELLIJ", "-u", "ZELLIJ_SESSION_NAME", "-u", "ZELLIJ_PANE_ID",
                     binary, "--config", str(guest_config)]
            terminal.action("new-pane", "--floating", "--", *child, "attach", "--create", guest)
            log = temp_files / f"zellij-{os.getuid()}" / "zellij-log/zellij.log"
            terminal.until("nested handshake completes", lambda:
                           log.exists() and "nested session handshake complete" in log.read_text())
            terminal.drain(3.2)
            nested = next(pane for pane in terminal.terminals() if pane["is_floating"])
            def reject_switch(key):
                before = len(terminal.output)
                offset = log.stat().st_size
                terminal.send(key)
                terminal.until("containing session switch is rejected", lambda:
                               b"containing session" in terminal.output[before:]
                               and "containing session" in log.read_text()[offset:])
                assert any(pane["id"] == nested["id"] for pane in terminal.terminals())
                assert terminal.action("list-panes", "--json", session=guest)
                terminal.send(b"\r")

            for key in (b"\x19", b"\x15"):
                reject_switch(key)
            new_guest = guest + "-renamed"
            owned_names.add(new_guest)
            terminal.action("rename-session", new_guest, session=guest)
            terminal.until("guest reannounces its committed rename", lambda:
                           f'guest session "{new_guest}" announced' in log.read_text())
            terminal.action("rename-session", guest)
            terminal.name = guest
            host = guest
            guest = new_guest
            terminal.drain(3.2)
            reject_switch(b"\x14")
            terminal.send(b"\x12")
            terminal.until("unrelated switch reconnects the nested viewer", lambda:
                           f'guest session "{unrelated}" announced' in log.read_text()
                           and bool(terminal.action("list-panes", "--json", session=unrelated)))
            assert terminal.action("list-panes", "--json", session=guest), "Switching lost the renamed guest"
            terminal.action("close-pane", "--pane-id", str(nested["id"]))
            terminal.until("nested viewer closes", lambda: len(terminal.terminals()) == 1)

            def client_ids():
                return {int(line.split()[0]) for line in
                        terminal.action("list-clients").splitlines()[1:] if line.strip()}

            original_clients = client_ids()
            assert len(original_clients) == 1, "Expected only the original host client"

            def recursive_command(exit_file):
                return ["/bin/sh", "-c",
                        'exit_file=$1; shift; "$@"; status=$?; '
                        'printf "%s\\n" "$status" > "$exit_file"; exit "$status"',
                        "recursive-attach", str(exit_file), *child, "attach", host]

            def require_rejection(exit_file):
                terminal.until("recursive client records its exit status", lambda:
                               exit_file.exists() and exit_file.stat().st_size > 0)
                assert int(exit_file.read_text()) == 1, "Recursive attachment did not exit with a rejection"
                terminal.until("recursive client is unregistered", lambda: client_ids() == original_clients)

            recursive_exit = temporary / "recursive-pane-exit"
            terminal.action("new-pane", "--floating", "--close-on-exit", "--",
                            *recursive_command(recursive_exit))
            require_rejection(recursive_exit)
            terminal.until("recursive attach pane closes", lambda:
                           [pane["id"] for pane in terminal.terminals()] == [outer["id"]])

            if not terminal.terminals()[0]["is_focused"]:
                terminal.action("focus-pane-id", str(outer["id"]))
            recursive_exit = temporary / "recursive-shell-exit"
            terminal.send((shlex.join(recursive_command(recursive_exit)) + "\r").encode())
            require_rejection(recursive_exit)
            terminal.until("surviving shell clears its rejected guest", lambda:
                           all(not pane.get("nested_session_name") for pane in terminal.terminals()))
            def rejection_visible():
                screen = terminal.action("dump-screen", "--pane-id", str(outer["id"]))
                # Both ancestry guards reject through the same cleanup; handshake timing selects the reason.
                return any(message in screen for message in (
                    "Cannot attach a containing session",
                    "The maximum nested session depth was reached.",
                ))

            terminal.until("surviving shell shows the rejection", rejection_visible)
            panes = terminal.terminals()
            assert [pane["id"] for pane in panes] == [outer["id"]]
            current = panes[0]
            assert (current["pane_content_rows"], current["pane_content_columns"]) == (
                outer["pane_content_rows"], outer["pane_content_columns"])
            if not current["is_focused"]:
                terminal.action("focus-pane-id", str(outer["id"]))
            before = len(terminal.output)
            terminal.send(b"printf '%s-%s-%s\\n' host still live\r")
            terminal.until("original host remains responsive", lambda: b"host-still-live" in terminal.output[before:])
        finally:
            cleanup_errors = []
            try:
                for name in owned_names:
                    try:
                        subprocess.run([binary, "kill-session", "--", name], env=env,
                                       capture_output=True, timeout=5)
                    except subprocess.TimeoutExpired as error:
                        cleanup_errors.append(error)
            finally:
                terminal.close()
            if cleanup_errors:
                raise cleanup_errors[0]
    print("Session cycles: switches, close-current, renames, and direct attachment preserve the host.")


if __name__ == "__main__":
    main()
