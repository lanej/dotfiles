"""Characterization tests for bin/claude-autoname-hook.

The hook is loaded from disk via importlib rather than imported normally,
because its filename (claude-autoname-hook) is not a valid Python module
name. It is loaded under a distinct name ('claude_autoname_hook'), not
'__main__' — loading it as '__main__' would make the module's own
`if __name__ == '__main__': main()` guard fire on load, running main()
(and blocking on stdin) as a side effect of importing it.
"""

import importlib.util
import io
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest


def _load(name, filename):
    # spec_from_file_location can't infer a loader for an extensionless
    # file (claude-autoname-hook has no .py suffix), so the loader is
    # supplied explicitly.
    path = Path(__file__).parent / filename
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load('claude_autoname_hook', 'claude-autoname-hook')


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Fake HOME so Path.home()-derived paths never touch the real filesystem."""
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# get_cwd()
# ---------------------------------------------------------------------------

def test_get_cwd_valid_transcript_returns_cwd(tmp_path):
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(json.dumps({'cwd': '/some/project'}) + '\n')

    assert hook.get_cwd(str(transcript)) == '/some/project'


def test_get_cwd_returns_first_line_with_cwd_key_when_multiple(tmp_path):
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(
        json.dumps({'cwd': '/first'}) + '\n' +
        json.dumps({'cwd': '/second'}) + '\n'
    )

    assert hook.get_cwd(str(transcript)) == '/first'


def test_get_cwd_skips_malformed_json_line_still_finds_later_valid(tmp_path):
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(
        'not valid json {\n' +
        json.dumps({'cwd': '/valid'}) + '\n'
    )

    assert hook.get_cwd(str(transcript)) == '/valid'


def test_get_cwd_non_dict_json_line_aborts_scan(tmp_path):
    # A line that parses to valid JSON but isn't a dict (e.g. a list) makes
    # `.get('cwd')` raise AttributeError. That's not a json.JSONDecodeError,
    # so the inner except doesn't catch it — it propagates to the outer
    # `except Exception`, which aborts the *entire* scan and returns None,
    # rather than skipping just that one line.
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(
        json.dumps([1, 2]) + '\n' +
        json.dumps({'cwd': '/valid'}) + '\n'
    )

    assert hook.get_cwd(str(transcript)) is None


def test_get_cwd_empty_string_is_falsy_loop_continues_past_it(tmp_path):
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(
        json.dumps({'cwd': ''}) + '\n' +
        json.dumps({'cwd': '/real'}) + '\n'
    )

    assert hook.get_cwd(str(transcript)) == '/real'


def test_get_cwd_missing_file_returns_none(tmp_path):
    missing = tmp_path / 'does-not-exist.jsonl'

    assert hook.get_cwd(str(missing)) is None


def test_get_cwd_file_with_no_valid_lines_returns_none(tmp_path):
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text('not json\n\nalso not json\n')

    assert hook.get_cwd(str(transcript)) is None


# ---------------------------------------------------------------------------
# log_window_action()
# ---------------------------------------------------------------------------

def test_log_window_action_writes_to_fake_home_log(fake_home, monkeypatch):
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='@1:main'))
    monkeypatch.setattr(hook.subprocess, 'run', mock_run)

    hook.log_window_action('test-action-xyz')

    logfile = fake_home / '.claude' / 'logs' / 'window-naming.log'
    assert logfile.exists()
    assert 'test-action-xyz' in logfile.read_text()


# ---------------------------------------------------------------------------
# set_title()
# ---------------------------------------------------------------------------

def test_set_title_tmux_set_pane_set_renames_window_and_sets_option(fake_home, monkeypatch):
    monkeypatch.setenv('TMUX', '/tmp/tmux-501/default,1234,0')
    monkeypatch.setenv('TMUX_PANE', '%3')
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout=''))
    monkeypatch.setattr(hook.subprocess, 'run', mock_run)

    hook.set_title('myproject')

    display_name = f'{hook.GLYPH} myproject'
    # log_window_action fires its own 'tmux display-message' call first, so
    # exact call_args_list equality would be wrong — assert containment.
    assert call(['tmux', 'rename-window', '-t', '%3', display_name], check=False) \
        in mock_run.call_args_list
    assert call(['tmux', 'set-option', '-w', '-t', '%3', '@claude_named', display_name], check=False) \
        in mock_run.call_args_list


def test_set_title_tmux_set_pane_empty_uses_bare_commands(fake_home, monkeypatch):
    monkeypatch.setenv('TMUX', '/tmp/tmux-501/default,1234,0')
    monkeypatch.setenv('TMUX_PANE', '')
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout=''))
    monkeypatch.setattr(hook.subprocess, 'run', mock_run)

    hook.set_title('myproject')

    display_name = f'{hook.GLYPH} myproject'
    assert call(['tmux', 'rename-window', display_name], check=False) \
        in mock_run.call_args_list
    assert call(['tmux', 'set-option', '-w', '@claude_named', display_name], check=False) \
        in mock_run.call_args_list


def test_set_title_no_tmux_writes_to_dev_tty(fake_home, monkeypatch):
    monkeypatch.delenv('TMUX', raising=False)
    monkeypatch.delenv('TMUX_PANE', raising=False)

    class FakeTTY:
        def __init__(self):
            self.written = []

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def write(self, data):
            self.written.append(data)

    fake_tty = FakeTTY()
    opened_paths = []

    def fake_open(path, mode='r', *args, **kwargs):
        # Don't assert here: set_title's no-tmux branch wraps this call in
        # try/except Exception: pass, so an AssertionError raised inside
        # this fake would be silently swallowed, producing a false pass.
        # Record instead, and assert after set_title() returns.
        opened_paths.append(path)
        return fake_tty

    monkeypatch.setattr(hook, 'open', fake_open, raising=False)

    hook.set_title('myproject')

    display_name = f'{hook.GLYPH} myproject'
    assert opened_paths == ['/dev/tty']
    assert fake_tty.written == [f'\033]0;{display_name}\007']


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def _set_stdin(monkeypatch, payload_str):
    monkeypatch.setattr(sys, 'stdin', io.StringIO(payload_str))


def _names_dir(fake_home):
    return fake_home / '.claude' / 'session-names'


def test_main_malformed_stdin_exits_zero_no_file_written(fake_home, monkeypatch):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)
    _set_stdin(monkeypatch, 'not json at all')

    with pytest.raises(SystemExit) as exc_info:
        hook.main()

    assert exc_info.value.code == 0
    assert not _names_dir(fake_home).exists()
    mock_set_title.assert_not_called()


def test_main_missing_session_id_exits_zero_no_file_written(fake_home, monkeypatch, tmp_path):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(json.dumps({'cwd': '/some/project'}) + '\n')
    _set_stdin(monkeypatch, json.dumps({'transcript_path': str(transcript)}))

    with pytest.raises(SystemExit) as exc_info:
        hook.main()

    assert exc_info.value.code == 0
    assert not _names_dir(fake_home).exists()
    mock_set_title.assert_not_called()


def test_main_missing_transcript_path_exits_zero_no_file_written(fake_home, monkeypatch):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)
    _set_stdin(monkeypatch, json.dumps({'session_id': 'abc123'}))

    with pytest.raises(SystemExit) as exc_info:
        hook.main()

    assert exc_info.value.code == 0
    assert not _names_dir(fake_home).exists()
    mock_set_title.assert_not_called()


def test_main_transcript_path_missing_on_disk_exits_zero_no_file_written(fake_home, monkeypatch, tmp_path):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)
    missing_transcript = tmp_path / 'does-not-exist.jsonl'
    _set_stdin(monkeypatch, json.dumps({
        'session_id': 'abc123',
        'transcript_path': str(missing_transcript),
    }))

    with pytest.raises(SystemExit) as exc_info:
        hook.main()

    assert exc_info.value.code == 0
    assert not _names_dir(fake_home).exists()
    mock_set_title.assert_not_called()


def test_main_transcript_with_no_cwd_line_exits_zero_no_file_set_title_not_called(fake_home, monkeypatch, tmp_path):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(json.dumps({'other': 'value'}) + '\n')
    _set_stdin(monkeypatch, json.dumps({
        'session_id': 'abc123',
        'transcript_path': str(transcript),
    }))

    with pytest.raises(SystemExit) as exc_info:
        hook.main()

    assert exc_info.value.code == 0
    assert not _names_dir(fake_home).exists()
    mock_set_title.assert_not_called()


def test_main_existing_name_file_calls_set_title_with_contents_no_new_derivation(fake_home, monkeypatch, tmp_path):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)

    names_dir = _names_dir(fake_home)
    names_dir.mkdir(parents=True)
    name_file = names_dir / 'abc123'
    name_file.write_text('existing-name')

    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(json.dumps({'cwd': '/some/other/project'}) + '\n')
    _set_stdin(monkeypatch, json.dumps({
        'session_id': 'abc123',
        'transcript_path': str(transcript),
    }))

    with pytest.raises(SystemExit) as exc_info:
        hook.main()

    assert exc_info.value.code == 0
    mock_set_title.assert_called_once_with('existing-name')
    # No new derivation from the transcript's cwd.
    assert name_file.read_text() == 'existing-name'


def test_main_no_name_file_real_cwd_creates_name_file_and_calls_set_title(fake_home, monkeypatch, tmp_path):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)

    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text(json.dumps({'cwd': '/Users/someone/projects/myrepo'}) + '\n')
    _set_stdin(monkeypatch, json.dumps({
        'session_id': 'abc123',
        'transcript_path': str(transcript),
    }))

    hook.main()

    name_file = _names_dir(fake_home) / 'abc123'
    assert name_file.exists()
    assert name_file.read_text() == 'myrepo'
    mock_set_title.assert_called_once_with('myrepo')


def test_main_cwd_under_fake_home_dot_claude_is_skipped(fake_home, monkeypatch, tmp_path):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)

    transcript = tmp_path / 'transcript.jsonl'
    internal_cwd = str(fake_home / '.claude' / 'session-names')
    transcript.write_text(json.dumps({'cwd': internal_cwd}) + '\n')
    _set_stdin(monkeypatch, json.dumps({
        'session_id': 'abc123',
        'transcript_path': str(transcript),
    }))

    with pytest.raises(SystemExit) as exc_info:
        hook.main()

    assert exc_info.value.code == 0
    assert not _names_dir(fake_home).exists()
    mock_set_title.assert_not_called()


def test_main_cwd_under_fake_home_dot_claude_mem_is_skipped(fake_home, monkeypatch, tmp_path):
    mock_set_title = MagicMock()
    monkeypatch.setattr(hook, 'set_title', mock_set_title)

    transcript = tmp_path / 'transcript.jsonl'
    internal_cwd = str(fake_home / '.claude-mem' / 'observer-sessions' / 'foo')
    transcript.write_text(json.dumps({'cwd': internal_cwd}) + '\n')
    _set_stdin(monkeypatch, json.dumps({
        'session_id': 'abc123',
        'transcript_path': str(transcript),
    }))

    with pytest.raises(SystemExit) as exc_info:
        hook.main()

    assert exc_info.value.code == 0
    assert not _names_dir(fake_home).exists()
    mock_set_title.assert_not_called()
