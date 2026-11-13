#!/usr/bin/env python3
"""Exercise installed directory-title shell hooks; Zellij rendering is separate."""

import hashlib
import os
from pathlib import Path
import pty
import shlex
import shutil
import subprocess
import tempfile
import sys
from zellij_ipc_fixture import fields, message

ROOT = Path(__file__).resolve().parents[1]


def main():
    zsh = shutil.which("zsh")
    assert zsh, "zsh is required"
    with tempfile.TemporaryDirectory(prefix="zellij-auto-title-") as temporary:
        work = Path(temporary)
        home = work / "home"
        home.mkdir()
        executables = work / "bin"
        executables.mkdir()
        context = executables / "zellij-context"
        context.write_text('''#!/bin/sh
if [ "$1" = title-context ]; then
  [ "$PROVIDER" = zellij ] || exit 1
  printf '{}\\n'
else
  [ "$PROVIDER" != failure ] || exit 1
  printf '%s\\n' "$PROVIDER"
fi
''')
        context.chmod(0o755)
        tmux = executables / "tmux"
        tmux.write_text('''#!/bin/sh
case "$*" in
  *'#{window_index}'*) echo 0 ;;
  *'#{pane_active}'*) echo 1 ;;
  *'#{window_name}'*) echo zsh ;;
  rename-window*) printf '%s\\n' "$*" >> "$TMUX_LOG" ;;
esac
''')
        tmux.chmod(0o755)
        env = {**os.environ, "HOME": str(home), "PATH": f"{executables}:{ROOT / 'bin'}:{os.environ['PATH']}",
               "ZELLIJ": "1", "ZELLIJ_PANE_ID": "7", "ZELLIJ_SESSION_NAME": "fixture", "TMUX": "outer-session",
               "PROVIDER": "zellij", "TMUX_LOG": str(work / "tmux.log"),
               "TMPDIR": str(work)}
        subprocess.run(["make", "zsh-config", f"HOME={home}"], cwd=ROOT,
                       env=env, check=True, capture_output=True)
        project = work / "project with spaces"
        project.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "topic"], cwd=project, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-qm", "Initial", "--allow-empty"], cwd=project, check=True)
        plain = work / "plain"
        plain.mkdir()
        unsafe = work / "bad\x1b\x07\nname"
        unsafe.mkdir()
        hook_dir = home / ".local/share/zsh"
        source = (f'source {shlex.quote(str(hook_dir / "tmux-auto-title.zsh"))}\n'
                  f'source {shlex.quote(str(hook_dir / "zellij-auto-title.zsh"))}\n')

        def run(script, provider="zellij", terminal=True):
            master, slave = pty.openpty()
            try:
                result = subprocess.run([zsh, "-f", "-c", source + script], cwd=plain,
                                        env={**env, "PROVIDER": provider},
                                        stdout=slave if terminal else subprocess.PIPE,
                                        stderr=subprocess.PIPE, timeout=10)
                assert result.returncode == 0, result.stderr
                if not terminal:
                    return result.stdout
                # Keep the slave open until queued bytes are drained: macOS
                # can discard unread PTY output when its last slave closes.
                # The child has exited, so no later output is expected.
                os.set_blocking(master, False)
                output = b""
                while True:
                    try:
                        part = os.read(master, 4096)
                    except BlockingIOError:
                        break
                    if not part:
                        break
                    output += part
                return output
            finally:
                os.close(master)
                if slave is not None:
                    os.close(slave)

        script = f'''cd {shlex.quote(str(project))}
git checkout -qb other
for hook in $precmd_functions; do "$hook"; done
cd {shlex.quote(str(plain))}
cd {shlex.quote(str(unsafe))}
'''
        observed = run(script)
        assert observed == ("\x1b]2;project with spaces  topic\x07"
                               "\x1b]2;project with spaces  other\x07"
                               "\x1b]2;plain\x07\x1b]2;bad   name\x07").encode(), repr(observed)
        assert not (work / "tmux.log").exists(), "inner Zellij renamed outer tmux"
        cd = f"cd {shlex.quote(str(plain))}\n"
        assert run(cd, terminal=False) == b""
        assert run(cd, provider="failure") == b""
        assert run(cd, provider="none") == b""
        assert run(cd, provider="tmux") == b""
        assert (work / "tmux.log").read_text() == "rename-window -t :0 plain\n"
        print("PASS: installed directory/git hooks, branch refresh, control sanitization, redirected output, and nearest-multiplexer routing (controlled provider boundary).")


