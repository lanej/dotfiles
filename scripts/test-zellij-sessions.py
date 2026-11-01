#!/usr/bin/env python3
"""Observe persistent popup state and confirmed shutdown through installed keys."""

import os
from pathlib import Path
import re
import runpy
import shutil
import socket
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parent.parent
Terminal = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))["Terminal"]
POPUP = "dotfiles-popup"


def prove_popup_startup(binary, env, runtime):
    """A discovery connection must not kill a guest before its first client."""
    name = "starting-" + runtime.parent.name
    path = runtime / "contract_version_1" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    log = Path(env["TMPDIR"]) / f"zellij-{os.getuid()}" / "zellij-log" / "zellij.log"
    try:
        subprocess.run([binary, "--server", str(path)], env=env, check=True,
                       capture_output=True, text=True, timeout=5)
        deadline = time.monotonic() + 5
        while not path.exists():
            assert time.monotonic() < deadline, "uninitialized guest socket did not appear"
            time.sleep(0.01)
        with socket.socket(socket.AF_UNIX) as probe:
            probe.settimeout(5)
            probe.connect(str(path))
            probe.shutdown(socket.SHUT_WR)
            # EOF acknowledges that native removal released its connection;
            # keep the first real client absent throughout this controlled gap.
            while probe.recv(4096):
                pass
        result = subprocess.run([binary, "list-sessions", "--short", "--no-formatting"],
                                env=env, capture_output=True, text=True, timeout=5)
        assert result.returncode == 0 and name in result.stdout.splitlines(), "\n".join([
            "Guest server did not survive a connection closing before its first client",
            result.stdout, result.stderr,
            log.read_text()[-4000:] if log.exists() else "No native log",
        ])
    finally:
        # This name is scoped to the workflow's private socket directory.
        subprocess.run([binary, "kill-session", "--", name], env=env,
                       capture_output=True, timeout=5)
    print("Popup startup: a native server survives an acknowledged early IPC disconnect.")


def tab_is_dimmed(terminal, name, offset):
    """Read the native tab bar's latest focus rendition from actual PTY output."""
    output = bytes(terminal.output[offset:])
    title = output.rfind(name.encode())
    if title < 0:
        return None
    italic = None
    for match in re.finditer(rb"\x1b\[([0-9;]*)m", output[:title]):
        codes = [int(code or b"0") for code in match[1].split(b";")]
        index = 0
        while index < len(codes):
            code = codes[index]
            if code in (38, 48, 58) and index + 1 < len(codes):
                # RGB/indexed color components are not SGR style operations.
                index += 5 if codes[index + 1] == 2 else 3
                continue
            if code in (0, 23):
                italic = False
            elif code == 3:
                italic = True
            index += 1
    return italic


def floating_screen(terminal):
    pane = next((p for p in terminal.terminals() if p["is_floating"]), None)
    return terminal.action("dump-screen", "--pane-id", str(pane["id"])) if pane else ""


def open_popup(terminal):
    host_tab = next(tab["name"] for tab in terminal.tabs() if tab["active"])
    rendered = len(terminal.output)
    log = Path(terminal.env["TMPDIR"]) / f"zellij-{os.getuid()}" / "zellij-log" / "zellij.log"
    offset = log.stat().st_size if log.exists() else 0
    terminal.prefix(b"P")
    # Probing before the first render can disrupt main's client registration.
    # Observe this guest's prompt before opening any additional CLI connection.
    terminal.until("popup renders its ready shell", lambda:
                   f"{POPUP}:zellij-ready> ".encode() in terminal.output[rendered:])
    # Confirm the guest through the CLI, then its host's nesting-focus indication.
    terminal.until("popup client attaches to its ready shell", lambda:
                   bool(terminal.action("list-clients", session=POPUP).strip().splitlines()[1:])
                   and "zellij-ready>" in terminal.action("dump-screen", session=POPUP))
    # The shell can render before native nesting registration finishes. Wait
    # for its acknowledged host before sending keys intended for the guest.
    def nested_ready():
        if not log.exists():
            return False
        with log.open("rb") as handle:
            handle.seek(offset)
            output = handle.read().decode(errors="replace")
        return ("nested session handshake complete: this session is nested inside ancestry "
                f'["{terminal.name}"]') in output
    terminal.until("popup registers its containing session", nested_ready)
    terminal.until("host tab shows keyboard focus in the popup", lambda:
                   tab_is_dimmed(terminal, host_tab, rendered) is True)


