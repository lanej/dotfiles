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
        projects = [home / "src" / f"{name}-{suffix}" for name in domains
                 for suffix in ("api", "cli", "dashboard", "docs", "jobs", "worker")]
        paths = [topic, *projects, repo, home / "release notes"]
        for path in paths:
            path.mkdir(exist_ok=True)
        billing = home / "src/billing-api"
        (billing / "invoices").mkdir()
        (billing / "reconciliation").mkdir()
        (billing / "invoices/ledger.py").touch()
        (billing / "pyproject.toml").write_text('[project]\nname = "billing-api"\n')
        (billing / "README.md").write_text("# Billing API\n\nIssue invoices and reconcile payments against the ledger.\n\n## Development\n\nRun the invoice checks before closing a billing period.\n")
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
            'chpwd_functions+=(record_directory)\nPS1="%1~ $ "\n')
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(repo)
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 38, 176, 0, 0))
            os.execvpe("zsh", ["zsh", "-d", "-i"], env)
        screen = native.NativeScreen(176, 38)
        stream, decoder = native.NativeStream(screen), codecs.getincrementaldecoder("utf-8")("replace")
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
        def panel(title):
            for i, row in enumerate(screen.display):
                if row.lstrip().startswith(title + " >"):
                    return screen.display[i:]
            return []
        def header(title):
            rows = panel(title)
            return rows[0] if rows else ""
        def underlines(label):
            for y, row in enumerate(screen.display):
                x = row.find(label)
                if x >= 0 and any(screen.buffer[y][x+i].underscore for i in range(len(label))):
                    return "".join(c for i, c in enumerate(label) if screen.buffer[y][x+i].underscore)
            return ""
        def capture(name, just_panel=False):
            # rationale: Drain asynchronous repaint output before recording terminal cells.
            quiet = time.monotonic() + .15
            while time.monotonic() < quiet:
                if select.select([fd], [], [], .03)[0]:
                    stream.feed(decoder.decode(os.read(fd, 65536)))
                    quiet = time.monotonic() + .15
            colors = {"default": "#D8DEE9", "black": "#3B4252", "red": "#BF616A", "green": "#A3BE8C", "brown": "#EBCB8B", "blue": "#81A1C1", "magenta": "#B48EAD", "cyan": "#88C0D0", "white": "#E5E9F0"}
            def color(value, fallback):
                return colors.get(value, "#" + value if len(value) == 6 else fallback)
            top = next(i for i, line in enumerate(screen.display) if line.lstrip().startswith(("Directories >", "Worktrees >"))) if just_panel else 0
            bottom = max(i for i, line in enumerate(screen.display) if line.strip()) + 1
            svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{screen.columns*9+24}" height="{(bottom-top)*20+24}">',
                   '<rect width="100%" height="100%" fill="#2E3440"/>',
                   '<g font-family="Hack Nerd Font Mono" font-size="14">']
            for row in range(top, bottom):
                for column in range(screen.columns):
                    cell = screen.buffer[row][column]
                    fg = color(cell.fg, "#D8DEE9")
                    bg = "#2E3440" if cell.bg == "default" else color(cell.bg, "#2E3440")
                    if cell.reverse:
                        fg, bg = bg, fg
                    x, y = column*9+12, (row-top)*20+12
                    if bg != "#2E3440":
                        svg.append(f'<rect x="{x}" y="{y}" width="9" height="20" fill="{bg}"/>')
                    if cell.underscore:
                        svg.append(f'<path d="M{x} {y+17}h9" stroke="{fg}"/>')
                    if cell.data.strip():
                        weight = "bold" if cell.bold else "normal"
                        svg.append(f'<text x="{x}" y="{y+15}" fill="{fg}" font-weight="{weight}">{html.escape(cell.data)}</text>')
            (destination / (name + ".svg")).write_text("".join([*svg, "</g></svg>\n"]))
        def resize(columns, lines):
            screen.resize(lines=lines, columns=columns)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0))
            os.killpg(pid, signal.SIGWINCH)
        try:
            until(lambda: any(row.rstrip().endswith(" $") for row in screen.display))
            os.write(fd, b"git status --short --branch\r")
            until(lambda: "## main" in text())
            os.write(fd, b"\x1bw")
            until(lambda: "2/2" in header("Worktrees") and "Working tree" in text())
            until(lambda: any("dirty 3" in row and "Codex" in row for row in panel("Worktrees")))
            capture("worktrees")
            assert "## main" in text(), "The picker took over the shell screen"
            os.write(fd, b"'Codex dirty")
            until(lambda: "1/2" in header("Worktrees") and "Working tree  3 files" in text())
            assert underlines("dirty 3") == "dirty" and underlines("Codex") == "Codex"
            os.write(fd, b"\x15")
            until(lambda: "2/2" in header("Worktrees"))
            os.write(fd, b"/pmt")
            until(lambda: "/pmt" in header("Worktrees") and "2/2" in header("Worktrees") and "return attempts" in text()
                  and "Codex" in text() and underlines("~/worktrees/payment-retries") == "/pmt")
            # The selection and the other result both show the actual fuzzy characters.
            assert underlines("~/worktrees/payment-retries") == "/pmt"
            assert underlines("~/src/payments") == "/pmt"
            panes = next(row for row in panel("Worktrees") if "README.md" in row and "payment-retries" in row and " │ " in row)
            assert panes.index(" │ ") < panes.index("README.md") < panes.rindex(" │ ") < panes.rindex("payment-retries"), panes
            for phrase in ("1 staged", "1 unstaged", "1 untracked", "src/main.py", "Recent commits",
                           "Retry failed payments", "src/retry.py", "NOTES.md"):
                assert phrase in text(), phrase
            recent = next(row for row in screen.display if "Bound retry attempts" in row)
            assert re.search(r"1 file\s+\+1\s+−1", recent), recent
            first = next(row for row in screen.display if "Retry payments" in row)
            assert re.search(r"2 files\s+\+3\s+−1", first), first
            if shutil.which("glow"):
                assert "```" not in text() and "# Payments" not in text(), "README Markdown was not rendered"
            assert "\uf418" in text() and r"\uf418" not in text()
            for attribute, value in (("bg", "a3be8c"), ("fg", "88c0d0"), ("bg", "434c5e"), ("fg", "ebcb8b")):
                assert any(getattr(cell, attribute) == value for row in screen.buffer.values() for cell in row.values()), value
            assert "ctrl-" not in text()
            capture("wide", just_panel=True)
            os.write(fd, b"\x15")
            until(lambda: "pmt" not in header("Worktrees"))
            os.write(fd, b"payment-retries")
            until(lambda: "1/2" in header("Worktrees") and "return attempts" in text())
            os.write(fd, b"\x00")
            until(lambda: "1/1" in header("Worktrees"))
            resize(80, 40)
            until(lambda: "return attempts" in text() and any("Working tree  3 files" in row for row in panel("Worktrees")[:8]))
            capture("tall")
            resize(80, 18)
            until(lambda: "preview 1-" in header("Worktrees") and "Working tree  3 files" in text())
            capture("compact")
            os.write(fd, b"\n" * 26)  # Ctrl-J scrolls past Git into the README.
            until(lambda: "return attempts" in text())
            os.write(fd, b"\x0b" * 26)
            until(lambda: "preview 1-" in header("Worktrees"))
            os.write(fd, b"\x1f")
            until(lambda: "Working tree" not in text() and "1/1" in header("Worktrees"))
            os.write(fd, b"\x1f")
            until(lambda: "Working tree  3 files" in text())
            os.write(fd, b"\r")
            until(lambda: result.exists() and result.read_text().strip() == str(topic))
            until(lambda: any(row.rstrip().endswith(" $") for row in screen.display) and not header("Worktrees"))
            result.unlink()
            resize(204, 54)
            os.write(fd, b"clear; git log -2 --oneline --stat --color=never; git status --short --branch\r")
            until(lambda: "## retry-payments" in text())
            os.write(fd, b"\x02")
            labels = ["~/" + str(path.relative_to(home)) for path in paths]
            until(lambda: "81/81" in header("Directories") and "return attempts" in text() and "attached" in text())
            rows = panel("Directories")
            assert all(any(label in row for row in rows) for label in labels)
            assert max(row.partition(" │ ")[0].count("~/") for row in rows) >= 3, rows[1]
            assert any("README.md" in row.partition(" │ ")[2].partition(" │ ")[0]
                       and "payment-retries" in row.rpartition(" │ ")[2] for row in rows), rows[1]
            assert "## retry-payments" in text()
            capture("history")
            os.write(fd, b"b")
            until(lambda: re.search(r"Directories > b\s+\d+/81", header("Directories")))
            os.write(fd, b"illing-")
            until(lambda: "6/81" in header("Directories") and "invoices/" in text() and "against the ledger" in text())
            capture("files", just_panel=True)
            assert underlines("~/src/billing-api") == "billing-"
            assert underlines("~/src/billing-worker") == "billing-"
            os.write(fd, b"\x0e")  # Ctrl-N picks billing-cli, an empty directory.
            until(lambda: "› ~/src/billing-cli" in text() and "Empty directory" in text() and "invoices/" not in text())
            rows = panel("Directories")
            assert rows[1].partition(" │ ")[0].count("billing-") == 6, rows[1]
            assert sum(bool(row.strip()) for row in rows) == 3, rows[:5]
            capture("filtered", just_panel=True)
            os.write(fd, b"\x15")
            until(lambda: "81/81" in header("Directories") and "› ~/src/billing-cli" in text())
            row = next(line for line in panel("Directories") if "› ~/src/billing-cli" in line)
            right = re.search(r"› ~/src/billing-cli\s+(~/\S+)", row)
            assert right, row
            destination_label = right[1]
            os.write(fd, b"\x1b[C")
            until(lambda: "› " + destination_label in text())
            resize(72, 18)
            until(lambda: "› " + destination_label in text() and "81/81" in header("Directories") and "Empty directory" in text())
            os.write(fd, b"\r")
            target = str(paths[labels.index(destination_label)])
            until(lambda: result.exists() and result.read_text().strip() == target)
            until(lambda: any(row.rstrip().endswith(" $") for row in screen.display) and not header("Directories"))
            os.write(fd, b'print -r -- "$PWD" > "$HOME/preserved"')
            os.write(fd, b"\x02")
            until(lambda: "81/81" in header("Directories") and "› " + labels[0] in text())
            os.write(fd, b"webhooks-jobs")
            until(lambda: "1/81" in header("Directories") and "webhooks-jobs" in header("Directories"))
            os.write(fd, b"\x1b")
            until(lambda: "preserved" in text() and not header("Directories"))
            assert not (home / "preserved").exists(), "Cancelled picker executed unfinished input"
            os.write(fd, b"\r")
            until(lambda: (home / "preserved").exists())
            assert (home / "preserved").read_text().strip() == target
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
