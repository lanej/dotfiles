#!/usr/bin/env python3
"""Exercise zero-based tab labels and directory titles through the installed UI."""

import base64
import codecs
import errno
import fcntl
import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time

import pyte

workflow = importlib.import_module("test-zellij")
Display = importlib.import_module("test-zellij-status").Display
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT



# Instrument only this test process; keep the installed chooser and its deadline
# unchanged. Function globals are the namespace actually used by runpy functions.
CLIENT_SNAPSHOT_PROBE = r"""
import json, runpy, sys, time
chooser = runpy.run_path(sys.argv[1])["client_choices"]
namespace = chooser.__globals__
started = time.monotonic()

def emit(event, **details):
    print(json.dumps({"event": event, "elapsed": time.monotonic() - started,
                      **details}, default=str), file=sys.stderr, flush=True)

def instrument(name):
    original = namespace[name]
    def traced(*args, **kwargs):
        emit(name + ":start", args=args, timeout=kwargs.get("timeout"))
        try:
            result = original(*args, **kwargs)
        except Exception as error:
            emit(name + ":error", error=repr(error),
                 stdout=getattr(error, "stdout", None),
                 stderr=getattr(error, "stderr", None))
            raise
        if name == "status_pipe":
            emit(name + ":result", raw_rows=result)
            try:
                rows = [json.loads(line) for line in result.splitlines() if line.strip()]
                emit("returned-client-ids", ids=[row.get("token", {}).get("client_id")
                                                 for row in rows])
            except (ValueError, AttributeError) as error:
                emit("returned-client-ids:error", error=repr(error))
        else:
            emit(name + ":result", native_state=result,
                 expected_client_ids=sorted({str(client) for tab in result
                                             for client in tab["other_focused_clients"]}))
        return result
    namespace[name] = traced

instrument("status_pipe")
instrument("snapshot")
print(json.dumps(chooser(sys.argv[2])))
"""


def capture_failure(terminal, other, error):
    """Preserve evidence before teardown without retrying the chooser."""
    print(f"Tab-label failure: {error!r}", file=sys.stderr, flush=True)
    for field in ("stdout", "stderr"):
        value = getattr(error, field, None)
        if value:
            print(f"Failing subprocess {field}: {value!r}", file=sys.stderr, flush=True)
    for client in (terminal, other):
        if client is None:
            continue
        try:
            print("\n".join(client.startup_diagnostics()), file=sys.stderr, flush=True)
        except Exception as diagnostic_error:
            print(f"Client {client.pid} diagnostics failed: {diagnostic_error!r}",
                  file=sys.stderr, flush=True)
    try:
        artifact_root = os.environ.get("ZELLIJ_TEST_ARTIFACTS")
        destination = None
        if artifact_root:
            Path(artifact_root).mkdir(parents=True, exist_ok=True)
            destination = Path(tempfile.mkdtemp(prefix="labels-state-", dir=artifact_root))
        for index, cache in enumerate((Path(terminal.env["XDG_CACHE_HOME"]) / "zellij",
                                      Path(terminal.env["HOME"]) / "Library/Caches/zellij")):
            permissions = cache / "permissions.kdl"
            if permissions.exists():
                data = permissions.read_bytes()
                print(f"Permission cache {permissions}: {data!r}", file=sys.stderr, flush=True)
                if destination:
                    (destination / f"permissions-{index}.kdl").write_bytes(data)
        for kind in ("tabs", "panes"):
            try:
                result = subprocess.run([terminal.binary, "--session=" + terminal.name,
                                         "action", "list-" + kind, "--json"],
                                        env=terminal.env, capture_output=True, text=True, timeout=5)
                evidence = {"returncode": result.returncode, "stdout": result.stdout,
                            "stderr": result.stderr}
            except Exception as diagnostic_error:
                evidence = {"error": repr(diagnostic_error),
                            "stdout": str(getattr(diagnostic_error, "stdout", None)),
                            "stderr": str(getattr(diagnostic_error, "stderr", None))}
            text = json.dumps(evidence, indent=2)
            print(f"Native {kind}: {text}", file=sys.stderr, flush=True)
            if destination:
                (destination / f"{kind}.json").write_text(text + "\n")
    except Exception as diagnostic_error:
        print(f"Failure state capture failed: {diagnostic_error!r}", file=sys.stderr, flush=True)


