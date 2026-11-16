"""Exercise transcript reading and package validation through their CLI boundaries."""

import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parent.parent
READER = ROOT / "ai/skills/handoff/scripts/transcript.py"


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_transcript_resolution_digest_and_paging_preserve_evidence(tmp_path, host):
    session = "session-123"
    if host == "codex":
        events = [
            {"type": "session_meta", "payload": {"id": session}},
            {"type": "response_item", "payload": {"type": "message", "role": "user",
             "content": [{"type": "input_text", "text": "Keep the original file — report only."}]}},
            {"type": "response_item", "payload": {"type": "reasoning", "summary": "PRIVATE_REASONING"}},
            {"type": "response_item", "payload": {"type": "function_call", "name": "read_file", "arguments": "report.txt"}},
            {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "read-1", "output": "bounded " * 200}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant",
             "content": [{"type": "output_text", "text": "The original is unchanged."}]}},
        ]
    else:
        events = [
            {"type": "system", "sessionId": session},
            {"type": "user", "message": {"content": "Keep the original file — report only."}},
            {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "PRIVATE_REASONING"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": "report.txt"}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "read-1", "content": "bounded " * 200}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "The original is unchanged."}]}},
        ]
    transcript = tmp_path / f"rollout-{session}.jsonl"
    original = "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n"
    transcript.write_text(original)
    base = [sys.executable, str(READER), "--host", host]
    found = subprocess.run(base + ["--root", str(tmp_path), "--session-id", session, "--resolve"],
                           check=True, capture_output=True, text=True)
    assert found.stdout.strip() == str(transcript)
    first = subprocess.run(base + [str(transcript), "--limit", "1"], check=True, capture_output=True, text=True)
    assert "Keep the original file — report only." in first.stdout
    assert f"{transcript}:2" in first.stdout and "--start-line 3" in first.stdout
    rest = subprocess.run(base + [str(transcript), "--start-line", "3"], check=True, capture_output=True, text=True)
    assert "report.txt" in rest.stdout and "The original is unchanged." in rest.stdout
    assert "PRIVATE_REASONING" not in rest.stdout
    assert "[truncated; inspect source]" in rest.stdout and len(rest.stdout) < 2000
    assert transcript.read_text() == original
    if host == "codex":
        hidden = {"type": "response_item", "payload": {"type": "message", "role": "assistant",
                  "channel": "analysis", "content": [{"type": "output_text", "text": "PRIVATE_CHANNEL"}]}}
        with transcript.open("a") as stream:
            stream.write(json.dumps(hidden) + "\n")
        result = subprocess.run(base + [str(transcript)], check=True, capture_output=True, text=True)
        assert "PRIVATE_CHANNEL" not in result.stdout
    duplicate = tmp_path / "duplicate" / transcript.name
    duplicate.parent.mkdir()
    duplicate.write_text(original)
    ambiguous = subprocess.run(base + ["--root", str(tmp_path), "--session-id", session, "--resolve"],
                               capture_output=True, text=True)
    assert ambiguous.returncode != 0 and "found 2" in ambiguous.stderr
    missing = subprocess.run(base + ["--root", str(tmp_path), "--session-id", "missing", "--resolve"],
                             capture_output=True, text=True)
    assert missing.returncode != 0 and "found 0" in missing.stderr


def test_reader_reports_bad_input_without_treating_it_as_empty_success(tmp_path):
    transcript = tmp_path / "broken.jsonl"
    transcript.write_text('{"type":')
    result = subprocess.run([sys.executable, str(READER), str(transcript), "--host", "codex"],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "malformed or incomplete JSON" in result.stderr


def test_authoring_validator_checks_real_resources_and_rejects_broken_packages(tmp_path):
    pytest.importorskip("yaml")
    validator = ROOT / "ai/skills/skill-authoring/scripts/validate.py"
    names = json.loads((ROOT / "ai/skills/portable-workflows.json").read_text())
    subprocess.run([sys.executable, str(validator), *[str(ROOT / "ai/skills" / name) for name in names]],
                   check=True, capture_output=True, text=True)
    package = tmp_path / "sample"
    package.mkdir()
    entrypoint = package / "SKILL.md"
    entrypoint.write_text('---\nname: sample\ndescription: "Use when reviewing a sample --- document."\n---\nRead [the guide](references/guide.md).\n')
    (package / "references").mkdir()
    guide = package / "references/guide.md"
    guide.write_text("Inspect the supplied document.\n")
    command = [sys.executable, str(validator), str(package)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    guide.unlink()
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0 and "missing resource" in result.stderr
    entrypoint.write_text('---\nname: different\ndescription: Example\n---\nInspect.\n')
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0 and "match the folder" in result.stderr
