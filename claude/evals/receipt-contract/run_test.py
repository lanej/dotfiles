"""Exercise the receipt measurement boundary without invoking a model."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "claude/evals/receipt-contract/run.sh"


@pytest.fixture
def run_trial(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    timeout = bindir / "timeout"
    timeout.write_text('#!/bin/bash\nshift\nexec "$@"\n')
    timeout.chmod(0o755)
    claude = bindir / "claude"
    claude.write_text(f"#!{sys.executable}\n" + '''
import os, re, sys
from pathlib import Path
mode = os.environ.get("STUB_MODE", "ok")
if mode == "fail":
    print("simulated failure", file=sys.stderr)
    sys.exit(17)
if mode == "empty":
    sys.exit(0)
prompt = sys.argv[sys.argv.index("-p") + 1]
match = re.search(r"Write your full findings to (.+)", prompt)
if match:
    path = Path(match.group(1))
    if mode != "missing":
        path.write_text("Findings — preserved.\\n")
    reported = str(path) if mode != "wrong_path" else str(path) + ".wrong"
    print(f"status: done\\nwrote: {reported}\\nblockers: none")
else:
    print("Résumé — 完了")
''')
    claude.chmod(0o755)
    env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"])

    def invoke(arm="receipt", mode="ok", out=None, cwd=REPO, trial="1"):
        target = Path(out) if out is not None else tmp_path / "results with spaces"
        result = subprocess.run(
            ["bash", str(SCRIPT), arm, trial, str(target)],
            cwd=cwd, env=dict(env, STUB_MODE=mode), capture_output=True, text=True,
        )
        absolute = target if target.is_absolute() else cwd / target
        return result, absolute / arm

    return invoke


def test_receipt_paths_and_files(run_trial):
    result, out = run_trial(trial="08")
    assert result.returncode == 0, result.stderr
    records = [json.loads(line) for line in (out / "t08.jsonl").read_text().splitlines()]
    assert len(records) == 3
    for record in records:
        assert record["trial"] == 8 and record["wrote"] and record["fsize"] > 0
        reply = out / f"reply-t08-{record['task']}.txt"
        assert record["bytes"] == len(reply.read_bytes())


def test_counts_bytes_not_characters(run_trial):
    result, out = run_trial(arm="plain")
    assert result.returncode == 0, result.stderr
    record = json.loads((out / "t1.jsonl").read_text().splitlines()[0])
    assert record["bytes"] == len("Résumé — 完了\n".encode())
    assert record["bytes"] > len("Résumé — 完了\n")


@pytest.mark.parametrize("mode", ["fail", "empty", "missing", "wrong_path"])
def test_failed_calls_are_not_successful_measurements(run_trial, mode):
    result, out = run_trial(mode=mode)
    assert result.returncode != 0
    assert not (out / "t1.jsonl").exists()


def test_trial_reuse_cannot_count_stale_findings(run_trial):
    first, out = run_trial()
    assert first.returncode == 0
    original = (out / "t1.jsonl").read_bytes()
    second, _ = run_trial(mode="missing")
    assert second.returncode != 0
    assert (out / "t1.jsonl").read_bytes() == original


def test_relative_output_from_nested_directory(run_trial, tmp_path):
    out_arg = os.path.relpath(tmp_path / "relative results", REPO / "claude")
    result, out = run_trial(out=out_arg, cwd=REPO / "claude")
    assert result.returncode == 0, result.stderr
    assert (out / "t1.jsonl").is_file()


def test_rejects_invalid_arguments(run_trial):
    result, _ = run_trial(arm="invalid")
    assert result.returncode == 2
