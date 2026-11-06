#!/usr/bin/env python3
"""Exercise installed directory-title shell hooks; Zellij rendering is separate."""

import os
from pathlib import Path
import pty
import shlex
import shutil
import subprocess
import tempfile

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
        context.write_text('#!/bin/sh\n[ "$PROVIDER" != failure ] || exit 1\nprintf "%s\\n" "$PROVIDER"\n')
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
        env = {**os.environ, "HOME": str(home), "PATH": f"{executables}:{os.environ['PATH']}",
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
        assert observed == (b"\x1b]2;project with spaces [topic]\x07"
                               b"\x1b]2;project with spaces [other]\x07"
                               b"\x1b]2;plain\x07\x1b]2;bad   name\x07"), repr(observed)
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
    import sys

    with tempfile.TemporaryDirectory(prefix="zellij-title-state-") as temporary:
        work = Path(temporary)
        executables = work / "bin"
        executables.mkdir()
        sockets = work / "run" / "contract_version_1"
        sockets.mkdir(parents=True)
        cache = work / "cache" / "contract_version_1"
        cache.mkdir(parents=True)
        with sqlite3.connect(cache / "session_index.sqlite") as db:
            db.execute("CREATE TABLE sessions (name TEXT PRIMARY KEY, id TEXT)")
            db.execute("INSERT INTO sessions VALUES ('fixture', 'abc123')")
        state = work / "native.json"
        state.write_text(json.dumps({"tab_id": 4, "name": "Tab #5"}))
        fake = executables / "zellij"
        fake.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
state = pathlib.Path(os.environ["NATIVE_STATE"])
args = sys.argv[1:]
if args == ["setup", "--check"]:
    print('[Version]: "0.46.0"\\n[CACHE DIR]: ' + os.environ["XDG_CACHE_HOME"])
elif "list-panes" in args:
    print(json.dumps([{"id": 7, "tab_id": 4, "is_plugin": False, "is_focused": True}]))
elif "list-tabs" in args:
    print('[' + state.read_text() + ']')
elif "rename-tab" in args:
    assert args[args.index("--tab-id") + 1] == "4"
    tab = json.loads(state.read_text())
    tab["name"] = args[-1]
    state.write_text(json.dumps(tab))
else:
    raise SystemExit(1)
''')
        fake.chmod(0o755)
        ps = executables / "ps"
        # The controlled ancestry boundary identifies this test process as the
        # nearest server; real ancestry is exercised by the native workflow.
        ps.write_text(f'#!/bin/sh\nprintf "%s 1 zellij\\n" {os.getpid()}\n')
        ps.chmod(0o755)
        env = {**os.environ, "PATH": f"{executables}:{os.environ['PATH']}",
               "ZELLIJ_SESSION_NAME": "fixture", "ZELLIJ_PANE_ID": "7",
               "ZELLIJ_SOCKET_DIR": str(work / "run"), "NATIVE_STATE": str(state),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_STATE_HOME": str(work / "state"),
               "PWD": str(work / "project")}

        def rename():
            subprocess.run([sys.executable, ROOT / "bin/zellij-auto-title"],
                           cwd=work, env=env, check=True, timeout=5)
            return json.loads(state.read_text())["name"]

        def owned():
            result = subprocess.run([sys.executable, ROOT / "bin/zellij-status", "view", "fixture"],
                                    env=env, check=True, capture_output=True, text=True, timeout=5)
            return json.loads(result.stdout)["auto_titles"]

        with socket.socket(socket.AF_UNIX) as original, socket.socket(socket.AF_UNIX) as replacement:
            address = sockets / "abc123"
            original.bind(str(address))
            assert rename() == "project"
            assert owned() == {"4": "project"}
            env["PWD"] = str(work / "next")
            assert rename() == "next"
            assert owned() == {"4": "next"}
            state.write_text(json.dumps({"tab_id": 4, "name": "manual"}))
            assert rename() == "manual", "explicit title was overwritten"
            # A resurrected session may reuse its ID and the exact old title.
            # Its new socket must prevent old ownership transferring to it.
            address.unlink()
            replacement.bind(str(address))
            state.write_text(json.dumps({"tab_id": 4, "name": "next"}))
            env["PWD"] = str(work / "new-session")
            assert owned() == {}, "stale ownership survived socket replacement"
            assert rename() == "next", "new session's explicit title was overwritten"
            state.write_text(json.dumps({"tab_id": 4, "name": "Tab #5"}))
            assert rename() == "new-session", "generated title did not resume ownership"
            assert owned() == {"4": "new-session"}
            record = next((work / "state/zellij-auto-titles").glob("*.json"))
            record.write_text(json.dumps("new-session"))
            env["PWD"] = str(work / "legacy")
            assert owned() == {}
            assert rename() == "new-session", "legacy record claimed unproven ownership"
        print("PASS: native title ownership, explicit names, socket recreation, and legacy state (controlled CLI, real sockets/index).")


if __name__ == "__main__":
    main()
    ownership_lifecycle()
