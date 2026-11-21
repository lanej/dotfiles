# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte", "pillow"]
# ///
"""Exercise native Pi keyboard flows in owned PTYs and retain rendered screenshots."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import select
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
palette = json.loads((root / "../../design-system/generated/colors.json").read_text())
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix="pi-driver-terminal-") as directory:
    home = Path(directory)
    agent = home / ".pi/agent"
    agent.mkdir(parents=True)
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
elif 'list' in sys.argv: print(json.dumps([{'id':'daily-1','title':'Pi daily driver','status':'in_progress'},{'id':'daily-1.1','title':'Idle compaction','status':'open','parent':'daily-1'}]))
elif 'show' in sys.argv: print(json.dumps([{'id':sys.argv[-1],'title':'Idle compaction','status':'open','parent':'daily-1','description':'Compact settled sessions after five minutes and 60%.','acceptance_criteria':'Preserve drafts, task identity, and pending effects.'}]))
''')
    boundary.chmod(0o755)
    (home / "config.json").write_text(json.dumps({"beads": {"workspace": str(workspace), "database": "fixture", "branch": "main", "executable": str(boundary)}}))
    env = {**os.environ, "HOME": str(home), "PI_CODING_AGENT_DIR": str(agent), "PI_DRIVER_CONFIG": str(home / "config.json"), "TERM": "xterm-256color", "COLORTERM": "truecolor", "PI_TELEMETRY": "0", "PI_SKIP_VERSION_CHECK": "1"}
    subprocess.run([sys.executable, str(root / "../../scripts/configure-pi-driver.py"), str(root), str(agent)], env=env, check=True, stdout=subprocess.DEVNULL)
    project = home / "dotfiles"
    project.mkdir()
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for columns, rows in [(100, 26), (60, 20)]:
        master, slave = os.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        process = subprocess.Popen(["node", str(root / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"), "--offline", "--no-mcp", "--no-session", "--model", "fixture/tiny"], env=env, cwd=project, stdin=slave, stdout=slave, stderr=slave)
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
            os.write(master, b"/tasks\r")
            pump(1)
            assert "daily-1" in "\n".join(screen.display), screen.display
            for noise in ["navigation", "Pi can explain", "[Extensions]", "[Extension issues]", "Warning: Extension", "idle compact", "escape/ctrl+c"]:
                assert noise not in "\n".join(screen.display), screen.display
            colors = {screen.buffer[y][x].fg.upper() for y in range(rows) for x in range(columns)}
            assert palette["roles"]["accent"].lstrip("#") in colors, colors
            backgrounds = {screen.buffer[y][x].bg.upper() for y in range(rows) for x in range(columns)}
            assert palette["roles"]["accent"].lstrip("#") in backgrounds, backgrounds
            assert palette["roles"]["text.muted"].lstrip("#") in backgrounds, backgrounds
            assert "IN PROGRESS" in "\n".join(screen.display) and "OPEN" in "\n".join(screen.display)
            capture("tasks")
            os.write(master, b"j\r")
            pump(.5)
            assert "Acceptance" in "\n".join(screen.display), screen.display
            assert "Read-only observation" not in "\n".join(screen.display)
            capture("task-details")
            os.write(master, b"\x1b")
            pump(.2)
            os.write(master, b"unfinished instruction")
            pump(.2)
            assert "unfinished instruction" in "\n".join(screen.display)
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            os.close(master)
print("Native Pi tree selection, Escape recovery, and draft editing passed.")
