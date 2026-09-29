"""One regression detector for the ~/.claude.json stale-project pruner.

Covers, against one shared fixture set:
  (a) never-existed path -> recorded as newly missing, no claude calls
  (b) stale path past threshold -> purged (dry-run capture + real purge + log + state cleared)
  (c) reappeared path -> state cleared, no claude calls
  (d) inconclusive (permission-denied) path -> untouched entirely
  (e) large gap since last check -> streak resets instead of carrying a stale day-count through

Plus two dedicated detectors for the delta-based circuit breaker (distinct
from the day-to-day classify/purge decisions above — a cumulative-ratio
breaker can't tell "one big pre-existing backlog" apart from "something
just broke", so it's scoped to NEWLY-missing paths since the last run):
  (f) cold start (no tracked history yet) bypasses the breaker entirely
  (g) a warm run (history exists) still trips on a burst of new missing paths
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent


def _days_ago(days):
    return int(time.time()) - days * 86400


def _build_executables(tmp_path, calls_log):
    """Fully-replaced PATH dir: real jq/bash/stat/coreutils plus a fake `claude`
    that logs every invocation to calls_log and no-ops `project purge`."""
    executables = tmp_path / "bin"
    executables.mkdir()
    (executables / "python3").symlink_to(sys.executable)
    for tool in ("jq", "bash", "stat", "mkdir", "mv", "mktemp", "date", "rmdir", "cut"):
        resolved = shutil.which(tool)
        assert resolved, f"{tool} must be resolvable on PATH to run this test"
        (executables / tool).symlink_to(resolved)
    (executables / "claude-json-prune").symlink_to(ROOT / "bin/claude-json-prune")

    calls_log.write_text("")
    cli = executables / "claude"
    cli.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
with open(os.environ["TEST_CLAUDE_CALLS"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1:3] == ["project", "purge"]:
    sys.exit(0)
sys.exit(1)
''')
    cli.chmod(0o755)
    return executables


def _run(executables, env_overrides, cwd):
    env = dict(os.environ, PATH=str(executables), **env_overrides)
    return subprocess.run(
        [str(executables / "claude-json-prune")],
        env=env, cwd=str(cwd), capture_output=True, text=True, timeout=30,
    )


def test_claude_json_prune_classifies_and_purges_correctly(tmp_path):
    calls_log = tmp_path / "claude-calls.jsonl"
    executables = _build_executables(tmp_path, calls_log)

    projects_dir = tmp_path / "projects"
    never_existed = projects_dir / "never-existed"
    stale_ready = projects_dir / "stale-ready"
    reappeared = projects_dir / "reappeared"
    reappeared.mkdir(parents=True)
    gap_reset = projects_dir / "gap-reset"
    inconclusive_parent = projects_dir / "locked-parent"
    inconclusive_parent.mkdir(parents=True)
    inconclusive_child = inconclusive_parent / "child"

    # Dilute the missing/inconclusive ratio below the circuit breaker's 50%
    # threshold so this run's real assertions aren't aborted by it.
    dummy_existing = []
    for i in range(5):
        d = projects_dir / f"dummy-exists-{i}"
        d.mkdir()
        dummy_existing.append(d)

    claude_json = tmp_path / "claude.json"
    projects = {
        str(never_existed): {},
        str(stale_ready): {},
        str(reappeared): {},
        str(gap_reset): {},
        str(inconclusive_child): {},
    }
    for d in dummy_existing:
        projects[str(d)] = {}
    claude_json.write_text(json.dumps({"projects": projects}))

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_file = state_dir / "state.json"
    purge_log = state_dir / "purge.log"
    state_file.write_text(json.dumps({
        "version": 1,
        "paths": {
            str(stale_ready): {
                "first_missing_epoch": _days_ago(15),
                "last_checked_epoch": _days_ago(1),
            },
            str(reappeared): {
                "first_missing_epoch": _days_ago(5),
                "last_checked_epoch": _days_ago(1),
            },
            str(gap_reset): {
                "first_missing_epoch": _days_ago(20),
                "last_checked_epoch": _days_ago(20),
            },
        },
    }))

    env_overrides = dict(
        CLAUDE_JSON_PRUNE_CLAUDE_JSON=str(claude_json),
        CLAUDE_JSON_PRUNE_STATE_DIR=str(state_dir),
        CLAUDE_JSON_PRUNE_LOG=str(purge_log),
        TEST_CLAUDE_CALLS=str(calls_log),
    )

    try:
        os.chmod(inconclusive_parent, 0o000)
        result = _run(executables, env_overrides, tmp_path)
    finally:
        os.chmod(inconclusive_parent, 0o755)

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"

    calls = [json.loads(line) for line in calls_log.read_text().splitlines() if line.strip()]
    state = json.loads(state_file.read_text())

    # (a) never-existed: recorded as newly missing, zero claude calls involving it
    assert str(never_existed) in state["paths"]
    assert "first_missing_epoch" in state["paths"][str(never_existed)]
    assert not any(str(never_existed) in c for c in calls)

    # (b) stale-ready: past threshold -> dry-run capture + real purge, logged, state cleared
    assert any(c[:2] == ["project", "purge"] and c[2] == str(stale_ready) and "--dry-run" in c
               for c in calls), calls
    assert any(c[:2] == ["project", "purge"] and c[2] == str(stale_ready) and "-y" in c
               for c in calls), calls
    assert str(stale_ready) in purge_log.read_text()
    assert str(stale_ready) not in state["paths"]

    # (c) reappeared: cleared from state, zero claude calls involving it
    assert str(reappeared) not in state["paths"]
    assert not any(str(reappeared) in c for c in calls)

    # (d) inconclusive: fully untouched — no state entry, no claude calls
    assert str(inconclusive_child) not in state["paths"]
    assert not any(str(inconclusive_child) in c for c in calls)

    # (e) large gap since last check: streak resets, not purged despite old first_missing_epoch
    assert str(gap_reset) in state["paths"]
    assert not any(str(gap_reset) in c for c in calls)
    now = int(time.time())
    assert now - state["paths"][str(gap_reset)]["first_missing_epoch"] < 3600


def test_claude_json_prune_cold_start_bypasses_circuit_breaker(tmp_path):
    """(f) A fresh install with no tracked history records its whole existing
    backlog on day 1 even when most projects are missing (a ratio that would
    trip a cumulative-count breaker) — nothing to compare "new" against yet."""
    calls_log = tmp_path / "claude-calls.jsonl"
    executables = _build_executables(tmp_path, calls_log)

    projects_dir = tmp_path / "projects"
    missing_paths = [projects_dir / f"missing-{i}" for i in range(3)]
    existing_path = projects_dir / "existing"
    existing_path.mkdir(parents=True)

    claude_json = tmp_path / "claude.json"
    claude_json.write_text(json.dumps({
        "projects": {str(p): {} for p in [*missing_paths, existing_path]},
    }))

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_file = state_dir / "state.json"
    purge_log = state_dir / "purge.log"
    state_file.write_text(json.dumps({"version": 1, "paths": {}}))

    env_overrides = dict(
        CLAUDE_JSON_PRUNE_CLAUDE_JSON=str(claude_json),
        CLAUDE_JSON_PRUNE_STATE_DIR=str(state_dir),
        CLAUDE_JSON_PRUNE_LOG=str(purge_log),
        TEST_CLAUDE_CALLS=str(calls_log),
    )
    result = _run(executables, env_overrides, tmp_path)

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    calls = [json.loads(line) for line in calls_log.read_text().splitlines() if line.strip()]
    state = json.loads(state_file.read_text())

    for p in missing_paths:
        assert str(p) in state["paths"], (p, state)
        assert "first_missing_epoch" in state["paths"][str(p)]
    assert not calls, calls  # nothing can have 14 days of history on a cold start


def test_claude_json_prune_warm_run_trips_on_new_missing_burst(tmp_path):
    """(g) With tracked history already present (not a cold start), a burst of
    paths that were fine as of the last run and are now all missing at once
    still trips the breaker — untouched state, no claude calls, logged."""
    calls_log = tmp_path / "claude-calls.jsonl"
    executables = _build_executables(tmp_path, calls_log)

    projects_dir = tmp_path / "projects"
    already_tracked_missing = projects_dir / "already-tracked-missing"
    burst_missing = [projects_dir / f"burst-missing-{i}" for i in range(3)]
    existing_path = projects_dir / "existing"
    existing_path.mkdir(parents=True)

    claude_json = tmp_path / "claude.json"
    claude_json.write_text(json.dumps({
        "projects": {
            str(p): {}
            for p in [already_tracked_missing, *burst_missing, existing_path]
        },
    }))

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    state_file = state_dir / "state.json"
    purge_log = state_dir / "purge.log"
    initial_state = {
        "version": 1,
        "paths": {
            str(already_tracked_missing): {
                "first_missing_epoch": _days_ago(3),
                "last_checked_epoch": _days_ago(1),
            },
        },
    }
    state_file.write_text(json.dumps(initial_state))
    state_bytes_before = state_file.read_bytes()

    env_overrides = dict(
        CLAUDE_JSON_PRUNE_CLAUDE_JSON=str(claude_json),
        CLAUDE_JSON_PRUNE_STATE_DIR=str(state_dir),
        CLAUDE_JSON_PRUNE_LOG=str(purge_log),
        TEST_CLAUDE_CALLS=str(calls_log),
    )
    # 3 newly-missing out of 5 total = 60% > 50% threshold; the one
    # pre-existing tracked-missing path does NOT count toward "new".
    result = _run(executables, env_overrides, tmp_path)

    assert result.returncode != 0
    assert state_file.read_bytes() == state_bytes_before
    calls = [json.loads(line) for line in calls_log.read_text().splitlines() if line.strip()]
    assert not calls, calls
    purge_log_text = purge_log.read_text() if purge_log.exists() else ""
    assert "circuit breaker" in purge_log_text.lower()
