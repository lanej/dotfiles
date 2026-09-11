#!/usr/bin/env python3
"""Paired, tool-free dialogue replay. Never uses real task data or native tools."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ACTIONS = {"ask_user", "ready_to_plan", "specification_complete", "continue_existing"}
SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": sorted(ACTIONS)},
        "reply": {"type": "string", "description": "Only the conversational response. Do not put the full specification here."},
        "spec": {"type": "string", "description": "The complete current Markdown specification, including all requirements, decisions, and required history. Never refer to another field instead of providing the artifact."},
    },
    "required": ["action", "reply", "spec"],
    "additionalProperties": False,
}
DRIVER = """You are replaying one turn of a Socrates workflow in a simulated environment.
Apply the supplied command and companion instructions. All relevant research facts,
session artifacts, and user statements are supplied in the input; no tools exist.
Do not actually execute work, seek credentials, or claim real files were written.
Simulate the session-artifact updates by returning the complete current spec as
Markdown in `spec`, and the actual user-facing conversational turn in `reply`.
Put the full specification in `spec`, never in `reply` or a 'see above' reference.
Return artifact Markdown without XML/protocol delimiters. Do not invent missing
prior artifact content; the supplied facts and artifacts are the entire context.
Preserve required workflow bookkeeping in the spec rather than hiding its cost.
Represent the next workflow action as `ask_user`, `ready_to_plan` (enter planning,
not approval or execution), `specification_complete` (specify endpoint), or
`continue_existing` (an unchanged later lifecycle state). If the command would ask
a question, ask it naturally; do not answer on the user's behalf. Respond using
the required JSON schema. The input's conversation includes the exact prior outputs
and scripted user replies. Only the command bundle differs between comparison arms.
"""


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def bundle(ref, entry):
    paths = [f"claude/commands/{entry}.md", "claude/commands/socrates/spec-scaffold.tpl"]
    if entry == "socrates":
        paths.append("claude/commands/socrates/phases-2-3.txt")
    shared = "claude/commands/socrates/dialogue.txt"
    tracked = set(git("ls-tree", "-r", "--name-only", ref).splitlines())
    if shared in tracked:
        paths.append(shared)
    content = "\n\n".join(f"<file path='{p}'>\n{git('show', f'{ref}:{p}')}\n</file>" for p in paths)
    return DRIVER + "\n\n" + content


def parse_cli(text):
    payload = json.loads(text)
    events = payload if isinstance(payload, list) else [payload]
    if not all(isinstance(event, dict) for event in events):
        raise ValueError("CLI envelope must contain objects")
    results = [event for event in events if event.get("type") == "result"]
    if len(results) != 1 or results[0].get("is_error") or results[0].get("subtype") != "success":
        raise ValueError("CLI did not return exactly one successful result")
    result = results[0]
    if result.get("permission_denials"):
        raise ValueError("Permission-denied result cannot count as a dialogue trial")
    response = result.get("structured_output")
    if response is None:
        if not isinstance(result.get("result"), str):
            raise ValueError("CLI result has no structured response")
        response = json.loads(result["result"])
    if (not isinstance(response, dict) or set(response) != set(SCHEMA["required"])
            or not all(isinstance(response[k], str) for k in SCHEMA["required"])
            or response["action"] not in ACTIONS
            or not response["spec"].strip() or not response["reply"].strip()):
        raise ValueError("Missing or invalid response fields")
    if not isinstance(result.get("modelUsage"), dict):
        raise ValueError("CLI result must record model usage")
    models = sorted(result["modelUsage"])
    if len(models) != 1:
        raise ValueError("Trial must record exactly one resolved model")
    return response, models[0]


def mechanical_checks(scenario, responses):
    failures = []
    for index, (step, response) in enumerate(zip(scenario["turns"], responses)):
        if response["action"] != step["action"]:
            failures.append(f"turn {index + 1}: expected {step['action']}, got {response['action']}")
    if len(responses) != len(scenario["turns"]):
        failures.append("incomplete conversation")
    if responses:
        for pattern in scenario["required_facts"]:
            if re.search(pattern, responses[-1]["spec"], re.I) is None:
                failures.append(f"final spec missing fixture fact: {pattern}")
    return failures


def run_case(arm, ref, scenario, trial, args, system_prompt):
    folder = args.out / f"{arm}-{scenario['id']}-{trial}"
    folder.mkdir()  # refuse to reuse an existing run, including failed attempts
    history = []
    responses = []
    models = set()
    start = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="socrates-eval-") as scratch:
            for index, step in enumerate(scenario["turns"]):
                history.append({"role": "user", "content": step["user"]})
                prompt = json.dumps({"entry": scenario["entry"], "context": scenario["context"],
                                     "conversation": history}, ensure_ascii=False)
                command = [args.claude, "-p", prompt, "--bare", "--no-session-persistence",
                           "--disable-slash-commands", "--strict-mcp-config", "--tools", "",
                           "--model", args.model, "--effort", args.effort, "--output-format", "json",
                           "--json-schema", json.dumps(SCHEMA), "--system-prompt", system_prompt]
                result = subprocess.run(command, cwd=scratch, stdin=subprocess.DEVNULL,
                                        capture_output=True, text=True, timeout=args.timeout)
                (folder / f"turn-{index + 1}.stdout.json").write_text(result.stdout)
                (folder / f"turn-{index + 1}.stderr.txt").write_text(result.stderr)
                if result.returncode:
                    raise RuntimeError(f"CLI exited {result.returncode}; inspect captured output")
                response, model = parse_cli(result.stdout)
                models.add(model)
                responses.append(response)
                history.append({"role": "assistant", "content": response})
                (folder / f"turn-{index + 1}.json").write_text(json.dumps(response, indent=2, ensure_ascii=False))
        record = {"arm": arm, "ref": ref, "scenario": scenario["id"], "trial": trial,
                  "models": sorted(models), "responses": responses,
                  "mechanical_failures": mechanical_checks(scenario, responses),
                  "elapsed_seconds": round(time.monotonic() - start, 2),
                  "manual_review": "pending"}
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        if isinstance(error, subprocess.TimeoutExpired):
            for stream, value in (("stdout.json", error.stdout), ("stderr.txt", error.stderr)):
                if value is not None:
                    if isinstance(value, bytes):
                        value = value.decode(errors="replace")
                    (folder / f"turn-{index + 1}.{stream}").write_text(value)
            message = f"CLI timed out after {args.timeout} seconds; inspect captured output"
        else:
            message = str(error)
        record = {"arm": arm, "ref": ref, "scenario": scenario["id"], "trial": trial,
                  "error": message, "responses": responses}
    (folder / "record.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return record


def summarize(records):
    errors = [r for r in records if "error" in r]
    models = {m for r in records for m in r.get("models", [])}
    valid = not errors and len(models) == 1
    return {
        "comparison_valid": valid,
        "models": sorted(models),
        "infrastructure_errors": len(errors),
        "manual_review": "pending: inspect questions and specs against scenario rubrics",
        "arms": {arm: {
            "completed": sum("error" not in r for r in records if r["arm"] == arm),
            "mechanical_passes": sum("error" not in r and not r["mechanical_failures"]
                                     for r in records if r["arm"] == arm),
        } for arm in ("old", "new")},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, help="Immutable pre-change commit")
    parser.add_argument("--candidate", default="HEAD")
    parser.add_argument("--model", required=True, help="Pin the same model for both arms")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=360)
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if min(args.trials, args.jobs, args.timeout) < 1:
        parser.error("trials, jobs, and timeout must be positive")
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    scenarios = json.loads((HERE / "scenarios.json").read_text())
    (args.out / "scenarios.json").write_bytes((HERE / "scenarios.json").read_bytes())
    refs = {"old": git("rev-parse", args.baseline + "^{commit}"),
            "new": git("rev-parse", args.candidate + "^{commit}")}
    prompts = {(arm, entry): bundle(ref, entry) for arm, ref in refs.items()
               for entry in {s["entry"] for s in scenarios}}
    for (arm, entry), prompt in prompts.items():
        (args.out / f"{arm}-{entry}-prompt.txt").write_text(prompt)
    manifest = {"refs": refs, "model": args.model, "effort": args.effort, "trials": args.trials,
                "jobs": args.jobs, "cli_version": subprocess.check_output([args.claude, "--version"], text=True).strip(),
                "scenarios_sha256": hashlib.sha256((HERE / "scenarios.json").read_bytes()).hexdigest(),
                "prompt_sha256": {f"{a}-{e}": hashlib.sha256(p.encode()).hexdigest() for (a, e), p in prompts.items()}}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    records = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = []
        for trial in range(1, args.trials + 1):
            # Alternate order within each pair; never run all of one arm first.
            for index, scenario in enumerate(scenarios):
                for arm in (["old", "new"] if (index + trial) % 2 else ["new", "old"]):
                    futures.append(pool.submit(run_case, arm, refs[arm], scenario, trial, args,
                                               prompts[arm, scenario["entry"]]))
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            label = "ERROR" if "error" in record else ("CHECK" if record["mechanical_failures"] else "PASS")
            print(f"{record['arm']} {record['scenario']} trial {record['trial']}: {label}", flush=True)
    summary = summarize(records)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    # Baseline behavioral failures are expected; candidate failures gate adoption.
    return int(not summary["comparison_valid"] or any(
        r.get("mechanical_failures") for r in records if r["arm"] == "new"))


if __name__ == "__main__":
    raise SystemExit(main())
