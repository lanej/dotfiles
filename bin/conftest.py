"""Shared fixtures for the feature regression detectors."""
import importlib.util
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import pytest


@pytest.fixture
def load_script(request):
    missing = object()
    registered = {}
    active = {}

    def restore_registered_modules():
        for name, module in registered.items():
            if module is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    request.addfinalizer(restore_registered_modules)

    def load(name, path=None, register=False):
        loader = SourceFileLoader(name.replace("-", "_"),
                                  str(path or Path(__file__).with_name(name)))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        previous = active.get(loader.name) if register else None
        template = importlib.util.module_from_spec(spec)
        app = previous
        if app is None:
            app = template
        else:
            for attribute in ("__loader__", "__spec__", "__file__", "__cached__",
                              "__package__", "__path__"):
                if attribute in template.__dict__:
                    setattr(app, attribute, getattr(template, attribute))
                else:
                    app.__dict__.pop(attribute, None)
        if register:
            registered.setdefault(loader.name, sys.modules.get(loader.name, missing))
            active[loader.name] = app
            sys.modules[loader.name] = app
        try:
            loader.exec_module(app)
        except BaseException:
            if register and previous is None:
                active.pop(loader.name, None)
                original = registered[loader.name]
                if original is missing:
                    sys.modules.pop(loader.name, None)
                else:
                    sys.modules[loader.name] = original
            raise
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
        env = {k: v for k, v in os.environ.items()
               if k not in ("TMUX", "TMUX_PANE") and not k.startswith("PASEO_")}
        for key in tuple(os.environ):
            if key.startswith("PASEO_"):
                monkeypatch.delenv(key)

        def call(*args):
            return subprocess.run(["tmux", "-S", socket, *args], env=env,
                                  check=True, capture_output=True, text=True,
                                  timeout=5).stdout.strip()

        pane = call("-f", "/dev/null", "new-session", "-d", "-s", "main",
                    "-n", "keep", "-P", "-F", "#{pane_id}", "sleep 300")
        monkeypatch.setenv("TMUX", f"{socket},1,0")
        monkeypatch.setenv("TMUX_PANE", pane)
        cleanup = []
        try:
            yield SimpleNamespace(folder=folder, socket=socket, call=call, pane=pane,
                                  cleanup=cleanup)
        finally:
            for fn in reversed(cleanup):
                fn()
            subprocess.run(["tmux", "-S", socket, "kill-server"], env=env,
                           capture_output=True, timeout=5)
