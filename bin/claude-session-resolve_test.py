"""Tests for bin/claude-session-resolve.

Loaded from disk via importlib rather than imported normally, because its
filename (claude-session-resolve) is not a valid Python module name. It is
loaded under a distinct name ('claude_session_resolve'), not '__main__' —
loading it as '__main__' would make the module's own
`if __name__ == '__main__': main()` guard fire on load, running main() as a
side effect of importing it.
"""

import importlib.util
import os
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _load(name, filename):
    # spec_from_file_location can't infer a loader for an extensionless
    # file (claude-session-resolve has no .py suffix), so the loader is
    # supplied explicitly.
    path = Path(__file__).parent / filename
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resolver = _load('claude_session_resolve', 'claude-session-resolve')


# ---------------------------------------------------------------------------
# encode_cwd_to_project_dir()
# ---------------------------------------------------------------------------

def test_encode_cwd_regression_2026_08_07():
    assert resolver.encode_cwd_to_project_dir('/Users/joshlane/.files') == '-Users-joshlane--files'


def test_encode_cwd_name_md_comment_example():
    assert resolver.encode_cwd_to_project_dir('/Users/josh/.files') == '-Users-josh--files'


def test_encode_cwd_dot_free_path_no_spurious_double_dash():
    assert resolver.encode_cwd_to_project_dir('/Users/josh/src/project') == '-Users-josh-src-project'


def _broken_encode_2026_08_07(cwd):
    """Reference reproduction of the original bug: strip leading dash, skip dots.

    Equivalent to `sed 's|/|-|g; s|^-||'` — only `/` gets replaced, and the
    leading dash produced by the leading `/` is stripped. This is the
    original incident's encoding, kept here permanently (not as a
    mutate-and-restore step on the real function) so the regression is
    diff-visible forever: if someone "simplifies" encode_cwd_to_project_dir
    back toward this shape, this test fails immediately.
    """
    return cwd.replace('/', '-').lstrip('-')


def test_encode_cwd_regression_2026_08_07_broken_reference_produces_wrong_value():
    cwd = '/Users/joshlane/.files'
    assert _broken_encode_2026_08_07(cwd) == 'Users-joshlane-.files'
    assert resolver.encode_cwd_to_project_dir(cwd) == '-Users-joshlane--files'
    assert _broken_encode_2026_08_07(cwd) != resolver.encode_cwd_to_project_dir(cwd)


# ---------------------------------------------------------------------------
# project_dir_for_cwd()
# ---------------------------------------------------------------------------

def test_project_dir_for_cwd(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    result = resolver.project_dir_for_cwd('/Users/joshlane/.files')
    assert result == tmp_path / '.claude' / 'projects' / '-Users-joshlane--files'


# ---------------------------------------------------------------------------
# session_id_from_tmux_pane_option()
# ---------------------------------------------------------------------------

def test_session_id_from_tmux_pane_option_found(monkeypatch):
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout='abc123\n'))
    monkeypatch.setattr(resolver.subprocess, 'run', mock_run)

    assert resolver.session_id_from_tmux_pane_option('%3') == 'abc123'


def test_session_id_from_tmux_pane_option_empty_stdout(monkeypatch):
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout=''))
    monkeypatch.setattr(resolver.subprocess, 'run', mock_run)

    assert resolver.session_id_from_tmux_pane_option('%3') is None


