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
    for name in ("make", "jq"):
        executable = shutil.which(name)
        assert executable, f"{name} is required"
        (executables / name).symlink_to(executable)
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
elif sys.argv[1:] == ["plugin", "uninstall", "superpowers@claude-plugins-official", "--scope", "user"]:
    if os.environ.get("TEST_UNINSTALL_FAIL"):
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
        return subprocess.run([str(executables / "make"), "claude-plugins"],
                              cwd=ROOT, env=env, capture_output=True, text=True)

    return run, state, log, cli, env


def test_default_make_and_claude_include_convergence():
    for goal in ([], ["claude"]):
        result = subprocess.run(["make", "-n", *goal], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        assert result.stdout.count("claude plugin uninstall") == 1


def test_missing_claude_is_a_successful_skip(converge):
    run, _, log, cli, _ = converge
    cli.unlink()
    assert run().returncode == 0
    assert not log.exists()


def test_removal_converges_and_preserves_other_plugins_and_scopes(converge):
    run, state, log, _, _ = converge
    retained = [{"id": PLUGIN, "scope": "project"},
                {"id": "skill-creator@claude-plugins-official", "scope": "user"}]
    state.write_text(json.dumps(retained + [{"id": PLUGIN, "scope": "user", "enabled": False}]))
    assert run().returncode == 0
    assert json.loads(state.read_text()) == retained
    assert run().returncode == 0
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert sum(call[1] == "uninstall" for call in calls) == 1


@pytest.mark.parametrize("failure", ["TEST_LIST_FAIL", "TEST_UNINSTALL_FAIL", "malformed", "wrong_shape"])
def test_inspection_and_uninstall_failures_are_reported(converge, failure):
    run, state, log, _, env = converge
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
