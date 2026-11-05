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
               "ZELLIJ": "1", "ZELLIJ_PANE_ID": "7", "TMUX": "outer-session",
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


if __name__ == "__main__":
    main()