def ownership_lifecycle():
    """Exercise native renaming and status reads across a real socket replacement."""
    import json
    import socket
    import sqlite3
    import struct
    import threading
    from contextlib import contextmanager, ExitStack

    # Independent wire fixture for Action(9), ListPanes(98), RenameTabById(103)
    # and Log(5)/UnblockInputThread(2) from the pinned protobuf contract.
    @contextmanager
    def server(listener, state):
        stopped, errors = threading.Event(), []
        listener.listen()
        listener.settimeout(0.05)

        def serve():
            try:
                while not stopped.is_set():
                    try:
                        connection, _ = listener.accept()
                    except socket.timeout:
                        continue
                    with connection:
                        connection.settimeout(1)

                        def receive(length):
                            data = b""
                            while len(data) < length:
                                part = connection.recv(length - len(data))
                                assert part, "Client disconnected before completing its request"
                                data += part
                            return data

                        length = struct.unpack("<I", receive(4))[0]
                        request = fields(fields(receive(length))[9])
                        assert request.get(2) in (None, 7, 999) and request[4] == 1
                        action = fields(request[1])
                        tab = json.loads(state.read_text())
                        ack = message(2, b"")
                        if 104 in action:
                            tabs = [{"tab_id": tab["tab_id"], "name": tab["name"]}]
                            if "other_name" in tab:
                                tabs.append({"tab_id": 2, "name": tab["other_name"]})
                            if "loading_name" in tab:
                                tabs.append({"tab_id": 5, "name": tab["loading_name"]})
                            response = message(5, message(1, json.dumps(tabs).encode()))
                            connection.sendall(struct.pack("<I", len(ack)) + ack)
                        elif 98 in action:
                            assert fields(action[98])[6] == 1
                            panes = [{"id": 7, "tab_id": tab["tab_id"], "tab_name": tab["name"],
                                      "title": tab.get("title", ""),
                                      "is_plugin": False, "is_focused": True}]
                            if "other_name" in tab:
                                panes.append({"id": 8, "tab_id": 2, "tab_name": tab["other_name"],
                                              "title": tab.get("other_title", ""),
                                              "is_plugin": False, "is_focused": False})
                            response = message(5, message(1, json.dumps(panes).encode()))
                            connection.sendall(struct.pack("<I", len(ack)) + ack)
                        else:
                            rename = fields(action[103])
                            target = rename.get(1, 0)
                            assert target in (tab["tab_id"], 2)
                            tab["name" if target == tab["tab_id"] else "other_name"] = rename[2].decode()
                            state.write_text(json.dumps(tab))
                            response = ack
                        frame = struct.pack("<I", len(response)) + response
                        connection.sendall(frame[:2])
                        connection.sendall(frame[2:])
            except Exception as error:
                errors.append(error)

        worker = threading.Thread(target=serve)
        worker.start()
        try:
            yield
        finally:
            stopped.set()
            worker.join(timeout=2)
            assert not worker.is_alive(), "Fixture server failed to stop"
            assert not errors, errors

    with tempfile.TemporaryDirectory(prefix="zj-title-state-", dir="/tmp") as temporary:
        work = Path(temporary)
        executables = work / "bin"
        executables.mkdir()
        sockets = work / "run" / "contract_version_1"
        sockets.mkdir(parents=True)
        cache_root = (work / "home/Library/Caches/org.Zellij-Contributors.Zellij" if sys.platform == "darwin"
                      else work / "cache/zellij")
        cache = cache_root / "contract_version_1"
        cache.mkdir(parents=True)
        index_name = "session_index-" + hashlib.sha256(os.fsencode(sockets)).hexdigest()[:12] + ".sqlite"
        with sqlite3.connect(cache / index_name) as db:
            db.execute("CREATE TABLE sessions (name TEXT PRIMARY KEY, id TEXT, created_at INTEGER)")
            db.execute("INSERT INTO sessions VALUES ('fixture', 'abc123', 123)")
        state = work / "native.json"
        state.write_text(json.dumps({"tab_id": 4, "name": "Tab #5"}))
        fake = executables / "zellij"
        fake.write_text("#!/bin/sh\nexit 99\n")
        fake.chmod(0o755)
        ps = executables / "ps"
        ps.write_text("#!/bin/sh\nexit 99\n")
        ps.chmod(0o755)
        env = {**os.environ, "PATH": f"{executables}:{ROOT / 'bin'}:{os.environ['PATH']}",
               "ZELLIJ_SESSION_NAME": "fixture", "ZELLIJ_PANE_ID": "7",
               "ZELLIJ_SOCKET_DIR": str(work / "run"), "NATIVE_STATE": str(state),
               "HOME": str(work / "home"), "FIXTURE_ZELLIJ_CACHE": str(cache_root),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_STATE_HOME": str(work / "state"),
               "PWD": str(work / "project")}

        def rename():
            directory = Path(env["PWD"])
            directory.mkdir(exist_ok=True)
            subprocess.run([ROOT / "bin/zellij-auto-title"],
                           cwd=directory, env=env, check=True, timeout=5)
            return json.loads(state.read_text())["name"]

        def owned():
            result = subprocess.run([ROOT / "bin/zellij-status", "view", "fixture"],
                                    env=env, check=True, capture_output=True, text=True, timeout=5)
            return json.loads(result.stdout)["auto_titles"]

        with socket.socket(socket.AF_UNIX) as original, socket.socket(socket.AF_UNIX) as replacement, ExitStack() as servers:
            address = sockets / "abc123"
            original.bind(str(address))
            servers.enter_context(server(original, state))
            env["ZELLIJ_TITLE_CONTEXT"] = subprocess.check_output(
                [ROOT / "bin/zellij-context", "title-context"], env=env, text=True).strip()
            assert rename() == "project"
            assert owned() == {"4": "project"}
            env["PWD"] = str(work / "next")
            assert rename() == "project"
            assert owned() == {"4": "project"}
            state.write_text(json.dumps({"tab_id": 4, "name": "manual"}))
            assert rename() == "manual", "explicit title was overwritten"
            # Restore a recorded automatic name after replacing the server.
            address.unlink()
            replacement.bind(str(address))
            servers.enter_context(server(replacement, state))
            state.write_text(json.dumps({"tab_id": 0, "name": "project"}))
            env["PWD"] = str(work / "new-session")
            assert owned() == {}, "stale ownership survived socket replacement"
            assert rename() == "project", "new session's explicit title was overwritten"
            state.write_text(json.dumps({"tab_id": 0, "name": "Tab #1"}))
            assert rename() == "Tab #1", "cached context crossed server lifetimes"
            state.write_text(json.dumps({"tab_id": 0, "name": "project"}))
            env["ZELLIJ_TITLE_CONTEXT"] = subprocess.check_output(
                [ROOT / "bin/zellij-context", "title-context"], env=env, text=True).strip()
            state.write_text(json.dumps({"tab_id": 0, "name": "project", "loading_name": "pending"}))
            assert rename() == "project", "partial resurrection reconciled title records"
            assert next((work / "state/zellij-auto-titles").glob("*-4.json")).exists()
            state.write_text(json.dumps({"tab_id": 0, "name": "project"}))
            assert rename() == "new-session", "restored automatic title did not resume ownership"
            assert owned() == {"0": "new-session"}
            state.write_text(json.dumps({"tab_id": 3, "name": "project"}))
            assert rename() == "project", "obsolete title record took over a fresh manual tab"
            state.write_text(json.dumps({"tab_id": 0, "name": "manual"}))
            assert rename() == "manual", "restored manual name was overwritten"
            state.write_text(json.dumps({"tab_id": 0, "name": "new-session"}))
            record = next((work / "state/zellij-auto-titles").glob("*-0.json"))
            record.write_text(json.dumps("new-session"))
            env["PWD"] = str(work / "legacy")
            assert owned() == {}
            assert rename() == "new-session", "legacy record claimed unproven ownership"
            state.write_text(json.dumps({"tab_id": 0, "name": "Tab #1"}))
            assert rename() == "legacy"
            third = servers.enter_context(socket.socket(socket.AF_UNIX))
            address.unlink()
            third.bind(str(address))
            servers.enter_context(server(third, state))
            state.write_text(json.dumps({"tab_id": 0, "name": "legacy", "other_name": "legacy"}))
            env["PWD"] = str(work / "ambiguous")
            env["ZELLIJ_TITLE_CONTEXT"] = subprocess.check_output(
                [ROOT / "bin/zellij-context", "title-context"], env=env, text=True).strip()
            assert rename() == "legacy", "ambiguous restored name claimed ownership"
            assert owned() == {}
            state.write_text(json.dumps({"tab_id": 0, "name": "review", "title": "current project",
                                         "other_name": "logs", "other_title": "log project"}))
            env["ZELLIJ_TITLE_CONTEXT"] = '{"session":"obsolete"}'
            subprocess.run([ROOT / "bin/zellij-auto-title", "--clear"],
                           env=env, check=True, timeout=5)
            assert json.loads(state.read_text())["name"] == "current project"
            assert json.loads(state.read_text())["other_name"] == "logs", "clear renamed another tab"
            assert owned() == {"0": "current project"}
            failed = subprocess.run([ROOT / "bin/zellij-auto-title", "--clear"],
                                    env={**env, "ZELLIJ_PANE_ID": "999"},
                                    capture_output=True, text=True, timeout=5)
            assert failed.returncode != 0 and "Cannot find" in failed.stderr, failed
            assert json.loads(state.read_text())["other_name"] == "logs"
            state.write_text(json.dumps({"tab_id": 0, "name": "current project", "title": "changed program",
                                         "other_name": "logs", "other_title": "log project"}))
            subprocess.run([ROOT / "bin/zellij-auto-title", "--clear", "--all"],
                           env=env, check=True, timeout=5)
            assert json.loads(state.read_text())["name"] == "current project", "clear lost an automatic provider"
            assert json.loads(state.read_text())["other_name"] == "log project"
            assert owned() == {"0": "current project", "2": "log project"}
            subprocess.run([ROOT / "bin/zellij-auto-title", "--clear", "--all"],
                           env=env, check=True, timeout=5)
            assert owned() == {"0": "current project", "2": "log project"}, "clear was not idempotent"
        print("PASS: protobuf title ownership, explicit names, socket recreation, and legacy state (real sockets/index).")


if __name__ == "__main__":
    main()
    ownership_lifecycle()
