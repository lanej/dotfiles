#!/usr/bin/env python3
"""Exercise prefix waiting, native attention and triage through the installed bar.

Local protocol emitters stand in for Claude/Codex; no model/account is used.
Requires Rust, Python with pyte 0.8.2, and the pinned Zellij runtime. State stays in private sessions.
"""

import codecs
import fcntl
import importlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import struct
import tempfile
import termios

import pyte

workflow = importlib.import_module("test-zellij")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


class Display(pyte.Screen):
    def report_device_status(self, mode, **kwargs):
        # Zellij asks the real PTY for private terminal status. This decoder
        # observes rendered cells; Terminal handles the interactive endpoint.
        if not kwargs.get("private"):
            super().report_device_status(mode)


EMITTER = r'''
import os
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(str(os.getpid()))
def status(value):
    print("\x1b]7501;state=" + value + ":app=fixture\x07", end="", flush=True)
status("working")
print("native-agent-ready", flush=True)
for line in sys.stdin:
    value = line.strip()
    if value == "exit":
        status("clear")
        break
    status(value)
    print("native-state:" + value, flush=True)
'''


def main():
    for name in ("zellij", "cargo", "python3"):
        assert shutil.which(name), f"Install {name} before testing native attention"
    with tempfile.TemporaryDirectory(prefix="zj-status-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / "home", work / "run", work / "tmp"
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temporary),
               "ZELLIJ_PEER_SCAN_INTERVAL_MS": "50",
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        workflow.preserve_rust_homes(env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij-status", "zellij"], cwd=ROOT,
                       env=env, check=True, capture_output=True, text=True)
        program = work / "agent.py"
        program.write_text(EMITTER)
        binary = shutil.which("zellij")
        first, second = "status-first-" + work.name, "status-second-" + work.name
        clients = []
        screens = {}

        def display(client):
            if client not in screens:
                screen = Display(120, 32)
                screens[client] = [screen, pyte.Stream(screen), codecs.getincrementaldecoder("utf-8")("replace"), 0]
            screen, stream, decoder, offset = screens[client]
            stream.feed(decoder.decode(bytes(client.output[offset:])))
            screens[client][3] = len(client.output)
            return screen

        def top_line(client):
            return display(client).display[0]

        def resize(client, cols):
            display(client).resize(lines=32, columns=cols)
            fcntl.ioctl(client.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 32, cols, 0, 0))

        def prefix_banner(client):
            screen = display(client)
            return "PREFIX" in screen.display[0] and all(
                screen.buffer[0][col].bg == "b48ead"
                and screen.buffer[0][col].fg == "2e3440"
                and screen.buffer[0][col].bold
                for col in range(screen.columns))

        terminal = Terminal(binary, env, first)
        clients.append(terminal)
        try:
            terminal.grant_status_permissions()
            terminal.until("first shell is ready", lambda:
                           PROMPT in terminal.output and len(terminal.terminals()) == 1)
            terminal.until("normal status bar is ready", lambda: "!0 ●0" in top_line(terminal))
            terminal.send(b"\x06")
            terminal.until("prefix waiting paints the whole bar with bold high-contrast text", lambda:
                           prefix_banner(terminal) and "waiting for next key" in top_line(terminal)
                           and "Esc cancels" in top_line(terminal))
            # The prefix wins over the clock even when the terminal is narrow.
            resize(terminal, 28)
            terminal.until("prefix remains visible after narrowing the terminal", lambda:
                           prefix_banner(terminal) and top_line(terminal).endswith("…"))
            terminal.send(b"\x1b")
            terminal.until("Escape restores the normal bar", lambda:
                           "PREFIX" not in top_line(terminal)
                           and display(terminal).buffer[0][0].bg == "2e3440"
                           and not display(terminal).buffer[0][0].bold)
            resize(terminal, 120)
            terminal.send(b"\x06")
            terminal.until("prefix waiting can be entered again", lambda: prefix_banner(terminal))
            terminal.send(b"\x12")
            terminal.until("a command consumes the prefix and labels the resulting mode", lambda:
                           "RESIZE" in top_line(terminal) and "PREFIX" not in top_line(terminal)
                           and display(terminal).buffer[0][0].bg == "2e3440")
            terminal.send(b"\r")
            terminal.until("leaving resize restores the ordinary bar", lambda:
                           "RESIZE" not in top_line(terminal) and "!0 ●0" in top_line(terminal))
            first_pane = terminal.terminals()[0]["id"]
            first_pid = home / "first-agent-pid"
            terminal.send((shlex.join(["python3", str(program), str(first_pid)]) + "\r").encode())

            def pane(session, pane_id):
                return next(p for p in terminal.panes(session=session)
                            if not p["is_plugin"] and p["id"] == pane_id)

            def state(session, pane_id, expected):
                return any(record.get("state") == expected
                           for record in pane(session, pane_id).get("program_status", []))

            terminal.until("first native program is working", lambda:
                           first_pid.exists() and state(first, first_pane, "Working"))
            original_pid = first_pid.read_text()
            other = Terminal(binary, env, second)
            clients.append(other)
            other.until("second shell is ready", lambda:
                        PROMPT in other.output and len(other.terminals()) == 1)
            second_pane = other.terminals()[0]["id"]
            other.send((shlex.join(["python3", str(program), str(home / "second-agent-pid")]) + "\r").encode())
            other.until("second native program is working", lambda:
                        state(second, second_pane, "Working"))

            # The native runtime keeps tracking state after every status-bar
            # instance in the first session has lost its attached client.
            terminal.prefix(b"d")
            other.until("first session is detached", lambda:
                        not other.action("list-clients", session=first).strip().splitlines()[1:])
            other.action("paste", "--pane-id", f"terminal_{first_pane}",
                         "blocked:kind=question\n", session=first)
            other.until("detached program reports a question", lambda:
                        state(first, first_pane, "Blocked") and
                        pane(first, first_pane)["attention"]["detail"]["kind"] == "Question")
            other.until("visible bar counts a detached question and the working program", lambda:
                        "!1 ●1" in top_line(other))
            # The familiar key stays local. Native global triage remains an
            # explicit action rather than changing tmux's selection policy.
            other.prefix(b"\x01")
            other.until("attention key completes without leaving the current session", lambda:
                        "PREFIX" not in top_line(other)
                        and bool(other.action("list-clients", session=second).strip().splitlines()[1:]))
            other.action("go-to-next-attention")
            other.until("native triage enters the detached session", lambda:
                        any(f"terminal_{first_pane}" in row for row in
                            other.action("list-clients", session=first).splitlines()[1:]))
            assert first_pid.read_text() == original_pid, "Triage restarted the program"
            assert state(second, second_pane, "Working"), "Triage changed the other program"
            other.name = first
            try:
                other.until("native question glyph renders after reattachment", lambda:
                            "?" in top_line(other) and "!?" not in top_line(other))
            except AssertionError as error:
                details = f"Decoded top row: {top_line(other)!r}"
                try:
                    details += f"\nNative pane: {pane(first, first_pane)!r}"
                except Exception as diagnostic_error:
                    details += f"\nCould not inspect native pane: {diagnostic_error}"
                raise AssertionError(f"{error}\n{details}") from error
            other.send(b"exit\r")
            other.until("program exit clears its native status", lambda:
                        not pane(first, first_pane).get("program_status"))
            # A realistic local triage round: two requests beat work, cycle
            # numerically and wrap. Once answered, quiet completions are skipped.
            origin = next(tab for tab in other.tabs() if tab["active"])["tab_id"]

            def focused_tab():
                return next(tab["tab_id"] for tab in other.tabs() if tab["active"])

            def agent_tab(name):
                previous = {pane["id"] for pane in other.terminals()}
                other.prefix(b"c")
                pane_id = other.until("new triage tab has a terminal", lambda:
                    next((pane["id"] for pane in other.terminals() if pane["id"] not in previous), None))
                pid_file = home / (name + "-pid")
                other.send((shlex.join(["python3", str(program), str(pid_file)]) + "\r").encode())
                other.until("triage agent is working", lambda:
                            pid_file.exists() and state(first, pane_id, "Working"))
                return focused_tab(), pane_id

            busy_tab, busy_pane = agent_tab("busy")
            done_tab, done_pane = agent_tab("done")
            other.send(b"done\r")
            other.until("completed work is quiet", lambda: state(first, done_pane, "Done"))
            question_tab, question_pane = agent_tab("question")
            other.send(b"blocked:kind=question\r")
            other.until("question needs an answer", lambda: state(first, question_pane, "Blocked"))
            approval_tab, approval_pane = agent_tab("approval")
            other.send(b"blocked:kind=permission\r")
            other.until("approval needs an answer", lambda: state(first, approval_pane, "Blocked"))
            other.until("both requests reach the attention bar", lambda:
                        "●2" in top_line(other) and "?" in top_line(other))
            other.prefix(b"0")
            other.until("triage starts on the original tab", lambda: focused_tab() == origin)
            other.prefix(b"\x01")
            other.until("question wins over earlier activity and completed work", lambda:
                        focused_tab() == question_tab)
            other.prefix(b"\x01")
            other.until("next request follows tab order", lambda: focused_tab() == approval_tab)
            other.prefix(b"\x01")
            other.until("requests wrap without revisiting the current tab", lambda: focused_tab() == question_tab)
            other.send(b"working\r")
            other.action("paste", "--pane-id", f"terminal_{approval_pane}", "working\n")
            other.until("answered requests resume work in the global stream", lambda:
                        "●4" in top_line(other))
            other.send(b"done\r")
            other.action("paste", "--pane-id", f"terminal_{approval_pane}", "done\n")
            other.until("both requests have completed", lambda:
                        state(first, question_pane, "Done") and state(first, approval_pane, "Done")
                        and "●2" in top_line(other))
            other.prefix(b"\x01")
            other.until("activity is selected after requests clear", lambda: focused_tab() == busy_tab)
            assert state(second, second_pane, "Working"), "Local triage modified another session"
            viewer = Terminal(binary, env, first)
            clients.append(viewer)
            viewer.until("second attachment is usable", lambda:
                         "!?" not in top_line(viewer) and "●" in top_line(viewer))
            viewer.prefix(b"0")

            def client_panes():
                viewer.drain()
                return {row.split()[1] for row in other.action("list-clients").splitlines()[1:]
                        if len(row.split()) > 1}

            other.until("clients have separate focused tabs", lambda:
                        client_panes() == {f"terminal_{first_pane}", f"terminal_{busy_pane}"})
            other.action("paste", "--pane-id", f"terminal_{question_pane}", "working\n")
            other.until("new work reaches the global stream", lambda: "●3" in top_line(other))
            other.action("paste", "--pane-id", f"terminal_{question_pane}", "blocked:kind=question\n")
            other.until("new request reaches the global stream", lambda:
                        state(first, question_pane, "Blocked") and "●2" in top_line(other))
            other.prefix(b"\x01")
            other.until("only the invoking client's tab changes", lambda:
                        client_panes() == {f"terminal_{first_pane}", f"terminal_{question_pane}"})
            print("PASS: installed status preserves prefix display and detached native state; local attention cycles requests before activity, skips quiet completions, and keeps other clients in place.")
        finally:
            for name in (first, second):
                subprocess.run([binary, "kill-session", name], env=env,
                               capture_output=True, timeout=5)
            for client in reversed(clients):
                client.close()


if __name__ == "__main__":
    main()
