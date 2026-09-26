"""Characterization test for bin/claude-session-start-hook's log_window_action().

Loaded from disk via importlib because the filename is not a valid Python
module name (same technique as claude-autoname-hook_test.py).
"""

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest


def _load(name, filename):
    path = Path(__file__).parent / filename
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load('claude_session_start_hook', 'claude-session-start-hook')


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path


def test_log_window_action_targets_own_pane_when_tmux_pane_set(fake_home, monkeypatch):
    # Without an explicit -t, tmux resolves "current" against whatever pane
    # the attached client happens to be looking at, not the pane the hook is
    # actually running in -- producing a diagnostic log that silently points
    # at the wrong window (or fails outright when no client is attached).
    monkeypatch.setenv('TMUX_PANE', '%7')
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='@1:main'))
    monkeypatch.setattr(hook.subprocess, 'run', mock_run)

    hook.log_window_action('test-action-xyz')

    assert call(
        ['tmux', 'display-message', '-p', '-t', '%7', '#{window_id}:#{window_name}'],
        capture_output=True, text=True, timeout=1,
    ) in mock_run.call_args_list
