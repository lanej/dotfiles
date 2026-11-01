#!/usr/bin/env python3
"""Observe popup state, selected-client detach, and shutdown through installed keys."""

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
workflow = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))
Terminal = workflow["Terminal"]
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


def tab_is_dimmed(terminal, tab, offset):
    """Read the top bar's native nesting-focus rendition from actual PTY output."""
    output = bytes(terminal.output[offset:])
    # A long hostname or tab name can clip the displayed label. Identify the
    # same tab by its visible index and full name or ellipsis-terminated prefix.
    # Continue reading its actual SGR style; a ready popup alone is not proof
    # that the host handed over keyboard focus.
    marker = re.escape(f" {tab['position']}:".encode())
    title = -1
    for match in re.finditer(marker + rb"([^\x1b\r\n]*)", output):
        label = match[1].decode(errors="replace")
        prefix, ellipsis, _ = label.partition("…")
        if (label.startswith(tab["name"] + " ")
                or (prefix and ellipsis and tab["name"].startswith(prefix))):
            title = match.start()
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
    host_tab = next(tab for tab in terminal.tabs() if tab["active"])
    panes = {pane["id"] for pane in terminal.terminals()}
    rendered = len(terminal.output)
    log = Path(terminal.env["TMPDIR"]) / f"zellij-{os.getuid()}" / "zellij-log" / "zellij.log"
    offset = log.stat().st_size if log.exists() else 0
    terminal.prefix(b"P")
    # Even host-targeted CLI queries probe every session socket and can crash
    # a starting guest. First observe a fresh acknowledgement for this host,
    # emitted by the initialized guest screen after this open's log offset.
    def nested_ready():
        if not log.exists():
            return False
        with log.open("rb") as handle:
            handle.seek(offset)
            output = handle.read().decode(errors="replace")
        return ("nested session handshake complete: this session is nested inside ancestry "
                f'["{terminal.name}"]') in output
    terminal.until("popup registers its containing session", nested_ready)
    def guest_rendered():
        floating = [pane for pane in terminal.terminals()
                    if pane["id"] not in panes and pane["is_floating"]
                    and pane["tab_id"] == host_tab["tab_id"]]
        return len(floating) == 1 and "zellij-ready>" in terminal.action(
            "dump-screen", "--pane-id", f"terminal_{floating[0]['id']}")
    terminal.until("fresh host popup pane renders the guest shell", guest_rendered)
    terminal.until("popup client attaches to its ready shell", lambda:
                   bool(terminal.action("list-clients", session=POPUP).strip().splitlines()[1:])
                   and "zellij-ready>" in terminal.action("dump-screen", session=POPUP))
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


