"""Exercise Make's plugin convergence with an isolated, stateful Claude CLI."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parent.parent
PLUGIN = "superpowers@claude-plugins-official"


@pytest.fixture
def converge(tmp_path):
    executables = tmp_path / "bin"
    executables.mkdir()
    for name in ("make",):
        executable = shutil.which(name)
        assert executable, f"{name} is required"
        (executables / name).symlink_to(executable)
    (executables / "python3").symlink_to(sys.executable)
    (executables / "claude-remove-blocked-plugins").symlink_to(ROOT / "bin/claude-remove-blocked-plugins")
    (tmp_path / "claude").mkdir()
    blocklist = tmp_path / "claude/blocked-plugins.json"
    blocklist.write_bytes((ROOT / "claude/blocked-plugins.json").read_bytes())
    state = tmp_path / "plugins.json"
    state.write_text("[]")
    log = tmp_path / "calls.jsonl"
    cli = executables / "claude"
    cli.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
from pathlib import Path
state = Path(os.environ["TEST_PLUGIN_STATE"])
with open(os.environ["TEST_PLUGIN_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1:] == ["plugin", "list", "--json"]:
    if os.environ.get("TEST_LIST_FAIL"):
        sys.exit(9)
    print(state.read_text())
elif len(sys.argv) == 6 and sys.argv[1:3] == ["plugin", "uninstall"] and sys.argv[4:] == ["--scope", "user"]:
    if os.environ.get("TEST_UNINSTALL_FAIL") in ("1", sys.argv[3]):
        sys.exit(10)
    state.write_text(json.dumps([p for p in json.loads(state.read_text())
        if not (p["id"] == sys.argv[3] and p["scope"] == "user")]))
else:
    sys.exit(11)
''')
    cli.chmod(0o755)
    env = dict(os.environ, PATH=str(executables), TEST_PLUGIN_STATE=str(state),
               TEST_PLUGIN_LOG=str(log))

    def run():
        return subprocess.run([str(executables / "make"), "claude-plugins", f"DOTFILES={tmp_path}"],
                              cwd=ROOT, env=env, capture_output=True, text=True)

    return run, state, log, cli, env, blocklist


def test_default_make_and_claude_include_convergence():
    for goal in ([], ["claude"]):
        result = subprocess.run(["make", "-n", *goal], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        assert result.stdout.count("/bin/claude-remove-blocked-plugins") == 1
        assert "/claude/blocked-plugins.json" in result.stdout


def test_missing_claude_is_a_successful_skip(converge):
    run, _, log, cli, _, _ = converge
    cli.unlink()
    assert run().returncode == 0
    assert not log.exists()


def test_removal_converges_and_preserves_other_plugins_and_scopes(converge):
    run, state, log, _, _, blocklist = converge
    another = "retired-tool@custom-marketplace"
    blocklist.write_text(json.dumps([PLUGIN, another, another]))
    retained = [{"id": PLUGIN, "scope": "project"},
                {"id": "superpowers@another-marketplace", "scope": "user"},
                {"id": "skill-creator@claude-plugins-official", "scope": "user"}]
    state.write_text(json.dumps(retained + [{"id": PLUGIN, "scope": "user", "enabled": False},
                                           {"id": another, "scope": "user"}]))
    assert run().returncode == 0
    assert json.loads(state.read_text()) == retained
    assert run().returncode == 0
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert sorted(call[2] for call in calls if call[1] == "uninstall") == sorted([PLUGIN, another])


@pytest.mark.parametrize("failure", ["TEST_LIST_FAIL", "TEST_UNINSTALL_FAIL", "malformed", "wrong_shape"])
def test_inspection_and_uninstall_failures_are_reported(converge, failure):
    run, state, log, _, env, _ = converge
    state.write_text(json.dumps([{"id": PLUGIN, "scope": "user"}]))
    if failure in ("malformed", "wrong_shape"):
        state.write_text("not json" if failure == "malformed" else "{}")
    else:
        env[failure] = "1"
    before = state.read_bytes()
    assert run().returncode != 0
    assert state.read_bytes() == before
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    if failure != "TEST_UNINSTALL_FAIL":
        assert all(call[1] != "uninstall" for call in calls)


@pytest.mark.parametrize("contents", ["not json", "{}", '[null]', '["--bad"]', '["unqualified"]'])
def test_invalid_blocklists_fail_before_invoking_claude(converge, contents):
    run, _, log, _, _, blocklist = converge
    blocklist.write_text(contents)
    assert run().returncode != 0
    assert not log.exists()


def test_empty_blocklist_is_a_noop(converge):
    run, _, log, _, _, blocklist = converge
    blocklist.write_text("[]")
    assert run().returncode == 0
    assert not log.exists()


def test_retry_converges_after_partial_uninstall_failure(converge):
    run, state, log, _, env, blocklist = converge
    first, second = "aaa@custom", "zzz@custom"
    blocklist.write_text(json.dumps([first, second]))
    state.write_text(json.dumps([{"id": p, "scope": "user"} for p in (first, second)]))
    env["TEST_UNINSTALL_FAIL"] = second
    assert run().returncode != 0
    assert json.loads(state.read_text()) == [{"id": second, "scope": "user"}]
    del env["TEST_UNINSTALL_FAIL"]
    assert run().returncode == 0
    assert json.loads(state.read_text()) == []
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert [call[2] for call in calls if call[1] == "uninstall"] == [first, second, second]
