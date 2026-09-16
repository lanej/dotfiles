"""Exercise the tdd-brief ablation end to end without invoking a model."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

def writes_expected(mode):
    """Files written inside the fixture — one per file, not per stream event."""
    return {"test_first": 2, "impl_first": 2, "no_test": 1}[mode]


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUN = HERE / "run.sh"
ANALYZE = HERE / "analyze.py"

STUB = '''
import json, os, sys
from pathlib import Path

mode = os.environ["STUB_MODE"]
if mode == "fail":
    print("simulated failure", file=sys.stderr); sys.exit(17)
if mode == "empty":
    sys.exit(0)

prompt = sys.argv[sys.argv.index("-p") + 1]
Path(os.environ["STUB_PROMPTS"]).open("a").write(prompt.replace("\\n", " | ") + "\\n")

order = {"test_first": ["tests/test_new.py", "textkit/core.py"],
         "impl_first": ["textkit/core.py", "tests/test_new.py"],
         "no_test": ["textkit/core.py"],
         "stray": ["../escaped.py", "tests/test_new.py", "textkit/core.py"]}[mode]

print(json.dumps({"type": "system", "subtype": "init"}))
for path in order:
    # The real CLI emits a partial tool_use in stream_event BEFORE the complete
    # one in the assistant message: same name, no input yet. Reproduce both, so
    # a classifier that scans indiscriminately double-counts and fails here.
    # Today the partial carries no input, so a naive scan happens to agree with
    # a correct one. Emit a COMPLETE input here — the shape a future CLI could
    # send — so this pins "only assistant events count" rather than relying on
    # the partial staying empty.
    print(json.dumps({"type": "stream_event", "event": {
        "type": "content_block_start", "index": 0,
        "content_block": {"type": "tool_use", "id": "t1", "name": "Write",
                          "input": {"file_path": path, "content": "x"}}}}))
    print(json.dumps({"type": "assistant", "message": {
        "model": "stub-model-1", "content": [
            {"type": "text", "text": "working"},
            {"type": "tool_use", "name": "Write",
             "input": {"file_path": path, "content": "x"}}]}}))
    print(json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}}))
print(json.dumps({"type": "result", "subtype": "success"}))
'''


@pytest.fixture
def harness(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "timeout").write_text('#!/bin/bash\nshift\nexec "$@"\n')
    (bindir / "timeout").chmod(0o755)
    (bindir / "claude").write_text(f"#!{sys.executable}\n{STUB}")
    (bindir / "claude").chmod(0o755)
    prompts = tmp_path / "prompts.txt"
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}",
               STUB_PROMPTS=str(prompts))

    def invoke(arm="state", mode="test_first", trial="1", out=None):
        target = Path(out) if out else tmp_path / "results with spaces"
        result = subprocess.run([
            "bash", str(RUN), arm, trial, str(target)],
            cwd=REPO, env=dict(env, STUB_MODE=mode), capture_output=True, text=True)
        return result, target / arm, prompts

    return invoke


def test_arm_briefs_differ_only_in_the_clause_under_test(harness):
    _, _, prompts = harness(arm="state")
    state = prompts.read_text().splitlines()
    prompts.write_text("")
    _, _, prompts = harness(arm="omit")
    omit = prompts.read_text().splitlines()

    assert len(state) == len(omit) == 4
    for said, silent in zip(state, omit):
        assert "Write tests first." in said
        assert "tests first" not in silent
        # Each arm works in its own directory; that path is the only other
        # difference, and it must not leak the arm name into the brief's wording.
        stripped = said.replace("Write tests first. ", "").replace("/state/", "/ARM/")
        assert stripped == silent.replace("/omit/", "/ARM/")


def test_write_order_is_read_from_the_event_stream(harness):
    for mode, expected in (("test_first", "test_first"),
                           ("impl_first", "impl_first"),
                           ("no_test", "no_test")):
        result, out, _ = harness(mode=mode, trial={"test_first": "1",
                                                   "impl_first": "2",
                                                   "no_test": "3"}[mode])
        assert result.returncode == 0, result.stderr
        records = [json.loads(l) for l in
                   (out / f"t{ {'test_first':1,'impl_first':2,'no_test':3}[mode] }.jsonl"
                    ).read_text().splitlines()]
        assert len(records) == 4
        assert {r["outcome"] for r in records} == {expected}
        assert {r["task"] for r in records} == {0, 1, 2, 3}
        # One write per file, not one per stream_event/assistant pair.
        assert all(r["writes"] == writes_expected(mode) for r in records)
        assert {r["model"] for r in records} == {"stub-model-1"}


def test_writes_outside_the_fixture_are_not_counted(harness):
    result, out, _ = harness(mode="stray")
    assert result.returncode == 0, result.stderr
    records = [json.loads(l) for l in (out / "t1.jsonl").read_text().splitlines()]
    # The escaped path must not become the first "impl" write and flip the call.
    assert {r["outcome"] for r in records} == {"test_first"}
    assert all(r["writes"] == 2 for r in records)


@pytest.mark.parametrize("mode", ["fail", "empty"])
def test_a_failed_call_is_never_a_measurement(harness, mode):
    result, out, _ = harness(mode=mode)
    assert result.returncode != 0
    assert not (out / "t1.jsonl").exists()


def test_a_reused_trial_cannot_count_stale_runs(harness):
    first, out, _ = harness()
    assert first.returncode == 0
    original = (out / "t1.jsonl").read_bytes()
    second, _, _ = harness(mode="impl_first")
    assert second.returncode != 0
    assert (out / "t1.jsonl").read_bytes() == original


def test_rejects_an_unknown_arm(harness):
    result, _, _ = harness(arm="control")
    assert result.returncode == 2


def _dataset(tmp_path, omit_hits, state_hits, n=20):
    for arm, hits in (("omit", omit_hits), ("state", state_hits)):
        (tmp_path / arm).mkdir(parents=True)
        rows = [{"arm": arm, "trial": 1, "task": i, "outcome":
                 "test_first" if i < hits else "impl_first", "writes": 2}
                for i in range(n)]
        (tmp_path / arm / "t1.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n")
    return subprocess.run([sys.executable, str(ANALYZE), str(tmp_path)],
                          capture_output=True, text=True)


def test_verdict_follows_the_preregistered_rule(tmp_path):
    # Clause looks inert: omit clears 18/20 and the arms are indistinguishable.
    delete = _dataset(tmp_path / "a", omit_hits=19, state_hits=20)
    assert "VERDICT: DELETE" in delete.stdout, delete.stdout

    # Clause is load-bearing: a large, significant gap.
    keep = _dataset(tmp_path / "b", omit_hits=5, state_hits=19)
    assert "VERDICT: KEEP" in keep.stdout, keep.stdout

    # Indistinguishable but the omit arm misses the absolute bar — not a delete.
    murky = _dataset(tmp_path / "c", omit_hits=14, state_hits=17)
    assert "VERDICT: INCONCLUSIVE" in murky.stdout, murky.stdout

    # Too few scored runs must refuse to render any verdict at all.
    short = _dataset(tmp_path / "d", omit_hits=10, state_hits=10, n=12)
    assert short.returncode == 1 and "INCOMPLETE" in short.stdout
    assert "VERDICT" not in short.stdout
