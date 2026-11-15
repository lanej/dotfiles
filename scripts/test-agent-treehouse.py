#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets==15.0.1", "psutil==7.2.2"]
# ///
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("test-agent-worktree.py")), run_name="__main__")
