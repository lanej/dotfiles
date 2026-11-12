#!/usr/bin/env python3
"""Exercise installed cd/Ctrl-B tab titles in an isolated native Zellij session."""

import importlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import tempfile


workflow = importlib.import_module("test-zellij")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT



def wait_for_exit(pids, timeout=5):
    """Wait for owned writers to stop; zombies can no longer touch the fixture."""
    pending = set(pids)
    deadline = time.monotonic() + timeout
    while pending:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"Session processes still running before fixture cleanup: {sorted(pending)}")
        try:
            result = subprocess.run(["ps", "-o", "pid=,stat=", "-p", ",".join(map(str, sorted(pending)))],
                                    capture_output=True, text=True, timeout=min(1, remaining))
        except subprocess.TimeoutExpired as error:
            raise TimeoutError(f"Could not confirm shutdown of session processes: {sorted(pending)}") from error
        if result.returncode not in (0, 1) or (result.returncode == 1 and result.stderr.strip()):
            raise RuntimeError(f"Could not verify session shutdown: {result.stderr}")
        rows = [line.split() for line in result.stdout.splitlines() if line.strip()]
        pending = {int(pid) for pid, state in rows if not state.startswith("Z")}
        if pending:
            time.sleep(min(0.05, max(0, deadline - time.monotonic())))


def stop_session(terminal):
    """Stop only this fixture's named session and wait for its process tree."""
    try:
        result = subprocess.run(["ps", "-axo", "pid=,ppid=,command="],
                                capture_output=True, text=True, check=True, timeout=5)
        rows = [line.split(None, 2) for line in result.stdout.splitlines()]
        rows = [row for row in rows if len(row) == 3]
        socket_prefix = " --server " + terminal.env["ZELLIJ_SOCKET_DIR"] + "/"
        owned = {terminal.pid} | {int(pid) for pid, _, command in rows if socket_prefix in command}
        while True:
            children = {int(pid) for pid, parent, _ in rows if int(parent) in owned}
            if children <= owned:
                break
            owned |= children
    finally:
        try:
            subprocess.run([terminal.binary, "kill-session", "--", terminal.name], env=terminal.env,
                           capture_output=True, timeout=5)
        finally:
            terminal.close()
    # rationale: kill-session replies before pane shells finish their exit-time history writes.
    wait_for_exit(owned)


