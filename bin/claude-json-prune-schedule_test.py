"""One regression detector for the `claude-json-prune-schedule` Make target's
OS branch: Darwin -> launchd plist, Linux -> systemd --user service+timer.

`make -n` can't validate this — it only echoes the recipe's shell text
verbatim without evaluating the embedded `if [ "$os" = ... ]` branches. This
actually executes the recipe with a faked `uname`, `launchctl`, and
`systemctl` on an isolated PATH (same technique as bin/claude-plugin-converge_test.py
and bin/claude-json-prune_test.py), against a throwaway HOME, and checks
each OS case rendered the right files and invoked the right tool — and only
that tool.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def _build_executables(bin_dir, calls_log, uname_value):
    bin_dir.mkdir()
    for tool in ("sed", "mkdir"):
        resolved = shutil.which(tool)
        assert resolved, f"{tool} must be resolvable on PATH to run this test"
        (bin_dir / tool).symlink_to(resolved)

    def write_script(name, body):
        script = bin_dir / name
        script.write_text(f"#!{sys.executable}\n" + body)
        script.chmod(0o755)

    write_script("uname", f'''
import sys
if sys.argv[1:] == ["-s"]:
    print("{uname_value}")
else:
    sys.exit(1)
''')

    def write_logging_cli(name):
        write_script(name, f'''
import json, os, sys
with open(os.environ["TEST_CALLS_LOG"], "a") as log:
    log.write(json.dumps(["{name}"] + sys.argv[1:]) + "\\n")
sys.exit(0)
''')

    write_logging_cli("launchctl")
    write_logging_cli("systemctl")
    return bin_dir


def _run_schedule(tmp_path, uname_value):
    home = tmp_path / f"home-{uname_value}"
    home.mkdir()
    calls_log = tmp_path / f"calls-{uname_value}.jsonl"
    calls_log.write_text("")
    executables = _build_executables(tmp_path / f"bin-{uname_value}", calls_log, uname_value)

    env = dict(os.environ, PATH=str(executables), TEST_CALLS_LOG=str(calls_log))
    command = [shutil.which("make"), "claude-json-prune-schedule",
               f"DOTFILES={ROOT}", f"HOME={home}"]
    result = subprocess.run(command, cwd=str(ROOT), env=env,
                             capture_output=True, text=True, timeout=30)
    calls = [json.loads(line) for line in calls_log.read_text().splitlines() if line.strip()]
    return home, result, calls


def test_claude_json_prune_schedule_branches_by_os(tmp_path):
    # --- Darwin: launchd plist rendered + launchctl invoked, systemd untouched
    home, result, calls = _run_schedule(tmp_path, "Darwin")
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"

    plist = home / "Library/LaunchAgents/com.joshlane.claude-json-prune.plist"
    assert plist.exists()
    plist_text = plist.read_text()
    assert "__HOME__" not in plist_text
    assert str(home) in plist_text

    assert any(c[0] == "launchctl" and c[1] == "unload" for c in calls), calls
    assert any(c[0] == "launchctl" and c[1] == "load" for c in calls), calls
    assert not any(c[0] == "systemctl" for c in calls), calls
    assert not (home / ".config/systemd/user/claude-json-prune.service").exists()
    assert not (home / ".config/systemd/user/claude-json-prune.timer").exists()

    # --- Linux: systemd unit + timer rendered + systemctl invoked, launchd untouched
    home, result, calls = _run_schedule(tmp_path, "Linux")
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"

    service = home / ".config/systemd/user/claude-json-prune.service"
    timer = home / ".config/systemd/user/claude-json-prune.timer"
    assert service.exists()
    assert timer.exists()
    service_text = service.read_text()
    timer_text = timer.read_text()
    assert "__HOME__" not in service_text
    assert "__HOME__" not in timer_text
    assert str(home) in service_text

    assert any(c[0] == "systemctl" and c[1:3] == ["--user", "daemon-reload"] for c in calls), calls
    assert any(c[0] == "systemctl" and "enable" in c and "--now" in c for c in calls), calls
    assert not any(c[0] == "launchctl" for c in calls), calls
    assert not (home / "Library/LaunchAgents/com.joshlane.claude-json-prune.plist").exists()