def main():
    for name in ("zellij", "cargo", "fzf", "zsh", "git"):
        assert shutil.which(name), f"Install {name} before testing tab labels"
    scratch = tempfile.TemporaryDirectory(prefix="zj-labels-", dir="/tmp")
    with scratch as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / "home", work / "run", work / "tmp"
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temporary),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        workflow.preserve_rust_homes(env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV",
                    "FZF_DEFAULT_OPTS", "FZF_DEFAULT_OPTS_FILE", "FZF_DEFAULT_COMMAND"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij-status", "zellij"], cwd=ROOT,
                       env=env, check=True, capture_output=True, text=True)
        project = home / "project"
        project.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "topic", str(project)], check=True)
        subprocess.run(["git", "-C", str(project), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm", "Initial",
                        "--allow-empty"], check=True)
        binary = shutil.which("zellij")
        name = "labels-" + work.name
        terminal = Terminal(binary, env, name)
        other = None
        screen, decoder = Display(480, 32), codecs.getincrementaldecoder("utf-8")("replace")
        stream, offset = pyte.Stream(screen), 0

        def top_line():
            nonlocal offset
            stream.feed(decoder.decode(bytes(terminal.output[offset:])))
            offset = len(terminal.output)
            return screen.display[0]

        def active():
            return next(tab for tab in terminal.tabs() if tab["active"])

        def picker_screen():
            pane = next((pane for pane in terminal.terminals() if pane["is_floating"]), None)
            return terminal.action("dump-screen", "--pane-id", f"terminal_{pane['id']}") if pane else ""

        try:
            terminal.grant_status_permissions()
            terminal.until("first tab starts at zero", lambda:
                           PROMPT in terminal.output and "0:Tab #0" in top_line())
            # Resize after startup (Terminal sets its initial PTY size in the
            # child), keeping all eleven full labels visible for this workflow.
            fcntl.ioctl(terminal.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 32, 480, 0, 0))
            # One session crosses the direct-key boundary, rather than separate
            # cases that repeat the same labeling workflow.
            for count in range(2, 12):
                terminal.prefix(b"c")
                terminal.until("create tabs through the eleventh", lambda:
                               len(terminal.tabs()) == count)
            eleventh = active()["tab_id"]
            terminal.until("eleventh tab displays position ten", lambda: "10:Tab #10" in top_line())
            terminal.prefix(b"0")
            terminal.until("zero key selects first tab", lambda: active()["position"] == 0)
            terminal.prefix(b"9")
            terminal.until("nine key selects tenth tab", lambda: active()["position"] == 9)
            terminal.prefix(b"\x06")
            terminal.until("tab picker opens", lambda: "Tabs (attention" in picker_screen())
            terminal.send(b"10:")
            terminal.until("picker exposes tab ten", lambda:
                           "1/11" in picker_screen() and "10: Tab #10" in picker_screen())
            terminal.send(b"\r")
            terminal.until("picker selects stable eleventh tab", lambda: active()["tab_id"] == eleventh
                           and not any(pane["is_floating"] for pane in terminal.terminals()))
            terminal.prefix(b"W")
            terminal.send(b"h\r")
            terminal.until("reordered fallback follows position rather than stable ID", lambda:
                           active()["tab_id"] == eleventh and active()["position"] == 9 and "9:Tab #9" in top_line())

            terminal.prefix(b"0")
            terminal.until("leave the reordered tab", lambda: active()["position"] == 0)
            terminal.prefix(b"\x06")
            terminal.until("reordered picker opens", lambda: "Tabs (attention" in picker_screen())
            terminal.send(b"9:")
            terminal.until("picker exposes the new position", lambda:
                           "1/11" in picker_screen() and "9: Tab #9" in picker_screen())
            terminal.send(b"\r")
            terminal.until("reordered selection retains the stable ID", lambda:
                           active()["tab_id"] == eleventh
                           and not any(pane["is_floating"] for pane in terminal.terminals()))
            terminal.prefix(b"v")
            terminal.until("split has two tiled terminals", lambda:
                           len([pane for pane in terminal.terminals() if pane["tab_id"] == eleventh]) == 2)
            hook = home / ".local/share/zsh/zellij-auto-title.zsh"
            terminal.send(("zsh -f\rsource " + shlex.quote(str(hook)) + "\rcd "
                           + shlex.quote(str(project)) + "\r").encode())
            terminal.until("directory/git hook titles the generated split tab", lambda:
                           active()["name"] == "project [topic]" and "9:project [topic]" in top_line())
            terminal.send(b"printf '\\033]2;application work\\007'; read application_done\r")
            terminal.until("application title overlays the managed native directory name", lambda:
                           active()["name"] == "project [topic]" and "9:application work" in top_line())
            terminal.send(b"done\r")
            terminal.until("prompt restores the directory pane title", lambda:
                           "9:project [topic]" in top_line())
            ownership_probe = home / "ownership.json"
            terminal.send(('env -u ZELLIJ_SOCKET_DIR zellij-status view "$ZELLIJ_SESSION_NAME" > '
                           + shlex.quote(str(ownership_probe)) + "\r").encode())
            terminal.until("server ancestry identifies ownership without a socket override", lambda:
                           ownership_probe.exists() and json.loads(ownership_probe.read_text())
                           ["auto_titles"].get(str(eleventh)) == "project [topic]")
            token = base64.urlsafe_b64encode(name.encode()).decode()
            preview = subprocess.run([str(home / ".local/bin/zellij-picker"), "--preview-session", token],
                                     env={**env, "ZELLIJ_SESSION_NAME": name}, check=True,
                                     capture_output=True, text=True, timeout=10)
            assert "9: project [topic]" in preview.stdout, preview.stdout
            source = next(pane for pane in terminal.terminals()
                          if pane["tab_id"] == eleventh and pane["is_focused"])
            terminal.action("rename-pane", "agent work", "--pane-id", f"terminal_{source['id']}")
            terminal.send(b"cd ..\r")
            terminal.until("shell hook preserves explicit pane title", lambda: "9:agent work" in top_line())
            other = Terminal(binary, env, name)
            other.grant_status_permissions()
            other.prefix(b"9")
            other.until("second attachment is ready", lambda: b"agent work" in other.output)
            other.prefix(b"h")
            terminal.until("disagreeing client focus uses an unambiguous fallback", lambda:
                           len([pane for pane in terminal.terminals()
                                if pane["tab_id"] == eleventh and pane["is_focused"]]) == 2
                           and "9:Tab #9" in top_line())
            preview = subprocess.run([str(home / ".local/bin/zellij-picker"), "--preview-session", token],
                                     env={**env, "ZELLIJ_SESSION_NAME": name}, check=True,
                                     capture_output=True, text=True, timeout=10)
            assert "9: Tab #9" in preview.stdout, preview.stdout
            # Use the real chooser's complete-snapshot read, including its
            # lifecycle ownership payload and attachment-readiness handling.
            # Caller stdin must not become a second, ownership-free request.
            clients = subprocess.run([sys.executable, "-c",
                                      CLIENT_SNAPSHOT_PROBE,
                                      str(home / ".local/bin/zellij-picker"), name], env=env, check=False,
                                     input="\n", capture_output=True, text=True, timeout=10)
            assert clients.returncode == 0, f"Client snapshot read failed:\n{clients.stderr}\n{clients.stdout}"
            rows = list(json.loads(clients.stdout).values())
            assert {row.get("tab") for row in rows} == {"9: agent work", "9: Tab #9"}, rows
            other.prefix(b"d")
            terminal.prefix(b"r")
            terminal.send(b"manual work\r")
            terminal.send(("cd " + shlex.quote(str(project)) + "\r").encode())
            terminal.until("directory change preserves explicit tab title", lambda:
                           active()["name"] == "manual work" and "9:manual work" in top_line())
            print("PASS: tab positions, direct keys, picker, reorder, directory/git titles, and explicit names agree.")
        except Exception as error:
            capture_failure(terminal, other, error)
            raise
        finally:
            subprocess.run([binary, "kill-session", name], env=env, capture_output=True, timeout=5)
            if other is not None:
                other.close()
            terminal.close()
            # Native shutdown acknowledges before every shell/helper finishes
            # writing. Retry only that teardown race, with a strict bound;
            # permission errors and persistent writers must still fail.
            deadline = time.monotonic() + 5
            while True:
                try:
                    scratch.cleanup()
                    break
                except OSError as error:
                    if error.errno != errno.ENOTEMPTY or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)


if __name__ == "__main__":
    main()
