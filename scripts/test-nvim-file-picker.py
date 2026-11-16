#!/usr/bin/env python3
"""Check standalone file history and its real shell/editor picker entrypoints."""
import argparse
import contextlib
import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import sqlite3
import struct
import subprocess
import sys
import tempfile
import termios
import time

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "scripts/file-history.py"
TIMEOUT = 30 if os.environ.get("CI") else 1


def run(env, *args, cwd=None):
    return subprocess.run([sys.executable, str(HELPER), *args], env=env, cwd=cwd or ROOT,
                          check=True, capture_output=True, timeout=TIMEOUT)


def interact(command, env, cwd, ready, keys):
    """Exercise acceptance/cancellation in fzf's real terminal, including bindings."""
    pid, descriptor = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 120, 0, 0))
        os.chdir(cwd)
        os.execvpe(command[0], command, dict(env, TERM="xterm-256color"))
    output = bytearray()
    exited = False
    try:
        deadline = time.monotonic() + TIMEOUT
        sent = False
        while time.monotonic() < deadline:
            if select.select([descriptor], [], [], 0.05)[0]:
                try:
                    chunk = os.read(descriptor, 65536)
                except OSError:
                    chunk = b""
                output.extend(chunk)
            if not sent and ready in output:
                os.write(descriptor, keys)
                sent = True
            waited, status = os.waitpid(pid, os.WNOHANG)
            if waited:
                exited = True
                assert sent, bytes(output)
                return os.waitstatus_to_exitcode(status)
        raise AssertionError("fzf did not finish: " + output.decode(errors="replace"))
    finally:
        os.close(descriptor)
        if not exited:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGTERM)
            os.waitpid(pid, 0)


def history_check(env, temporary):
    project = temporary / "project with spaces"
    project.mkdir()
    files = [project / path for path in ("Makefile", "long-directory-name/Makefile", "a/b/Makefile")]
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("all:\n")
    db = Path(env["XDG_STATE_HOME"]) / "dotfiles/file-history.sqlite3"
    rows = run(env, "files", cwd=project).stdout.decode().splitlines()
    assert rows == ["Makefile", "long-directory-name/Makefile", "a/b/Makefile"], rows
    assert not db.exists(), "ranking must not create history"
    # A reader can arrive after another process creates the file but before schema creation.
    db.parent.mkdir(parents=True)
    db.touch()
    assert run(env, "files", "--global").stdout == b""
    db.unlink()
    # Cold concurrent writers must retain every accepted visit.
    commands = [[sys.executable, str(HELPER), "record", "--", str(files[2])] for _ in range(12)]
    writers = [subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for command in commands]
    for writer in writers:
        stdout, stderr = writer.communicate(timeout=TIMEOUT)
        assert writer.returncode == 0, (stdout, stderr)
    with sqlite3.connect(db) as connection:
        score, = connection.execute("SELECT score FROM visits WHERE path = ?", (str(files[2]),)).fetchone()
        assert 11.99 < score <= 12, score
        # A once-frequent file should yield to a fresh visit after a year of decay.
        connection.execute("UPDATE visits SET updated = updated - 365 * 86400")
    run(env, "record", "--", str(files[1]))
    rows = run(env, "files", cwd=project).stdout.decode().splitlines()
    assert rows[0] == "long-directory-name/Makefile", rows
    elsewhere = temporary / "another project"
    elsewhere.mkdir()
    rows = run(env, "files", "--global", cwd=elsewhere).stdout.decode().splitlines()
    assert str(files[1]) == rows[0] and str(files[0]) not in rows, rows
    files[2].unlink()
    assert str(files[2]).encode() not in run(env, "files", "--global").stdout
    # NUL output preserves file names with whitespace and shell metacharacters.
    special = project / "picked-file $(touch escaped).txt"
    special.write_text("selected\n")
    run(env, "record", "--", str(special))
    assert os.fsencode(str(special)) in run(env, "files", "--global", "--print0").stdout.split(b"\0")
    # Real Ctrl-T enter binding records a shell selection into the same store.
    shell = '''source "$HOME/.files/zsh/zlogin"
eval "$FZF_CTRL_T_COMMAND" | FZF_DEFAULT_OPTS="--scheme=path $FZF_DEFAULT_OPTS $FZF_CTRL_T_OPTS" fzf --sync --height=100% --no-preview --query=picked-file > "$1"
'''
    selected = temporary / "selection"
    status = interact(["zsh", "-f", "-c", shell, "zsh", str(selected)], env, project, b"picked-file", b"\r")
    assert status == 0, status
    assert selected.read_text().strip() == special.name
    assert not (project / "escaped").exists(), "selected path was interpreted as shell code"
    with sqlite3.connect(db) as connection:
        before = connection.execute("SELECT score FROM visits WHERE path = ?", (str(special),)).fetchone()[0]
        assert before > 1.99, before
    # Global fzf accepts across projects; cancellation must not record a visit.
    for keys, expected in ((b"\3", 130), (b"\r", 0)):
        command = [sys.executable, str(HELPER), "pick", "--global"]
        picker_env = dict(env, FZF_DEFAULT_OPTS="--sync --height=100% --query=picked-file")
        status = interact(command, picker_env, elsewhere, b"picked-file", keys)
        assert status == expected, status
        with sqlite3.connect(db) as connection:
            after = connection.execute("SELECT score FROM visits WHERE path = ?", (str(special),)).fetchone()[0]
        assert (after == before) if expected else (after > before + 0.99), (before, after)
    print("PASS: standalone history, decay, concurrent writers, global search, real Ctrl-T recording and cancellation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", choices=("history", "editor"))
    args = parser.parse_args()
    plugins = Path(os.environ.get("NVIM_TEST_PLUGIN_ROOT", Path.home() / ".local/share/nvim/lazy"))
    if args.check != "history":
        for name in ("fzf-lua", "nvim-web-devicons"):
            if not (plugins / name / "lua").is_dir():
                raise SystemExit(f"Missing installed plugin: {plugins / name}")
    with tempfile.TemporaryDirectory(prefix="file-picker-test-") as temporary:
        temporary = Path(temporary).resolve()
        env = dict(os.environ, NVIM_TEST_PLUGIN_ROOT=str(plugins))
        home = temporary / "home with spaces"
        home.mkdir()
        (home / ".files").symlink_to(ROOT)
        env["HOME"] = str(home)
        env.pop("NVIM", None)
        env.pop("NVIM_LISTEN_ADDRESS", None)
        env["GIT_CONFIG_GLOBAL"] = os.devnull
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        for kind in ("CONFIG", "DATA", "STATE", "CACHE", "RUNTIME"):
            directory = temporary / kind.lower()
            directory.mkdir(mode=0o700)
            env[f"XDG_{kind}_DIR" if kind == "RUNTIME" else f"XDG_{kind}_HOME"] = str(directory)
        if args.check != "editor":
            history_check(env, temporary)
        if args.check != "history":
            # Keep the editor scenario independent of the shell history fixture.
            editor_state = temporary / "editor-state"
            editor_state.mkdir()
            env["XDG_STATE_HOME"] = str(editor_state)
            return subprocess.run(
                ["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l", "nvim/tests/file-picker.lua"],
                cwd=ROOT, env=env, timeout=TIMEOUT,
            ).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
