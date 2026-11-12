#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte==0.8.2"]
# ///
"""Render the real worktree picker and exercise filtering, narrowing, resize and selection."""

import codecs
import fcntl
import html
import importlib.util
import os
from pathlib import Path
import pty
import re
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time

import pyte

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native", ROOT / "scripts/test-theme-native.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def main():
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs/images/directory-picker"
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="picker-native-") as directory:
        home = Path(directory).resolve()
        repo, topic = home / "src/payments", home / "worktrees/payment-retries"
        repo.mkdir(parents=True)
        (repo / "README.md").write_text("Payments repository\n")
        (repo / "src").mkdir()
        (repo / "src/main.py").write_text("print('hello')\n")
        commit_date = "2026-01-01T00:00:00Z"
        git_env = {**os.environ, "GIT_AUTHOR_DATE": commit_date, "GIT_COMMITTER_DATE": commit_date}
        def git(*args):
            subprocess.run(["git", "-C", str(repo), *args], env=git_env, check=True, capture_output=True)
        git("init", "-b", "main")
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture")
        git("worktree", "add", "-b", "retry-payments", str(topic))
        (topic / "src/main.py").write_text("def retry_payment():\n    return 'retried'\n")
        (topic / "src/retry.py").write_text("RETRIES = 3\n")
        git("-C", str(topic), "add", ".")
        git("-C", str(topic), "-c", "user.name=Fixture", "-c", "user.email=test@example.invalid", "commit", "-m", "Retry payments")
        for limit, subject in ((4, 'Handle retry exhaustion'), (6, 'Bound retry attempts')):
            (topic / 'src/retry.py').write_text(f'RETRIES = {limit}\n')
            git('-C', str(topic), 'add', '.')
            git('-C', str(topic), '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', subject)
        (topic / "README.md").write_text("# Payments\n\nRetry failed payments with bounded backoff.\n\n```python\ndef retry_payment(attempts=5):\n    return attempts\n```\n")
        (topic / "src/retry.py").write_text("RETRIES = 5\n")
        git("-C", str(topic), "add", "src/retry.py")
        (topic / "NOTES.md").write_text("Investigate backoff\n")
        tools = home / 'tools'
        tools.mkdir()
        tmux = tools / 'tmux'
        tmux.write_text("#!/bin/sh\nprintf '%s\\n' " + shlex.quote(str(topic) + "\tcodex\t%1") + "\n")
        tmux.chmod(0o755)
        (home / ".files").symlink_to(ROOT)
        binary_path = Path(".local/libexec/dotfiles/directory-picker-ui")
        installed = Path.home() / binary_path
        if not installed.is_file():
            raise SystemExit("Build the native picker with make directory-picker before this check.")
        (home / binary_path).parent.mkdir(parents=True)
        (home / binary_path).symlink_to(installed)
        result = home / "result"
        env = {**os.environ, "HOME": str(home), "TERM": "xterm-256color", "COLORTERM": "truecolor", "FZF_DEFAULT_OPTS": "", "FZF_DEFAULT_OPTS_FILE": "", "DOTFILES_THEME_DIR": str(ROOT / "design-system/generated"), "PATH": str(tools) + os.pathsep + os.environ["PATH"]}
        for key in ("NO_COLOR", "TMUX", "TMUX_PANE", "ZELLIJ", "ZELLIJ_SESSION_NAME"):
            env.pop(key, None)
        if shutil.which('bat'):
            themes = home / '.config/bat/themes'
            themes.mkdir(parents=True)
            shutil.copyfile(ROOT / 'design-system/generated/Dotfiles.tmTheme', themes / 'Dotfiles.tmTheme')
            env.update(BAT_CONFIG_DIR=str(themes.parent), BAT_CACHE_PATH=str(home / '.cache/bat'))
            subprocess.run(['bat', 'cache', '--build'], env=env, check=True, capture_output=True)
        domains = ("address", "billing", "carrier", "claims", "delivery", "events", "fraud",
                   "insurance", "parcel", "rates", "routing", "tracking", "webhooks")
        paths = [home / "src" / f"{name}-{suffix}" for name in domains
                 for suffix in ("api", "cli", "dashboard", "docs", "jobs", "worker")]
        paths.extend((home / "release notes", repo, topic))
        for path in paths:
            path.mkdir(exist_ok=True)
        (home / "history").write_text("".join(f"{len(paths)-i} {path}\n" for i, path in enumerate(paths)))
        # fd gates the shell's fzf bindings. The directory-history and worktree sources never invoke it.
        if not shutil.which("fd"):
            (tools / "fd").symlink_to(shutil.which("true"))
        (home / ".zsh/cache").mkdir(parents=True)
        env.update(ZDOTDIR=str(home), SHELL=shutil.which("zsh"))
        (home / ".zshrc").write_text(
            'source "$HOME/.files/zsh/zshrc"\nsource "$HOME/.files/sh/alias"\n'
            '_z() { cat "$HOME/history"; }\n'
            'record_directory() { print -r -- "$PWD" > "$HOME/result"; }\n'
            'chpwd_functions+=(record_directory)\nPS1="picker-ready> "\n')
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(repo)
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 36, 140, 0, 0))
            os.execvpe("zsh", ["zsh", "-d", "-i"], env)
        screen = native.NativeScreen(140, 36)
        stream, decoder = pyte.Stream(screen), codecs.getincrementaldecoder("utf-8")("replace")
        def until(predicate):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if select.select([fd], [], [], .05)[0]:
                    try:
                        chunk = os.read(fd, 65536)
                    except OSError:
                        if predicate():
                            return
                        break
                    stream.feed(decoder.decode(chunk))
                if predicate():
                    return
            raise AssertionError("Picker condition failed:\n" + "\n".join(screen.display))
        def text():
            return "\n".join(screen.display)
        def capture(name):
            # rationale: Drain asynchronous repaint output before recording terminal cells.
            quiet = time.monotonic() + .15
            while time.monotonic() < quiet:
                if select.select([fd], [], [], .03)[0]:
                    stream.feed(decoder.decode(os.read(fd, 65536)))
                    quiet = time.monotonic() + .15
            colors = {"default": "#D8DEE9", "black": "#3B4252", "red": "#BF616A", "green": "#A3BE8C", "brown": "#EBCB8B", "blue": "#81A1C1", "magenta": "#B48EAD", "cyan": "#88C0D0", "white": "#E5E9F0"}
            def color(value, fallback):
                return colors.get(value, "#" + value if len(value) == 6 else fallback)
            svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{screen.columns*9+24}" height="{screen.lines*20+24}">',
                   '<rect width="100%" height="100%" fill="#2E3440"/>',
                   '<g font-family="Hack Nerd Font Mono" font-size="14">']
            for row in range(screen.lines):
                for column in range(screen.columns):
                    cell = screen.buffer[row][column]
                    fg = color(cell.fg, "#D8DEE9")
                    bg = "#2E3440" if cell.bg == "default" else color(cell.bg, "#2E3440")
                    if cell.reverse:
                        fg, bg = bg, fg
                    x, y = column*9+12, row*20+12
                    if bg != "#2E3440":
                        svg.append(f'<rect x="{x}" y="{y}" width="9" height="20" fill="{bg}"/>')
                    if cell.data.strip():
                        weight = "bold" if cell.bold else "normal"
                        svg.append(f'<text x="{x}" y="{y+15}" fill="{fg}" font-weight="{weight}">{html.escape(cell.data)}</text>')
            (destination / (name + ".svg")).write_text("".join([*svg, "</g></svg>\n"]))
        def resize(columns, lines):
            screen.resize(lines=lines, columns=columns)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0))
            os.killpg(pid, signal.SIGWINCH)
        try:
            until(lambda: "picker-ready>" in text())
            os.write(fd, b"\x1bw")
            until(lambda: "Worktrees >" in text() and "clean" in text())
            # Compare both worktrees, then narrow the real picker and inspect the selected one.
            until(lambda: "Working tree" in text())
            until(lambda: "dirty 3" in screen.display[2] and "Codex" in screen.display[2])
            capture("worktrees")
            assert "payments · main" in screen.display[1] and "clean" in screen.display[1]
            assert "payments · retry-payments" in screen.display[2] and "Codex" in screen.display[2]
            os.write(fd, b"'Codex dirty")
            until(lambda: "1/2" in text() and "Working tree  3 files" in text())
            os.write(fd, b"\x15")
            until(lambda: "2/2" in text())
            os.write(fd, b"payment-retries")
            until(lambda: "1/2" in text() and "Working tree  3 files" in text())
            until(lambda: 'return attempts' in text() and 'Bound retry attempts' in text())
            recent = next(line for line in screen.display if 'Bound retry attempts' in line)
            assert re.search(r'1 file\s+\+1\s+−1', recent), recent
            first = next(line for line in screen.display if 'Retry payments' in line)
            assert re.search(r'2 files\s+\+3\s+−1', first), first
            if shutil.which('glow'):
                assert '```' not in text(), 'README contains raw code fences'
                assert '# Payments' not in text(), 'README heading was not rendered'
            assert '\uf418' in text() and r'\uf418' not in text(), 'Branch glyph was escaped'
            assert any(screen.buffer[r][c].bg == 'a3be8c' for r in range(screen.lines) for c in range(screen.columns//2, screen.columns)), 'Staged pill fill missing'
            assert 'ctrl-' not in text(), 'Picker includes instruction text'
            assert any(screen.buffer[r][c].fg == '88c0d0' for r in range(screen.lines) for c in range(screen.columns)), 'Shared accent color missing'
            assert any(screen.buffer[r][c].bg == '434c5e' for r in range(screen.lines) for c in range(screen.columns)), 'Shared selection color missing'
            assert any(screen.buffer[r][c].fg == 'ebcb8b' for r in range(screen.lines) for c in range(screen.columns//2, screen.columns)), 'Preview Git change color missing'
            capture("wide")
            os.write(fd, b"\x00")
            until(lambda: "1/1" in text())
            resize(80, 40)
            until(lambda: "Working tree  3 files" in text() and any("─" in row for row in screen.display[10:]))
            capture("tall")
            resize(80, 18)
            until(lambda: "Worktrees >" in text() and "Working tree" not in text())
            capture("compact")
            os.write(fd, b"\x1f")
            until(lambda: "Working tree  3 files" in text())
            os.write(fd, b"\r")
            until(result.exists)
            assert result.read_text().strip() == str(topic)
            until(lambda: "picker-ready>" in text())
            result.unlink()
            resize(172, 44)
            os.write(fd, b"\x02")
            until(lambda: "81/81" in text() and "payment-retries" in text())
            labels = ["~/" + str(path.relative_to(home)) for path in paths]
            assert labels[0] in screen.display[1] and labels[41] in screen.display[1], screen.display[1]
            capture("history")
            os.write(fd, b"billing-")
            until(lambda: "6/81" in text())
            for row, label in enumerate(labels[6:12], 1):
                assert label in screen.display[row], screen.display[row]
            os.write(fd, b"\x15")  # clear the query
            until(lambda: "81/81" in text())
            os.write(fd, b"\x1b[C")  # same row in the next result column
            until(lambda: "› " + labels[47] in text())
            resize(72, 18)
            until(lambda: "› " + labels[47] in text())
            os.write(fd, b"\r")
            until(lambda: result.exists() and result.read_text().strip() == str(paths[47]))
            until(lambda: "picker-ready>" in text())
            os.write(fd, b'print -r -- "$PWD" > "$HOME/preserved"')
            os.write(fd, b"\x02")
            until(lambda: "81/81" in screen.display[0] and "› " + labels[0] in text())
            os.write(fd, b"webhooks-jobs")
            until(lambda: "1/81" in screen.display[0] and "webhooks-jobs" in screen.display[0])
            os.write(fd, b"\x1b")
            until(lambda: "picker-ready>" in text() and "preserved" in text())
            assert not (home / "preserved").exists(), "Cancelled picker executed unfinished input"
            os.write(fd, b"\r")
            until(lambda: (home / "preserved").exists())
            assert (home / "preserved").read_text().strip() == str(paths[47])
            os.write(fd, b"exit\r")
            print("PASS: Ctrl-B and Alt-W reflow, filter, preserve selection and unfinished input, and jump.")
        finally:
            os.close(fd)
            if os.waitpid(pid, os.WNOHANG)[0] == 0:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                os.waitpid(pid, 0)


if __name__ == "__main__":
    main()
