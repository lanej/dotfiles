#!/usr/bin/env python3
"""Exercise native attention and cross-session triage through the installed bar.

Local protocol emitters stand in for Claude/Codex; no model/account is used.
Requires Rust, Python with pyte 0.8.2, and the pinned Zellij runtime. State stays in private sessions.
"""

import codecs
import importlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

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

        def top_line(client):
            if client not in screens:
                screen = Display(120, 32)
                screens[client] = [screen, pyte.Stream(screen), codecs.getincrementaldecoder("utf-8")("replace"), 0]
            screen, stream, decoder, offset = screens[client]
            stream.feed(decoder.decode(bytes(client.output[offset:])))
            screens[client][3] = len(client.output)
            return screen.display[0]

        terminal = Terminal(binary, env, first)
        clients.append(terminal)
        try:
            terminal.grant_status_permissions()
            terminal.until("first shell is ready", lambda:
                           PROMPT in terminal.output and len(terminal.terminals()) == 1)
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
            other.prefix(b"\x01")
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
            print("PASS: installed native status tracks simultaneous programs, retains detached questions, and triages without restarting panes or a broker.")
        finally:
            for name in (first, second):
                subprocess.run([binary, "kill-session", name], env=env,
                               capture_output=True, timeout=5)
            for client in reversed(clients):
                client.close()


if __name__ == "__main__":
    main()