def hide_popup(terminal):
    terminal.prefix(b"P")
    terminal.until("popup client closes while its shell stays alive", lambda:
                   not any(p["is_floating"] for p in terminal.terminals())
                   and not terminal.action("list-clients", session=POPUP).strip().splitlines()[1:])


def prove_popup(terminal, home, expected, filename):
    proof = home / filename
    terminal.send((f"printf '%s|%s|%s\\n' \"$popup_token\" \"$$\" \"$PWD\" > \"$HOME/{filename}\"\r").encode())
    terminal.until("same popup PID, shell memory and cwd", lambda:
                   proof.exists() and proof.read_text().strip() == expected)


def popup_workflow(first, second, home):
    first.prefix(b"r")
    first.send(b"popup-origin\r")
    first.until("distinct host tab label", lambda: first.tabs()[0]["name"] == "popup-origin")
    first.send(b"outer_token=untouched\r")
    open_popup(first)
    first.send(b"mkdir -p \"$HOME/scratch\"; cd \"$HOME/scratch\"; popup_token=live-memory; "
               b"printf '%s\\n' \"$$\" > \"$HOME/popup-pid\"\r")
    first.until("record scratch shell PID", lambda: (home / "popup-pid").exists())
    pid = (home / "popup-pid").read_text().strip()
    expected = f"live-memory|{pid}|{home / 'scratch'}"
    popup_ids = {p["id"] for p in first.panes(POPUP) if not p["is_plugin"]}
    assert len(popup_ids) == 1
    rendered = len(first.output)
    first.prefix(b"u")
    # FocusHostSession queues a frame; its completion is not the host's
    # completed handoff. Observe the fresh, non-italic host tab before keys.
    first.until("host tab regains keyboard focus", lambda:
                tab_is_dimmed(first, "popup-origin", rendered) is False)
    first.prefix(b"r")
    first.send(b"host-controls\r")
    first.until("nested escape returns control to the host", lambda: first.tabs()[0]["name"] == "host-controls")
    rendered = len(first.output)
    first.prefix(b"i")
    first.until("host tab shows returned guest focus", lambda:
                tab_is_dimmed(first, "host-controls", rendered) is True)
    prove_popup(first, home, expected, "popup-after-focus-return")
    hide_popup(first)

    first.prefix(b"c")
    first.until("second outer tab", lambda: len(first.tabs()) == 2)
    open_popup(first)
    prove_popup(first, home, expected, "popup-other-tab")
    hide_popup(first)
    open_popup(second)
    prove_popup(second, home, expected, "popup-other-session")
    assert {p["id"] for p in second.panes(POPUP) if not p["is_plugin"]} == popup_ids
    hide_popup(second)
    print("Popup: host/guest focus keys work; one original shell PID, unexported state and cwd "
          "survive hiding, another tab, and another outer session.")
    return expected