def main():
    binary, shell = shutil.which("zellij"), shutil.which("zsh")
    assert binary and shell, "Install Zellij and Zsh before testing shell tab titles"
    directory = tempfile.mkdtemp(prefix="zj-shell-titles-", dir="/tmp")
    completed = stopped = False
    try:
        work = Path(directory).resolve()
        home, runtime, selection = work / "home", work / "run", work / "project" / "child"
        home.mkdir()
        runtime.mkdir(mode=0o700)
        selection.mkdir(parents=True)
        subprocess.run(["git", "init", "-b", "main", str(selection.parent)],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(selection.parent), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "fixture"],
                       capture_output=True, check=True)
        env = {**os.environ, "HOME": str(home), "SHELL": shell,
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_CACHE_HOME": str(work / "cache"),
               "XDG_DATA_HOME": str(work / "data"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(work),
               "SSH_CONNECTION": "isolated-title-test", "TITLE_SELECTION": str(selection),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV", "ZDOTDIR"):
            env.pop(key, None)
        # Isolate host-wide startup (including compinit) while retaining the
        # installed user configuration in every shell, including new splits.
        zdot = work / "zdot"
        zdot.mkdir()
        (zdot / ".zshenv").write_text('unsetopt GLOBAL_RCS\nsource "$HOME/.zshenv"\n')
        (zdot / ".zshrc").write_text('source "$HOME/.zshrc"\n')
        env["ZDOTDIR"] = str(zdot)
        (home / ".files").symlink_to(ROOT)
        subprocess.run(["make", "--no-print-directory", "zsh-config", "zellij"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        # Simulate an existing shell installation being upgraded via make zellij.
        (home / ".local/share/zsh/zellij-auto-title.zsh").unlink()
        subprocess.run(["make", "--no-print-directory", "zellij"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        shell_config = home / ".zshrc"
        configured = shell_config.read_text()
        shell_config.unlink()
        shell_config.write_text(configured + "\nPS1=" + shlex.quote(PROMPT.decode()) + "\n"
                                "_z() { printf '1 %s\\n' \"$TITLE_SELECTION\"; }\n"
                                '_title_test_prompt_done() {\n'
                                '  print -r -- "$PWD" >| "$HOME/prompt-$ZELLIJ_PANE_ID"\n'
                                '  [[ -z "$TITLE_PROOF" ]] || touch "$TITLE_PROOF"\n'
                                '}\nadd-zsh-hook precmd _title_test_prompt_done\n'
                                '_title_test_buffer() { print -r -- "$BUFFER" >| "$HOME/buffer"; }\n'
                                'zle -N _title_test_buffer\nbindkey \'^X^T\' _title_test_buffer\n')
        # Directory history and picker selection are simulated. The installed key binding, zz,
        # shell cd hooks and native tab names are exercised end to end.
        tools = home / ".local/bin"
        fzf = tools / "fzf"
        fzf.write_text('''#!/bin/sh
if [ "$*" = --zsh ]; then
    printf '%s\n' 'fzf-completion() { :; }' 'zle -N fzf-completion' '__fzf_defaults() { print -r -- "$*"; }'
else
    [ -z "$TITLE_CANCEL" ] || { touch "$HOME/cancel-seen"; exit 130; }
    python3 -c 'import sys; rows=sys.stdin.buffer.read(); sys.stdout.buffer.write(b"enter\\0" + rows)'
fi
''')
        fzf.chmod(0o755)
        fd = tools / "fd"
        fd.write_text("#!/bin/sh\nexit 0\n")
        fd.chmod(0o755)
        config = work / "config.kdl"
        config.write_text('default_mode "locked"\nshow_startup_tips false\n'
                          'show_release_notes false\nsession_serialization false\n')
        layout = work / "layout.kdl"
        layout.write_text("layout { pane; }\n")
        name = "shell-" + work.name
        terminal = Terminal(binary, env, name, [
            binary, "--config", str(config), "--new-session-with-layout", str(layout),
            "--session", name,
        ], install_navigation=False)
        try:
            terminal.until("the installed shell names its initial tab", lambda:
                           PROMPT in terminal.output and terminal.tabs()[0]["name"] == "home")
            tab_id = terminal.tabs()[0]["tab_id"]

            forbidden = home / "prompt-subprocesses"
            for executable in ("ps", "zellij"):
                stub = tools / executable
                stub.write_text(f"#!/bin/sh\nprintf '%s\\n' {executable} >> {shlex.quote(str(forbidden))}\nexit 99\n")
                stub.chmod(0o755)
            timings = home / "title-timings"
            terminal.send(("zmodload zsh/datetime; repeat 15 { started=$EPOCHREALTIME; "
                           "_zellij_auto_tab_title; print $(( (EPOCHREALTIME-started)*1000 )) >> "
                           + shlex.quote(str(timings)) + "; }\r").encode())
            terminal.until("prompt title measurements finish", lambda:
                           timings.exists() and len(timings.read_text().splitlines()) == 15)
            samples = sorted(float(line) for line in timings.read_text().splitlines())
            print(f"Prompt title hook: median {samples[7]:.2f} ms, max {samples[-1]:.2f} ms (15 warm runs)")
            assert not forbidden.exists(), "Prompt titles launched ps or the Zellij CLI"
            for executable in ("ps", "zellij"):
                (tools / executable).unlink()

            def title():
                return next(tab["name"] for tab in terminal.tabs() if tab["tab_id"] == tab_id)

            def prompt_in(pane, directory):
                marker = home / f"prompt-{pane}"
                return marker.exists() and marker.read_text().rstrip("\n") == str(directory)

            terminal.send(("cd " + shlex.quote(str(selection.parent)) + "\r").encode())
            terminal.until("cd adds the directory and branch", lambda: terminal.terminals()[0]["title"] == "project  main" and title() == "home")
            terminal.send(b"git switch -c topic\r")
            terminal.until("the prompt notices branch changes", lambda: terminal.terminals()[0]["title"] == "project  topic" and title() == "home")
            original = terminal.terminals()[0]["id"]
            terminal.send(b"\x02")
            terminal.until("Ctrl-B updates the pane after selecting a directory", lambda:
                           prompt_in(original, selection) and terminal.terminals()[0]["title"] == "child  topic"
                           and title() == "home")
            marker = home / "must-not-run"
            buffer = home / "buffer"
            pending = 'touch "$HOME/must-not-run"'
            proof = home / "buffer-prompt"
            terminal.send(("TITLE_PROOF=" + shlex.quote(str(proof)) + "\r").encode())
            terminal.until("buffer fixture reaches the prompt", proof.exists)
            proof.unlink()
            terminal.send(pending.encode() + b"\x02")
            terminal.until("Ctrl-B refreshes the prompt", proof.exists)
            terminal.send(b"\x18\x14")
            terminal.until("Ctrl-B retains unfinished input", lambda: buffer.exists() and buffer.read_text().strip() == pending)
            assert not marker.exists(), "Ctrl-B executed unfinished input"
            proof.unlink()
            terminal.send(b"\x01\x0bexport TITLE_CANCEL=1\r")
            terminal.until("cancellation fixture reaches the prompt", proof.exists)
            buffer.unlink()
            terminal.send(pending.encode() + b"\x02")
            terminal.until("picker cancellation completes", (home / "cancel-seen").exists)
            terminal.send(b"\x18\x14")
            terminal.until("cancel retains unfinished input", lambda: buffer.exists() and buffer.read_text().strip() == pending)
            assert not marker.exists(), "Cancellation executed unfinished input"
            proof.unlink()
            terminal.send(b"\x01\x0bunset TITLE_CANCEL\r")
            terminal.until("cancellation fixture is cleared", proof.exists)
            # Arm the command at the original prompt. Its cd runs only after the
            # new split has focus, independently of ZLE startup and resize timing.
            terminal.send(b'touch "$HOME/waiting"; read -r go; cd "$TITLE_SELECTION/.."; '
                          b'TITLE_PROOF="$HOME/inactive-done"\r')
            terminal.until("the original shell is waiting", (home / "waiting").exists)
            terminal.action("new-pane", "--direction", "right", "--cwd", str(home), "--", shell)
            terminal.until("a new active shell keeps the shared automatic title", lambda:
                           any(p["id"] != original and p["is_focused"] and prompt_in(p["id"], home)
                               for p in terminal.terminals()) and title() == "home")
            proof = home / "inactive-done"
            terminal.action("write", "--pane-id", f"terminal_{original}", "13")
            terminal.until("the inactive shell finishes its directory change", proof.exists)
            assert prompt_in(original, selection.parent)
            assert title() == "home", "An inactive split stole the tab title"
            terminal.action("rename-tab", "--tab-id", str(tab_id), "Review")
            terminal.send(("cd " + shlex.quote(str(selection)) + "; TITLE_PROOF=" + shlex.quote(str(home / "manual-done")) + "\r").encode())
            terminal.until("the explicitly named tab's shell finishes cd", (home / "manual-done").exists)
            assert title() == "Review", "An automatic title replaced the explicit name"
            completed = True
            print("PASS: installed cd/Ctrl-B hooks update pane directory and branch; "
                  "unfinished input survives selection and cancel; tabs retain ownership and preserve explicit names.")
        finally:
            original = sys.exception()
            try:
                stop_session(terminal)
                stopped = True
            except Exception as error:
                if original is None:
                    raise
                original.add_note(f"Session teardown also failed: {error}")
    finally:
        if completed and stopped:
            shutil.rmtree(directory)
        else:
            print(f"Retained failed shell-title fixture: {directory}", file=sys.stderr)


if __name__ == "__main__":
    main()
