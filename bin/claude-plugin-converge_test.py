"""One regression detector for removing blocklisted Claude plugins."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def test_make_converges_blocked_plugins_without_removing_other_installations(tmp_path):
    executables = tmp_path / "bin"
    executables.mkdir()
    (executables / "python3").symlink_to(sys.executable)
    (executables / "claude-remove-blocked-plugins").symlink_to(ROOT / "bin/claude-remove-blocked-plugins")
    (tmp_path / "claude").mkdir()
    (tmp_path / "claude/blocked-plugins.json").write_text(json.dumps([
        "superpowers@claude-plugins-official", "retired-tool@custom",
    ]))
    retained = [
        {"id": "skill-creator@claude-plugins-official", "scope": "user"},
        {"id": "superpowers@claude-plugins-official", "scope": "project"},
    ]
    state = tmp_path / "installed.json"
    state.write_text(json.dumps(retained + [
        {"id": "superpowers@claude-plugins-official", "scope": "user"},
        {"id": "retired-tool@custom", "scope": "user"},
    ]))
    calls = tmp_path / "uninstalls.jsonl"
    cli = executables / "claude"
    cli.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
from pathlib import Path
state = Path(os.environ["TEST_PLUGIN_STATE"])
if sys.argv[1:] == ["plugin", "list", "--json"]:
    print(state.read_text())
elif len(sys.argv) == 6 and sys.argv[1:3] == ["plugin", "uninstall"] and sys.argv[4:] == ["--scope", "user"]:
    plugin = sys.argv[3]
    with open(os.environ["TEST_PLUGIN_CALLS"], "a") as log:
        log.write(json.dumps(plugin) + "\\n")
    state.write_text(json.dumps([p for p in json.loads(state.read_text())
                                if not (p["id"] == plugin and p["scope"] == "user")]))
else:
    sys.exit(1)
''')
    cli.chmod(0o755)
    env = dict(os.environ, PATH=str(executables),
               TEST_PLUGIN_STATE=str(state), TEST_PLUGIN_CALLS=str(calls))
    command = [shutil.which("make"), "claude-plugins", f"DOTFILES={tmp_path}"]

    subprocess.run(command, cwd=ROOT, env=env, check=True)
    assert json.loads(state.read_text()) == retained
    first_run = calls.read_bytes()
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    assert calls.read_bytes() == first_run
