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
        def git(*args):
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
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
        result = home / "result"
        env = {**os.environ, "HOME": str(home), "TERM": "xterm-256color", "FZF_DEFAULT_OPTS": "", "FZF_DEFAULT_OPTS_FILE": "", "DOTFILES_THEME_DIR": str(ROOT / "design-system/generated"), "PATH": str(tools) + os.pathsep + os.environ["PATH"]}
        for key in ("NO_COLOR", "TMUX", "TMUX_PANE", "ZELLIJ", "ZELLIJ_SESSION_NAME"):
            env.pop(key, None)
        if shutil.which('bat'):
            themes = home / '.config/bat/themes'
            themes.mkdir(parents=True)
            shutil.copyfile(ROOT / 'design-system/generated/Dotfiles.tmTheme', themes / 'Dotfiles.tmTheme')
            env.update(BAT_CONFIG_DIR=str(themes.parent), BAT_CACHE_PATH=str(home / '.cache/bat'))
            subprocess.run(['bat', 'cache', '--build'], env=env, check=True, capture_output=True)
        command = f'source {shlex.quote(str(ROOT / "sh/alias"))}; zw; print -r -- "$PWD" > {shlex.quote(str(result))}'
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(repo)
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 36, 140, 0, 0))
            os.execvpe("zsh", ["zsh", "-f", "-c", command], env)
        screen = native.NativeScreen(140, 36)
        stream, decoder = pyte.Stream(screen), codecs.getincrementaldecoder("utf-8")("replace")
        def until(predicate):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if select.select([fd], [], [], .05)[0]:
                    try:
                        chunk = os.read(fd, 65536)
                    except OSError:
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
            until(lambda: "Worktrees >" in text() and "clean" in text())
            # The real fzf must search path labels, then retain exactly the filtered set.
            os.write(fd, b"payment-retries")
            until(lambda: "1/2" in text() and "Working tree  3 files" in text())
            until(lambda: 'return attempts' in text() and 'Bound retry attempts' in text())
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
            print("PASS: native fzf searches, narrows, resizes, toggles preview, and jumps to the selected worktree.")
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
