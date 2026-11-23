# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte", "pillow"]
# ///
"""Exercise native Pi keyboard flows in owned PTYs and retain rendered screenshots."""
import argparse
import fcntl
import gzip
import json
import os
from pathlib import Path
import select
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import termios

import pyte
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
palette = json.loads((root / "resources/colors.json").read_text())
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix="pi-driver-terminal-") as directory:
    home = Path(directory).resolve()
    agent = home / ".pi/agent"
    agent.mkdir(parents=True)
    archive_file = agent / "session-archive.db"
    with sqlite3.connect(archive_file) as archive:
        archive.executescript("""
            CREATE TABLE sessions(id TEXT PRIMARY KEY, name TEXT, cwd TEXT, first_message TEXT, archived_at INTEGER);
            CREATE TABLE session_data(session_id TEXT PRIMARY KEY, jsonl_gzip BLOB);
            INSERT INTO sessions VALUES ('first', 'Archive run', '/fixture', 'Preserved dialogue', 2);
            INSERT INTO sessions VALUES ('second', 'Damaged entry', '/fixture', 'Failed to open', 1);
        """)
        body = json.dumps({"type": "message", "message": {"role": "user", "content": "Preserved dialogue"}})
        archive.executemany("INSERT INTO session_data VALUES (?, ?)", [("first", gzip.compress(body.encode())), ("second", b"corrupt")])
    archive.close()
    archive_before = archive_file.read_bytes()
    (agent / "models.json").write_text('{"providers":{"fixture":{"baseUrl":"http://127.0.0.1:9/v1","api":"openai-completions","apiKey":"fixture","models":[{"id":"tiny"}]}}}')
    workspace = home / "beads"
    workspace.mkdir()
    (workspace / ".beads").mkdir()
    (workspace / ".beads/metadata.json").write_text('{"dolt_mode":"server","dolt_database":"fixture"}')
    boundary = home / "bd"
    boundary.write_text('''#!/usr/bin/env python3
import json, sys
if '--readonly' not in sys.argv: raise SystemExit(31)
if 'sql' in sys.argv: print(json.dumps([{'branch':'main'}]))
elif 'list' in sys.argv: print(json.dumps([
    {'id':'daily-1','title':'Pi daily driver','status':'in_progress'},
    {'id':'daily-1.1','title':'Idle compaction','status':'open','parent':'daily-1'},
    {'id':'daily-1.1.1','title':'Check idle guard','status':'closed','parent':'daily-1.1'},
    {'id':'daily-1.2','title':'Deliver through Octo','status':'open','parent':'daily-1'},
]))
elif 'show' in sys.argv: print(json.dumps([{'id':sys.argv[-1],'title':'Idle compaction','status':'open','parent':'daily-1','description':'Compact settled sessions after five minutes and 60%.','acceptance_criteria':'Preserve drafts, task identity, and pending effects.'}]))
''')
    boundary.chmod(0o755)
    (home / "config.json").write_text(json.dumps({"beads": {"workspace": str(workspace), "database": "fixture", "branch": "main", "executable": str(boundary)}}))
    env = {**os.environ, "HOME": str(home), "PI_CODING_AGENT_DIR": str(agent), "PI_DRIVER_CONFIG": str(home / "config.json"), "TERM": "xterm-256color", "COLORTERM": "truecolor", "PI_TELEMETRY": "0", "PI_SKIP_VERSION_CHECK": "1"}
    subprocess.run([sys.executable, str(root / "scripts/configure.py"), str(root), str(agent)], env=env, check=True, stdout=subprocess.DEVNULL)
    (home / "design").mkdir()
    project = home / "development/dotfiles"
    project.mkdir(parents=True)
    def git(*args):
        subprocess.run(["git", *args], cwd=project, env=env, check=True, capture_output=True)
    git("init", "--initial-branch=main")
    tracked = project / "tracked.txt"
    tracked.write_text("old\nkeep\n")
    git("add", "tracked.txt")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-m", "fixture")
    tracked.write_text("new\nkeep\n")
    git("add", "tracked.txt")
    tracked.write_text("new\nkeep\nextra\n")
    (project / "untracked.txt").touch()
    directory_label = "~/dev/dotfiles" if shutil.which("shortpath") else "~/development/dotfiles"
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for columns, rows in [(100, 26), (60, 20)]:
        master, slave = os.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        process = subprocess.Popen(["bun", str(root / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"), "--offline", "--no-mcp", "--model", "fixture/tiny"], env=env, cwd=project, stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        screen = pyte.Screen(columns, rows)
        stream = pyte.Stream(screen)
        def pump(seconds):
            import time
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                if select.select([master], [], [], 0.05)[0]:
                    try:
                        stream.feed(os.read(master, 65536).decode("utf-8", errors="replace"))
                    except OSError:
                        break
        def capture(name):
            occupied = [y for y, line in enumerate(screen.display) if line.strip()]
            first = max(0, min(occupied) - 1)
            last = min(rows, max(occupied) + 2)
            image = Image.new("RGB", (columns * 9, (last - first) * 18), palette["roles"]["surface"])
            draw = ImageDraw.Draw(image)
            ansi_names = ["black", "red", "green", "brown", "blue", "magenta", "cyan", "white"]
            def color(value, fallback):
                if value == "default": return palette["roles"][fallback]
                if value in ansi_names: return palette["ansi"][ansi_names.index(value)]
                if len(value) == 6: return "#" + value
                return palette["roles"][fallback]
            for y in range(first, last):
                for x in range(columns):
                    cell = screen.buffer[y][x]
                    fg, bg = color(cell.fg, "text"), color(cell.bg, "surface")
                    if cell.reverse: fg, bg = bg, fg
                    top = (y - first) * 18
                    draw.rectangle((x * 9, top, (x + 1) * 9, top + 18), fill=bg)
                    draw.text((x * 9, top), cell.data, font=font, fill=fg)
            image.save(output / f"{name}-{columns}.png")
        try:
            pump(1)
            footer = next((line for line in screen.display if "tiny" in line and directory_label in line), "")
            assert footer and len(footer) == columns, screen.display
            assert "↱ main" in footer and "Δ1 +2 −1 ?1" in footer, screen.display
            os.write(master, b"/tasks\r")
            pump(1)
            assert any("→ ◐ daily-1" in line for line in screen.display), screen.display
            assert all(line.strip() != "Tasks" for line in screen.display), screen.display
            for noise in ["navigation", "Pi can explain", "[Extensions]", "[Extension issues]", "Warning: Extension", "idle compact", "escape/ctrl+c"]:
                assert noise not in "\n".join(screen.display), screen.display
            colors = {screen.buffer[y][x].fg.upper() for y in range(rows) for x in range(columns)}
            assert palette["roles"]["accent"].lstrip("#") in colors, colors
            progress = [(y, line.index("◐")) for y, line in enumerate(screen.display) if "◐" in line]
            opened = [(y, line.index("○")) for y, line in enumerate(screen.display) if "○" in line]
            assert progress and opened, screen.display
            for (y, x), tone in [(progress[0], "accent"), (opened[0], "text.muted")]:
                assert x >= columns // 4, screen.display
                assert screen.buffer[y][x].fg.upper() == palette["roles"][tone].lstrip("#"), screen.display
            assert any("├─ ○ daily-1.1" in line for line in screen.display), screen.display
            assert any("│  └─ ● daily-1.1.1" in line for line in screen.display), screen.display
            assert any("└─ ○ daily-1.2" in line for line in screen.display), screen.display
            capture("tasks")
            os.write(master, b"j\r")
            pump(.5)
            assert "Acceptance" in "\n".join(screen.display), screen.display
            assert "Read-only observation" not in "\n".join(screen.display)
            capture("task-details")
            os.write(master, b"\x1b")
            pump(.2)
            os.write(master, b"/archives\r")
            pump(.5)
            assert "Archive run" in "\n".join(screen.display), screen.display
            os.write(master, b"Archive run")
            pump(.2)
            assert "Damaged entry" not in "\n".join(screen.display), screen.display
            capture("archives")
            os.write(master, b"\r")
            pump(.5)
            assert "Preserved dialogue" in "\n".join(screen.display), screen.display
            capture("archive-preview")
            os.write(master, b"\x1b")
            pump(.35)
            os.write(master, b"\x1b")
            pump(.35)
            os.write(master, b"/archives Damaged\r")
            pump(.5)
            os.write(master, b"\r")
            pump(.5)
            assert "corrupt" in "\n".join(screen.display), screen.display
            os.write(master, b"\x1b")
            pump(.35)
            os.write(master, b"\x1b")
            pump(.35)
            assert archive_file.read_bytes() == archive_before
            os.write(master, b"!echo remember-cobalt\r")
            pump(.5)
            assert "remember-cobalt" in "\n".join(screen.display), screen.display
            os.write(master, b"/cd ../../design\r")
            pump(1)
            assert any("~/design" in line and "tiny" in line for line in screen.display), screen.display
            assert "remember-cobalt" in "\n".join(screen.display), screen.display
            capture("directory")
            os.write(master, b"/cd missing-directory\r")
            pump(.35)
            assert "ENOENT" in "\n".join(screen.display), screen.display
            assert any("~/design" in line and "tiny" in line for line in screen.display), screen.display
            os.write(master, b"unfinished instruction")
            pump(.2)
            assert "unfinished instruction" in "\n".join(screen.display)
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            os.close(master)
print("Native Pi tree selection, Escape recovery, directory switching, and draft editing passed.")