def detach_workflow(clients):
    first, unrelated = clients[:2]

    def attached_ids():
        return {client for tab in first.tabs() for client in tab["other_focused_clients"]}

    def exited(terminal):
        try:
            waited, status = os.waitpid(terminal.pid, os.WNOHANG)
        except ChildProcessError:
            return True
        if waited:
            assert os.waitstatus_to_exitcode(status) == 0
        return bool(waited)

    def until(description, predicate):
        def observed():
            for terminal in clients[1:]:
                terminal.drain(0.01)
            return predicate()
        return first.until(description, observed)

    original = attached_ids()
    assert len(original) == 1
    panes = {pane["id"] for pane in first.terminals()}

    def attach():
        terminal = Terminal(first.binary, first.env, first.name)
        clients.append(terminal)
        until("second attachment uses the live session", lambda:
              b"zellij-ready> " in terminal.output and len(attached_ids()) == 2)
        return terminal

    target = attach()
    target_id = (attached_ids() - original).pop()

    def choose(invoker=first):
        invoker.prefix(b"D")
        until("client chooser lists both real attachments", lambda:
              "Detach one client" in floating_screen(first)
              and f"Client {target_id}" in floating_screen(first))
        # The two rows are sorted by native ID; select the second attachment.
        invoker.send(b"\x1b[B")

    choose()
    first.send(b"\x1b")
    until("cancel closes only the chooser", lambda:
          not any(p["is_floating"] for p in first.terminals()))
    assert attached_ids() == original | {target_id}
    assert not exited(target) and not exited(unrelated)
    choose()
    first.send(b"\r")
    until("only the selected client detaches", lambda:
          exited(target) and attached_ids() == original
          and not any(p["is_floating"] for p in first.terminals()))
    assert not exited(first) and not exited(unrelated)
    assert {pane["id"] for pane in first.terminals()} == panes

    old_attachment = attach()
    assert attached_ids() == original | {target_id}
    choose()
    old_attachment.prefix(b"d")
    until("ordinary detach closes its own attachment", lambda:
          exited(old_attachment) and attached_ids() == original)
    replacement = attach()
    assert attached_ids() == original | {target_id}, "the reconnect must reuse the selected ID"
    first.send(b"\r")
    until("old chooser entry rejects the replacement attachment", lambda:
          "selected attachment changed" in floating_screen(first))
    assert not exited(replacement) and not exited(first) and not exited(unrelated)
    assert attached_ids() == original | {target_id}
    first.send(b"\r")
    until("stale selection closes without side effects", lambda:
          not any(p["is_floating"] for p in first.terminals()))
    choose(replacement)
    replacement.send(b"\r")
    until("self-selection detaches and its acknowledged helper exits", lambda:
          exited(replacement) and attached_ids() == original
          and not any(p["is_floating"] for p in first.terminals()))
    reattached = attach()
    assert {pane["id"] for pane in first.terminals()} == panes
    reattached.prefix(b"d")
    until("ordinary detach remains unchanged after rejection", lambda:
          exited(reattached) and attached_ids() == original)
    assert {pane["id"] for pane in first.terminals()} == panes
    assert unrelated.action("list-clients").strip().splitlines()[1:]
    print("Client detach: cancel preserves both attachments; selection closes exactly one; "
          "a stale entry cannot detach a completed reconnect reusing its ID; "
          "self-selection closes its helper and reattaches to the original panes; "
          "ordinary detach and another session survive.")


def popup_workflow(first, second, home):
    # Force the installed bar to clip a real tab label on every host, including
    # runners whose own long hostname leaves less room for the tab list.
    host_label = "host-controls-with-a-clipped-tab-title"
    first.prefix(b"r")
    first.send(b"popup-origin\r")
    first.until("distinct host tab label", lambda: first.tabs()[0]["name"] == "popup-origin")
    host_tab = first.tabs()[0]
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
                tab_is_dimmed(first, host_tab, rendered) is False)
    first.prefix(b"r")
    first.send(host_label.encode() + b"\r")
    first.until("nested escape returns control to the host", lambda: first.tabs()[0]["name"] == host_label)
    host_tab = first.tabs()[0]
    rendered = len(first.output)
    first.prefix(b"i")
    first.until("host tab shows returned guest focus", lambda:
                tab_is_dimmed(first, host_tab, rendered) is True)
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
            exit_code = os.waitstatus_to_exitcode(status)
            assert exit_code == 0, "\n".join([
                f"Confirmed shutdown client {replacement.name} exited with code {exit_code} "
                f"(wait status {status})",
                *replacement.startup_diagnostics(),
                "Replacement terminal output:\n" + replacement.output[-4000:].decode(errors="replace"),
            ])
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
    assert binary and shutil.which("fzf"), "Install Zellij >=0.45.1 and fzf before make test-zellij-sessions"
    with tempfile.TemporaryDirectory(prefix="zj-session-", dir="/tmp") as directory:
        temporary = Path(directory).resolve()
        home = temporary / "home"
        home.mkdir()
        runtime = temporary / "run"
        runtime.mkdir(mode=0o700)
        temp_files = temporary / "tmp"
        temp_files.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": "zellij-ready> ",
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(temporary / "cache"),
               "XDG_DATA_HOME": str(temporary / "data"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temp_files),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        workflow["preserve_rust_homes"](env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "FZF_DEFAULT_OPTS",
                    "FZF_DEFAULT_OPTS_FILE", "FZF_DEFAULT_COMMAND", "ENV", "BASH_ENV"):
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
                if len(clients) == 1:
                    terminal.grant_status_permissions()
                terminal.until("outer shell starts", lambda:
                               b"zellij-ready> " in terminal.output and len(terminal.terminals()) == 1)
            first, second = clients
            detach_workflow(clients)
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
