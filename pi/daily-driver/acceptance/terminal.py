# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte", "pillow"]
# ///
"""Exercise native Pi keyboard flows in owned PTYs and retain rendered screenshots."""
import argparse
import fcntl
import os
from pathlib import Path
import select
import struct
import subprocess
import tempfile
import termios

import pyte
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
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
    import json
    (home / "config.json").write_text(json.dumps({"beads": {"workspace": str(workspace), "database": "fixture", "branch": "main", "executable": str(boundary)}}))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for columns, rows in [(100, 26), (60, 20)]:
        master, slave = os.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        process = subprocess.Popen(["node", str(root / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"), "--offline", "--no-mcp", "--no-session", "--model", "fixture/tiny", "--extension", str(root / "extension.ts")], env={**os.environ, "HOME": str(home), "PI_CODING_AGENT_DIR": str(agent), "PI_DRIVER_CONFIG": str(home / "config.json"), "TERM": "xterm-256color", "PI_TELEMETRY": "0", "PI_SKIP_VERSION_CHECK": "1"}, cwd=home, stdin=slave, stdout=slave, stderr=slave)
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
        try:
            pump(1)
            os.write(master, b"/tasks\r")
            pump(1)
            assert "daily-1" in "\n".join(screen.display), screen.display
            image = Image.new("RGB", (columns * 9, rows * 18), "#1e222a")
            draw = ImageDraw.Draw(image)
            for y, line in enumerate(screen.display):
                draw.text((0, y * 18), line, font=font, fill="#d8dee9")
            image.save(output / f"tasks-{columns}.png")
            os.write(master, b"\x1b[B\r")
            pump(.5)
            assert "Acceptance" in "\n".join(screen.display), screen.display
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