def test_session_id_from_tmux_pane_option_empty_pane_never_calls_subprocess(monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr(resolver.subprocess, 'run', mock_run)

    assert resolver.session_id_from_tmux_pane_option('') is None
    assert mock_run.call_count == 0


def test_session_id_from_tmux_pane_option_subprocess_raises_returns_none(monkeypatch):
    def raise_error(*args, **kwargs):
        raise subprocess.SubprocessError('boom')

    monkeypatch.setattr(resolver.subprocess, 'run', raise_error)

    assert resolver.session_id_from_tmux_pane_option('%3') is None


# ---------------------------------------------------------------------------
# newest_jsonl()
# ---------------------------------------------------------------------------

def test_newest_jsonl_picks_latest_mtime(tmp_path):
    older = tmp_path / 'older.jsonl'
    newer = tmp_path / 'newer.jsonl'
    older.write_text('{}')
    newer.write_text('{}')
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    assert resolver.newest_jsonl([older, newer]) == newer


def test_newest_jsonl_empty_iterable_returns_none():
    assert resolver.newest_jsonl([]) is None


def test_newest_jsonl_filters_nonexistent_paths(tmp_path):
    missing = tmp_path / 'missing.jsonl'
    assert resolver.newest_jsonl([missing]) is None


# ---------------------------------------------------------------------------
# newest_transcript_in_dir()
# ---------------------------------------------------------------------------

def test_newest_transcript_in_dir_picks_latest_mtime(tmp_path):
    project_dir = tmp_path / 'project'
    project_dir.mkdir()
    older = project_dir / 'session-a.jsonl'
    newer = project_dir / 'session-b.jsonl'
    older.write_text('{}')
    newer.write_text('{}')
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    assert resolver.newest_transcript_in_dir(project_dir) == newer


def test_newest_transcript_in_dir_empty_dir_returns_none(tmp_path):
    project_dir = tmp_path / 'project'
    project_dir.mkdir()

    assert resolver.newest_transcript_in_dir(project_dir) is None


def test_newest_transcript_in_dir_missing_dir_returns_none(tmp_path):
    project_dir = tmp_path / 'does-not-exist'

    assert resolver.newest_transcript_in_dir(project_dir) is None


# ---------------------------------------------------------------------------
# newest_transcript_cross_project()
# ---------------------------------------------------------------------------

def _fake_projects_home(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    projects_dir = tmp_path / '.claude' / 'projects'
    projects_dir.mkdir(parents=True)
    return projects_dir


def test_newest_transcript_cross_project_picks_newest_across_subdirs(monkeypatch, tmp_path):
    projects_dir = _fake_projects_home(monkeypatch, tmp_path)
    proj_a = projects_dir / 'proj-a'
    proj_b = projects_dir / 'proj-b'
    proj_a.mkdir()
    proj_b.mkdir()
    older = proj_a / 'older.jsonl'
    newer = proj_b / 'newer.jsonl'
    older.write_text('{}')
    newer.write_text('{}')
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    assert resolver.newest_transcript_cross_project() == newer


def test_newest_transcript_cross_project_missing_projects_dir_returns_none(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    # Deliberately do not create ~/.claude/projects.

    assert resolver.newest_transcript_cross_project() is None


def test_newest_transcript_cross_project_does_not_match_nested_two_levels_deep(monkeypatch, tmp_path):
    projects_dir = _fake_projects_home(monkeypatch, tmp_path)
    nested = projects_dir / 'proj-a' / 'nested'
    nested.mkdir(parents=True)
    deep_file = nested / 'deep.jsonl'
    deep_file.write_text('{}')
    os.utime(deep_file, (5000, 5000))

    # The single-level glob ('*/*.jsonl') must not reach two levels deep.
    assert resolver.newest_transcript_cross_project() is None


# ---------------------------------------------------------------------------
# resolve_session()
# ---------------------------------------------------------------------------

def _setup_cwd_and_home(monkeypatch, tmp_path, cwd):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('PWD', cwd)


def test_resolve_session_pane_lookup_succeeds_no_fallback(monkeypatch, tmp_path):
    cwd = '/some/project'
    _setup_cwd_and_home(monkeypatch, tmp_path, cwd)
    project_dir = resolver.project_dir_for_cwd(cwd)
    project_dir.mkdir(parents=True)
    transcript = project_dir / 'session-a.jsonl'
    transcript.write_text('{}')

    monkeypatch.setattr(resolver, 'session_id_from_tmux_pane_option', lambda pane: 'session-a')

    mock_newest_in_dir = MagicMock(side_effect=AssertionError('fallback should not be consulted'))
    monkeypatch.setattr(resolver, 'newest_transcript_in_dir', mock_newest_in_dir)

    assert resolver.resolve_session() == ('session-a', transcript)


def test_resolve_session_pane_empty_falls_back_to_same_dir_newest(monkeypatch, tmp_path):
    cwd = '/some/project'
    _setup_cwd_and_home(monkeypatch, tmp_path, cwd)
    project_dir = resolver.project_dir_for_cwd(cwd)
    project_dir.mkdir(parents=True)
    older = project_dir / 'session-old.jsonl'
    newer = project_dir / 'session-new.jsonl'
    older.write_text('{}')
    newer.write_text('{}')
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    monkeypatch.setattr(resolver, 'session_id_from_tmux_pane_option', lambda pane: None)

    assert resolver.resolve_session() == ('session-new', newer)


def test_resolve_session_same_dir_empty_falls_back_to_cross_project(monkeypatch, tmp_path):
    cwd = '/some/project'
    _setup_cwd_and_home(monkeypatch, tmp_path, cwd)
    project_dir = resolver.project_dir_for_cwd(cwd)
    project_dir.mkdir(parents=True)  # exists but empty

    other_proj = tmp_path / '.claude' / 'projects' / 'other-project'
    other_proj.mkdir(parents=True)
    cross = other_proj / 'session-cross.jsonl'
    cross.write_text('{}')

    monkeypatch.setattr(resolver, 'session_id_from_tmux_pane_option', lambda pane: None)

    assert resolver.resolve_session() == ('session-cross', cross)


def test_resolve_session_pane_stale_session_id_falls_through_to_cross_project(monkeypatch, tmp_path):
    """The easy-to-drop clause: a pane-reported session_id whose transcript
    file doesn't exist on disk must still fall through to the cross-project
    search, not just fail outright."""
    cwd = '/some/project'
    _setup_cwd_and_home(monkeypatch, tmp_path, cwd)
    project_dir = resolver.project_dir_for_cwd(cwd)
    project_dir.mkdir(parents=True)
    # No file named 'stale-session.jsonl' exists in project_dir.

    other_proj = tmp_path / '.claude' / 'projects' / 'other-project'
    other_proj.mkdir(parents=True)
    cross = other_proj / 'session-cross.jsonl'
    cross.write_text('{}')

    monkeypatch.setattr(resolver, 'session_id_from_tmux_pane_option', lambda pane: 'stale-session')

    assert resolver.resolve_session() == ('session-cross', cross)


def test_resolve_session_nothing_resolvable_returns_none_none(monkeypatch, tmp_path):
    cwd = '/some/project'
    _setup_cwd_and_home(monkeypatch, tmp_path, cwd)
    # Don't create project_dir or ~/.claude/projects at all.

    monkeypatch.setattr(resolver, 'session_id_from_tmux_pane_option', lambda pane: None)

    assert resolver.resolve_session() == (None, None)


def test_resolve_session_regression_2026_08_07_race(monkeypatch, tmp_path):
    """The other half of the 2026-08-07 incident: when two sessions share a
    cwd, the pane option (authoritative) must win over a same-dir
    newest-mtime race, even when the pane's session is the *older* file.

    Without this test, an implementation that consults
    newest_transcript_in_dir() before (or instead of) the pane option would
    still pass every other test in this file, because none of them pit an
    older pane-reported session against a newer same-dir file.
    """
    cwd = '/some/project'
    _setup_cwd_and_home(monkeypatch, tmp_path, cwd)
    project_dir = resolver.project_dir_for_cwd(cwd)
    project_dir.mkdir(parents=True)

    session_a = project_dir / 'session-a.jsonl'  # older, pane-reported
    session_b = project_dir / 'session-b.jsonl'  # newer, would win an ls -t race
    session_a.write_text('{}')
    session_b.write_text('{}')
    os.utime(session_a, (1000, 1000))
    os.utime(session_b, (2000, 2000))

    monkeypatch.setattr(resolver, 'session_id_from_tmux_pane_option', lambda pane: 'session-a')

    assert resolver.resolve_session() == ('session-a', session_a)


def test_resolve_session_uses_pwd_symlink_not_getcwd_resolved_target(monkeypatch, tmp_path):
    real_dir = tmp_path / 'real-target'
    real_dir.mkdir()
    symlink_dir = tmp_path / 'symlinked-cwd'
    symlink_dir.symlink_to(real_dir)

    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('PWD', str(symlink_dir))
    monkeypatch.chdir(real_dir)

    # Sanity: PWD (logical) and os.getcwd() (physical) actually diverge here.
    assert str(symlink_dir) != os.getcwd()

    symlink_project_dir = resolver.project_dir_for_cwd(str(symlink_dir))
    symlink_project_dir.mkdir(parents=True)
    transcript = symlink_project_dir / 'session-symlink.jsonl'
    transcript.write_text('{}')

    monkeypatch.setattr(resolver, 'session_id_from_tmux_pane_option', lambda pane: None)

    assert resolver.resolve_session() == ('session-symlink', transcript)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def test_main_success_prints_exact_two_lines_exit_zero(monkeypatch, capsys):
    monkeypatch.setattr(
        resolver, 'resolve_session',
        lambda: ('abc 123', Path('/tmp/some dir/abc 123.jsonl'))
    )

    resolver.main()

    captured = capsys.readouterr()
    assert captured.out == (
        "SESSION_ID='abc 123'\n"
        "TRANSCRIPT_PATH='/tmp/some dir/abc 123.jsonl'\n"
    )
    assert captured.err == ''


def test_main_failure_empty_stdout_exit_one(monkeypatch, capsys):
    monkeypatch.setattr(resolver, 'resolve_session', lambda: (None, None))

    with pytest.raises(SystemExit) as exc_info:
        resolver.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ''