def shutdown_workflow(clients, names, home, popup_expected):
    first, second = clients[:2]
    def confirmation(terminal):
        terminal.prefix(b"\x11")
        terminal.until("shutdown displays its explicit target", lambda:
                       "Type SHUTDOWN" in floating_screen(terminal)
                       and terminal.name in "".join(floating_screen(terminal).split()))
        return next(p for p in terminal.terminals() if p["is_floating"])

    original = {p["id"] for p in second.terminals()}
    confirmation(second)
    second.send(b"\r")
    second.until("cancel keeps original session attached", lambda:
                 {p["id"] for p in second.terminals()} == original
                 and bool(second.action("list-clients").strip().splitlines()[1:]))
    stale_pane = confirmation(second)
    original_name = second.name
    renamed = original_name + "-renamed"
    names.append(renamed)
    second.action("rename-session", renamed)
    second.name = renamed
    replacement = Terminal(first.binary, first.env, original_name)
    clients.append(replacement)
    replacement.until("replacement session starts", lambda: b"zellij-ready> " in replacement.output)
    # Recreate the same visible workspace and command IDs. The old tuple-only
    # guard matched this new server and killed it after a stale confirmation.
    open_popup(replacement)
    hide_popup(replacement)
    confirmation(replacement)
    replacement.send(b"\r")
    replacement.until("replacement cancellation completes", lambda:
                      not any(p["is_floating"] for p in replacement.terminals()))
    new_pane = confirmation(replacement)
    weak_identity = ("id", "tab_id", "terminal_command", "pane_cwd")
    assert [stale_pane.get(k) for k in weak_identity] == [new_pane.get(k) for k in weak_identity]
    second.send(b"SHUTDOWN\r")
    second.until("renamed/replaced target rejects stale confirmation", lambda:
                 "renamed or replaced" in floating_screen(second))
    assert replacement.action("list-clients").strip().splitlines()[1:]
    assert second.action("list-clients").strip().splitlines()[1:]
    second.send(b"\r")
    second.until("stale confirmation closes", lambda:
                 not any(p["is_floating"] for p in second.terminals()))
    replacement.send(b"SHUTDOWN\r")
    def target_stopped():
        replacement.drain()
        waited, status = os.waitpid(replacement.pid, os.WNOHANG)
        if waited:
            assert os.waitstatus_to_exitcode(status) == 0
        return bool(waited)
    first.until("only the confirmed session stops", target_stopped)
    sessions = subprocess.run([first.binary, "list-sessions", "--no-formatting"], env=first.env,
                              capture_output=True, text=True, check=True).stdout.splitlines()
    assert any(line.startswith(first.name + " [Created ") for line in sessions)
    assert not any(line.startswith(original_name + " [Created ") and "EXITED" not in line
                   for line in sessions)
    assert second.action("list-clients").strip().splitlines()[1:]
    assert first.action("list-clients").strip().splitlines()[1:]
    first.action("go-to-tab", "1")
    first.send(b"printf '%s\\n' \"$outer_token\" > \"$HOME/outer-proof\"\r")
    first.until("other session retains its shell state", lambda:
                (home / "outer-proof").exists() and (home / "outer-proof").read_text().strip() == "untouched")
    open_popup(first)
    prove_popup(first, home, popup_expected, "popup-after-shutdown")
    hide_popup(first)
    print("Shutdown: cancellation and stale rename/recreate confirmation preserve clients; "
          "valid confirmation ends only its original target while other sessions and the popup survive.")


def main():
    binary = shutil.which("zellij")
    assert binary, "Install Zellij >=0.45.1 before make test-zellij-sessions"
    with tempfile.TemporaryDirectory(prefix="zj-session-", dir="/tmp") as directory:
        temporary = Path(directory).resolve()
        home = temporary / "home"
        home.mkdir()
        runtime = temporary / "run"
        runtime.mkdir(mode=0o700)
        temp_files = temporary / "tmp"
        temp_files.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh",
               "PS1": "${ZELLIJ_SESSION_NAME}:zellij-ready> ",
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(temporary / "cache"),
               "XDG_DATA_HOME": str(temporary / "data"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temp_files),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij"], cwd=ROOT, env=env,
                       check=True, capture_output=True, text=True)
        subprocess.run([binary, "setup", "--check"], env=env, check=True,
                       capture_output=True, text=True)
        names = ["first-" + temporary.name, "second-" + temporary.name]
        clients = []
        try:
            prove_popup_startup(binary, env, runtime)
            for name in names:
                terminal = Terminal(binary, env, name)
                clients.append(terminal)
                terminal.until("outer shell starts", lambda:
                               b"zellij-ready> " in terminal.output and len(terminal.terminals()) == 1)
            first, second = clients
            expected = popup_workflow(first, second, home)
            shutdown_workflow(clients, names, home, expected)
        finally:
            # All names live only in this test's private socket directory.
            for name in [*names, POPUP]:
                subprocess.run([binary, "kill-session", "--", name], env=env,
                               capture_output=True, timeout=5)
            for client in clients:
                client.close()


if __name__ == "__main__":
    main()
