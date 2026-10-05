"""One detector for selecting a dispatcher belonging to the current checkout."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def test_launch_and_status_select_current_checkout(tmp_path):
    repo = tmp_path / "first/project"
    other = tmp_path / "second/project"
    repo.mkdir(parents=True)
    other.mkdir(parents=True)
    subprocess.run([shutil.which("git"), "init", "-q", str(repo)], check=True)
    (repo / ".claude").mkdir()
    (repo / ".claude/dispatcher.config.json").write_text("{}")
    state = tmp_path / "sessions.json"
    state.write_text(json.dumps([{
        "name": "dispatcher-project", "id": "other", "cwd": str(other),
        "state": "running", "startedAt": 999,
    }]))
    executables = tmp_path / "bin"
    executables.mkdir()
    (executables / "python3").symlink_to(sys.executable)
    cli = executables / "claude"
    cli.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
from pathlib import Path
state = Path(os.environ["DISPATCHER_TEST_STATE"])
sessions = json.loads(state.read_text())
if sys.argv[1] == "agents":
    print(json.dumps(sessions))
else:
    assert sys.argv[1] == "-n"
    sessions.append({"name": sys.argv[2], "id": "current", "cwd": os.getcwd(),
                     "state": "running", "startedAt": 1})
    state.write_text(json.dumps(sessions))
''')
    cli.chmod(0o755)
    env = dict(os.environ, PATH=f"{executables}:/usr/bin:/bin",
               DISPATCHER_TEST_STATE=str(state))
    env.pop("DISPATCHER_CONFIG", None)
    script = ROOT / "claude/skills/dispatcher/scripts/dispatcher-launch"
    launched = subprocess.run(["/bin/bash", str(script), "launch"], cwd=repo,
                              env=env, capture_output=True, text=True,
                              check=True, timeout=20)
    assert f"(id: current, repo: {repo})" in launched.stdout
    status = subprocess.run(["/bin/bash", str(script), "status"], cwd=repo,
                            env=env, capture_output=True, text=True,
                            check=True, timeout=10)
    assert "id: current\n" in status.stdout
    assert f"cwd: {repo}\n" in status.stdout
