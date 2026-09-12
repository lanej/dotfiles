"""Shared fixtures for the feature regression detectors."""
import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace

import pytest


@pytest.fixture
def load_script():
    def load(name):
        loader = SourceFileLoader(name.replace("-", "_"), str(Path(__file__).with_name(name)))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        app = importlib.util.module_from_spec(spec)
        loader.exec_module(app)
        return app
    return load


@pytest.fixture
def private_tmux(monkeypatch):
    if not shutil.which("tmux"):
        if os.environ.get("REQUIRE_TMUX_TESTS") == "1":
            pytest.fail("tmux is required for the feature regression detectors")
        pytest.skip("tmux is not installed")
    # Short paths fit macOS socket limits; an empty config isolates user hooks.
    with tempfile.TemporaryDirectory(prefix="claude-test-", dir="/tmp") as directory:
        folder = Path(directory)
        socket = str(folder / "tmux.sock")
        env = {k: v for k, v in os.environ.items() if k not in ("TMUX", "TMUX_PANE")}

        def call(*args):
            return subprocess.run(["tmux", "-S", socket, *args], env=env,
                                  check=True, capture_output=True, text=True,
                                  timeout=5).stdout.strip()

        pane = call("-f", "/dev/null", "new-session", "-d", "-s", "main",
                    "-n", "keep", "-P", "-F", "#{pane_id}", "sleep 300")
        monkeypatch.setenv("TMUX", f"{socket},1,0")
        monkeypatch.setenv("TMUX_PANE", pane)
        try:
            yield SimpleNamespace(folder=folder, socket=socket, call=call, pane=pane)
        finally:
            subprocess.run(["tmux", "-S", socket, "kill-server"], env=env,
                           capture_output=True, timeout=5)
