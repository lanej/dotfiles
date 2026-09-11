"""Deterministic checks of the evaluation boundary and installed command contract."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("dialogue_eval", HERE / "run.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
review_spec = importlib.util.spec_from_file_location("dialogue_review", HERE / "review.py")
review_app = importlib.util.module_from_spec(review_spec)
with patch.dict(sys.modules, {"run": app}):
    review_spec.loader.exec_module(review_app)


def envelope(response=None, **overrides):
    data = {"type": "result", "subtype": "success", "is_error": False,
            "modelUsage": {"fixture-model": {}},
            "structured_output": response or {"action": "ask_user", "reply": "Which duration?", "spec": "Pending duration."}}
    data.update(overrides)
    return data


@pytest.mark.parametrize("array", [True, False])
def test_supports_verbose_and_plain_cli_envelopes(array):
    data = envelope()
    result, model = app.parse_cli(json.dumps([{"type": "system"}, data] if array else data))
    assert result["action"] == "ask_user"
    assert model == "fixture-model"


@pytest.mark.parametrize("data", [
    envelope(is_error=True), envelope(subtype="error_during_execution"),
    envelope(permission_denials=[{"tool": "Write"}]), envelope(modelUsage={}),
    envelope(modelUsage={"first": {}, "second": {}}),
    envelope(structured_output={"action": [], "reply": "hi", "spec": "spec"}),
    envelope(structured_output={"action": "ask_user", "reply": "hi", "spec": ""}),
    [envelope(), envelope()], [42],
])
def test_invalid_or_failed_results_cannot_pass(data):
    with pytest.raises(ValueError):
        app.parse_cli(json.dumps(data))


def test_fallback_result_json_is_validated():
    data = envelope(structured_output=None, result=json.dumps({
        "action": "ready_to_plan", "reply": "Ready to draft.", "spec": "R1 has a check."}))
    assert app.parse_cli(json.dumps(data))[0]["action"] == "ready_to_plan"


def test_premature_planning_and_lost_decisions_are_detected():
    scenario = {"turns": [{"action": "ask_user"}], "required_facts": ["14 days"]}
    failures = app.mechanical_checks(scenario, [{"action": "ready_to_plan", "spec": "30 days"}])
    assert len(failures) == 2
    assert app.mechanical_checks(scenario, []) == ["incomplete conversation"]


def test_model_drift_invalidates_comparison():
    rows = [{"arm": arm, "models": [model], "mechanical_failures": []}
            for arm, model in [("old", "one"), ("new", "two")]]
    assert not app.summarize(rows)["comparison_valid"]


def test_infrastructure_failure_is_not_a_behavioral_score():
    rows = [{"arm": "old", "error": "timeout"},
            {"arm": "new", "models": ["one"], "mechanical_failures": []}]
    result = app.summarize(rows)
    assert not result["comparison_valid"]
    assert result["arms"]["old"]["completed"] == 0
    assert result["infrastructure_errors"] == 1


def test_complete_replay_preserves_history_and_excludes_answers(tmp_path):
    args = SimpleNamespace(out=tmp_path, claude="stub", model="fixture-model", effort="medium", timeout=10)
    scenario = {"id": "case", "entry": "socrates", "context": "facts",
                "turns": [{"user": "Pick retention", "action": "ask_user", "question_topic": "secret rubric"},
                          {"user": "14 days", "action": "ready_to_plan", "question_topic": None}],
                "required_facts": ["14 days"], "rubric": "secret expected behavior"}
    outputs = [envelope(), envelope({"action": "ready_to_plan", "reply": "14 days is now settled.", "spec": "14 days"})]
    calls = []

    def invoke(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps(outputs[len(calls)-1]), stderr="")

    with patch.object(app.subprocess, "run", side_effect=invoke):
        record = app.run_case("new", "sha", scenario, 1, args, "workflow")
    assert not record["mechanical_failures"]
    first, second = [json.loads(command[2]) for command, _ in calls]
    assert "14 days" not in json.dumps(first)
    assert "secret" not in json.dumps(second)
    assert second["conversation"][1]["content"]["reply"] == "Which duration?"
    assert calls[0][0][calls[0][0].index("--tools") + 1] == ""
    assert calls[0][1]["stdin"] == app.subprocess.DEVNULL
    with pytest.raises(FileExistsError):
        app.run_case("new", "sha", scenario, 1, args, "workflow")


def test_failed_process_keeps_diagnostics_but_no_success(tmp_path):
    args = SimpleNamespace(out=tmp_path, claude="stub", model="fixture-model", effort="medium", timeout=10)
    scenario = {"id": "case", "entry": "specify", "context": "", "turns": [{"user": "Hi"}]}
    with patch.object(app.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="failure")):
        result = app.run_case("old", "sha", scenario, 1, args, "workflow")
    assert "error" in result
    assert (tmp_path / "old-case-1/turn-1.stderr.txt").read_text() == "failure"
    assert "mechanical_failures" not in result


def test_scenario_coverage_and_expected_endpoints():
    scenarios = json.loads((HERE / "scenarios.json").read_text())
    assert len(scenarios) == len({s["id"] for s in scenarios}) == 8
    for scenario in scenarios:
        assert scenario["required_facts"] and scenario["rubric"]
        for turn in scenario["turns"]:
            assert turn["action"] in app.ACTIONS
            assert bool(turn["question_topic"]) == (turn["action"] == "ask_user")
            if scenario["entry"] == "specify":
                assert turn["action"] != "ready_to_plan"


@pytest.mark.parametrize("command", ["socrates", "specify", "shape", "critique", "verify"])
def test_entrypoints_load_one_contract_with_valid_metadata(command):
    text = (app.ROOT / "claude/commands" / f"{command}.md").read_text()
    metadata = yaml.safe_load(text.split("---", 2)[1])
    assert isinstance(metadata["argument-hint"], str)
    assert "Task" not in metadata["allowed-tools"]
    assert "$HOME/.claude/commands/socrates/dialogue.txt" in text
    assert "Score <" not in text and "sub-70%" not in text
    assert (app.ROOT / "claude/commands/socrates/dialogue.txt").is_file()


def test_shared_scaffold_and_planning_companion_do_not_restore_old_gate():
    root = app.ROOT / "claude/commands/socrates"
    scaffold = (root / "spec-scaffold.tpl").read_text()
    assert "Readiness Contract: evidence-v1" in scaffold
    assert "## Decision Record" in scaffold and "## Critique Reconciliation" in scaffold
    assert "Commandment Scores" not in scaffold and "Current Pass" not in scaffold
    phases = (root / "phases-2-3.txt").read_text()
    assert "dialogue.txt" in phases and "Score <" not in phases
    assert "SESSION_DIR/plan.md" in phases and "Once approved" in phases


@pytest.fixture
def reviewed_run(tmp_path):
    scenarios = json.loads((HERE / "scenarios.json").read_text())
    (tmp_path / "scenarios.json").write_bytes((HERE / "scenarios.json").read_bytes())
    manifest = {"scenarios_sha256": hashlib.sha256((HERE / "scenarios.json").read_bytes()).hexdigest(),
                "refs": {"old": "before", "new": "after"}, "trials": 1}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    reviews = {}
    for arm in ("old", "new"):
        for scenario in scenarios:
            key = f"{arm}-{scenario['id']}-1"
            folder = tmp_path / key
            folder.mkdir()
            data = json.dumps({"arm": arm, "ref": manifest["refs"][arm], "models": ["fixture"],
                               "mechanical_failures": []}).encode()
            (folder / "record.json").write_bytes(data)
            reviews[key] = {"record_sha256": hashlib.sha256(data).hexdigest(),
                            "checks": {c: {"passed": True, "evidence": "Fixture evidence"}
                                       for c in review_app.CHECKS},
                            "counts": {c: 0 for c in review_app.COUNTS},
                            "question_notes": "Fixture: no unnecessary question"}
    return tmp_path, reviews


def test_review_requires_all_candidate_checks_to_pass(reviewed_run):
    folder, reviews = reviewed_run
    assert review_app.assess(folder, reviews)["candidate_passes_all_checks"]
    reviews["new-legacy_scores-1"]["checks"]["decision_preservation"]["passed"] = False
    result = review_app.assess(folder, reviews)
    assert not result["candidate_passes_all_checks"]
    assert result["arms"]["new"]["scenario_passes"] == 7


@pytest.mark.parametrize("change", ["missing_case", "stale_record", "missing_check", "no_evidence", "invalid_count"])
def test_incomplete_or_stale_reviews_cannot_pass(reviewed_run, change):
    folder, reviews = reviewed_run
    item = reviews["new-clear_request-1"]
    if change == "missing_case":
        del reviews["old-legacy_scores-1"]
    elif change == "stale_record":
        item["record_sha256"] = "wrong"
    elif change == "missing_check":
        del item["checks"]["seeded_blockers"]
    elif change == "no_evidence":
        item["checks"]["readiness_and_endpoint"]["evidence"] = ""
    else:
        item["counts"]["unnecessary_questions"] = True
    with pytest.raises(ValueError):
        review_app.assess(folder, reviews)
