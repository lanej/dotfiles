"""Retire Paseo integration through the configuration entrypoint, preserving Pi."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def test_paseo_cleanup_preserves_pi_local_files_and_unrelated_hooks(tmp_path):
    home = tmp_path / "home"
    binaries = tmp_path / "bin"
    binaries.mkdir()
    (binaries / "python3").symlink_to(sys.executable)
    paseo = binaries / "paseo"
    paseo.write_text(
        "#!/bin/sh\n"
        'test -z "${PASEO_HOST:-}" || exit 2\n'
        'printf "%s\\n" "$@" >> "$PASEO_RELOAD_LOG"\n'
        'exit "${PASEO_RELOAD_STATUS:-0}"\n'
    )
    paseo.chmod(0o755)
    pi = {"enabled": True, "command": ["paseo-pi"], "paseoTools": {"enabled": True}}
    config = home / ".paseo/config.json"
    config.parent.mkdir(parents=True)
    initial = {
        "daemon": {
            "enableTerminalAgentHooks": True,
            "mcp": {"enabled": True, "injectIntoAgents": True},
        },
        "agents": {"providers": {
            "pi": pi,
            "claude": {"command": ["my-claude"], "paseoTools": {"enabled": True}},
            "codex": {"enabled": True, "command": ["my-codex"]},
        }},
        "pluginsEnabled": True,
    }
    config.write_text(json.dumps(initial))
    config.chmod(0o640)
    keep = {"type": "command", "command": "my-hook", "timeout": 3}
    for provider, filename in (("codex", ".codex/hooks.json"),
                               ("claude", ".claude/settings.json")):
        target = tmp_path / f"{provider}-hooks.json"
        target.write_text(json.dumps({"custom": "retain", "hooks": {
            "SessionStart": [{"matcher": "startup", "hooks": [
                keep,
                {"type": "command", "command":
                 f'if [ -n "$PASEO_TERMINAL_ID" ]; then "${{PASEO_HOOK_CLI:-paseo}}" hooks {provider} SessionStart; fi'},
            ]}],
            "Stop": [{"hooks": [{"type": "command", "command":
                                f'/usr/local/bin/paseo hooks {provider} Stop'}]}],
        }}))
        installed = home / filename
        installed.parent.mkdir(parents=True)
        installed.symlink_to(target)

    skill_roots = (".agents/skills", ".claude/skills", ".codex/skills", ".codex/dotfiles-skills")
    original_plugin = tmp_path / "paseo-plugin"
    original_plugin.mkdir()
    (original_plugin / "SKILL.md").write_text("Original package.\n")
    for root in skill_roots:
        directory = home / root
        directory.mkdir(parents=True)
        for name in ("paseo", "paseo-advisor", "paseo-committee", "paseo-handoff", "paseo-help"):
            skill = directory / name
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"{name} instructions.\n")
            (skill / "my-notes.md").write_text("Preserve local additions.\n")
        (directory / "paseo-plugin").symlink_to(original_plugin)
        personal = directory / "personal"
        personal.mkdir()
        (personal / "SKILL.md").write_text("Personal instructions.\n")
    pi_settings = home / ".pi/agent/settings.json"
    pi_settings.parent.mkdir(parents=True)
    pi_settings.write_text('{"extensions":["paseo-questions.mjs"]}\n')
    reload_log = tmp_path / "reload.log"
    environment = {
        key: value for key, value in os.environ.items()
        if key not in {"CODEX_HOME", "CLAUDE_CONFIG_DIR", "PASEO_HOME"}
    }
    environment.update(PATH=f"{binaries}:/usr/bin:/bin", PASEO_RELOAD_LOG=str(reload_log),
                       PASEO_HOST="unrelated.invalid:9999")
    command = [shutil.which("make"), "-f", str(ROOT / "Makefile"), "paseo-agent-cleanup",
               f"DOTFILES={ROOT}", f"HOME={home}"]
    for _ in range(2):
        subprocess.run(command, env=environment, check=True, capture_output=True, text=True)
        current = json.loads(config.read_text())
        assert current["daemon"] == {**initial["daemon"], "enableTerminalAgentHooks": False}
        assert current["agents"]["skills"]["selection"] == {"mode": "custom", "skills": []}
        assert current["agents"]["providers"]["pi"] == pi
        for provider in ("claude", "codex"):
            assert current["agents"]["providers"][provider] == {
                **initial["agents"]["providers"][provider],
                "enabled": False, "paseoTools": {"enabled": False},
            }
        assert current["pluginsEnabled"] is True
        assert config.stat().st_mode & 0o777 == 0o640
        for filename in (".codex/hooks.json", ".claude/settings.json"):
            installed = home / filename
            assert installed.is_symlink()
            assert json.loads(installed.read_text()) == {"custom": "retain", "hooks": {
                "SessionStart": [{"matcher": "startup", "hooks": [keep]}], "Stop": [],
            }}
        for root in skill_roots:
            assert not list((home / root).glob("paseo*"))
            assert (home / root / "personal/SKILL.md").read_text() == "Personal instructions.\n"
        assert pi_settings.read_text() == '{"extensions":["paseo-questions.mjs"]}\n'
        assert (original_plugin / "SKILL.md").read_text() == "Original package.\n"
        archived = home / ".local/share/dotfiles/retired-paseo-skills"
        assert len(list(archived.rglob("SKILL.md"))) == 20
        assert all(path.read_text() == "Preserve local additions.\n"
                   for path in archived.rglob("my-notes.md"))
    reload_args = ["reload", "--home", str(config.parent), "--json"]
    assert reload_log.read_text().splitlines() == reload_args * 2

    current["daemon"]["enableTerminalAgentHooks"] = True
    config.write_text(json.dumps(current))
    failed_reload = subprocess.run(command, env={**environment, "PASEO_RELOAD_STATUS": "1"},
                                   check=True, capture_output=True, text=True)
    assert "settings saved; live Paseo reload failed" in failed_reload.stderr
    assert json.loads(config.read_text())["daemon"]["enableTerminalAgentHooks"] is False
    recovered = subprocess.run(command, env=environment, check=True, capture_output=True, text=True)
    assert "live Paseo reload failed" not in recovered.stderr
    assert reload_log.read_text().splitlines() == reload_args * 4

    linked_root = home / ".codex/skills"
    shutil.rmtree(linked_root)
    linked_root.symlink_to(original_plugin.parent)
    preserved = subprocess.run(command, env=environment, check=True, capture_output=True, text=True)
    assert "preserving linked skill tree" in preserved.stderr
    assert linked_root.is_symlink()
    assert (original_plugin / "SKILL.md").read_text() == "Original package.\n"
