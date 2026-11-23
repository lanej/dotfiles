"""Focused installation and native-policy checks for Octo command allowances."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib


ROOT = Path(__file__).resolve().parent.parent


def test_make_codex_permissions_installs_preserves_and_refreshes_rules(tmp_path):
    home = tmp_path / "home"
    codex_home = home / "custom-codex"
    codex_home.mkdir(parents=True)
    config = codex_home / "config.toml"
    original = (
        '# Retained local settings\nmodel = "local-model"\n'
        'approval_policy = "on-request"\napprovals_reviewer = "auto_review"\n'
        'sandbox_mode = "workspace-write"\n'
        '[apps.connector_76869538009648d5b282a4bb21c3d157]\nenabled = true\n'
        '[plugins."github@openai-curated"]\nenabled = true\n'
        '[plugins."github@openai-curated-remote"]\nenabled = true\n'
    )
    config.write_text(original)
    config.chmod(0o640)
    rules = codex_home / "rules/octo-manager.rules"
    rules.parent.mkdir()
    retained = (
        '# Authored rule stays intact\n'
        'prefix_rule(pattern=["octo-manager", "ack"], decision="prompt")\n'
    )
    rules.write_text(retained)
    rules.chmod(0o640)
    other = rules.parent / "default.rules"
    other.write_text('prefix_rule(pattern=["custom-tool"], decision="allow")\n')
    machine = tmp_path / "machine.toml"
    machine.write_text('sets = ["personal"]\n')
    env = dict(os.environ, HOME=str(home), CODEX_HOME=str(codex_home),
               DOTFILES_CONFIG=str(machine),
               UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache/uv")))
    command = [
        shutil.which("make"), "--no-print-directory", "-f", str(ROOT / "Makefile"),
        f"DOTFILES={ROOT}", f"HOME={home}", f"UV={shutil.which('uv')}",
        "codex-permissions",
    ]

    def install():
        return subprocess.run(command, cwd=ROOT, env=env, check=True,
                              capture_output=True, text=True, timeout=60)

    install()
    installed = rules.read_text()
    assert installed != retained, "configuration must install the managed allowances"
    assert installed.startswith(retained)
    assert config.read_text() == original, "rule installation must run even with current config"
    assert rules.stat().st_mode & 0o777 == 0o640
    assert config.stat().st_mode & 0o777 == 0o640
    assert other.read_text() == 'prefix_rule(pattern=["custom-tool"], decision="allow")\n'
    assert tomllib.loads(config.read_text())["sandbox_mode"] == "workspace-write"
    assert not (home / ".codex").exists(), "CODEX_HOME must select the rule destination"

    # The real engine checks behavior when the native client is available.
    # CI still exercises installation without requiring a Codex download/login.
    codex = shutil.which("codex")
    if codex:
        def decision(*arguments):
            result = subprocess.run(
                [codex, "execpolicy", "check", "--rules", str(rules), "--", *arguments],
                env=env, check=True, capture_output=True, text=True, timeout=10,
            )
            return json.loads(result.stdout).get("decision")

        launcher = str(home / ".local/bin/octo-manager")
        for executable in ("octo-manager", launcher):
            assert decision(executable, "inbox", "--agent-id", "owner") == "allow"
            assert decision(executable, "pr", "show", "44") == "allow"
            assert decision(executable, "publication", "show", "receipt") == "allow"
            assert decision(executable, "record-activity", "--name", "run_checks") == "allow"
            assert decision(executable, "activity", "record", "--name", "run_checks") == "allow"
            assert decision(executable, "messages", "ack", "receipt") == "allow"
            for arguments in (
                ("read", "receipt"),
                ("assessment", "show", "assessment"),
                ("issue", "list"),
                ("issue", "show", "issue"),
                ("history", "submissions"),
                ("history", "submission", "receipt"),
                ("history", "policy", "lanej/octo-manager"),
                ("repair", "list"),
                ("conflict", "list"),
                ("conflict", "show", "1"),
            ):
                assert decision(executable, *arguments) == "allow", arguments
            for arguments in (
                ("submit-pr", "--title", "publish"),
                ("pr", "publish"),
                ("pr", "ready", "44"),
                ("pr", "auto-merge", "44", "--on"),
                ("publication", "retry", "receipt"),
                ("merge-ready", "44"),
                ("auto-merge", "44", "--on"),
                ("chain", "queue"),
                ("action", "retry-delivery", "44"),
                ("serve",),
                ("pr", "44"),
                ("merge", "receipt"),
                ("messages", "merge", "receipt"),
                ("assessment", "retry", "assessment"),
                ("issue", "track", "https://github.com/lanej/octo-manager/issues/1"),
                ("issue", "approve", "issue"),
                ("issue", "approve-publication", "issue"),
                ("issue", "approve-follow-up", "issue"),
                ("issue", "answer", "issue"),
                ("issue", "pause", "issue"),
                ("issue", "resume", "issue"),
                ("issue", "cancel", "issue"),
                ("issue", "refresh", "issue"),
                ("repair", "rebase"),
                ("dependency", "confirm"),
                ("reference", "dismiss", "reference"),
            ):
                assert decision(executable, *arguments) != "allow", arguments
        assert decision("octo-manager", "ack", "receipt") == "prompt"
        assert decision(launcher, "ack", "receipt") == "allow"
        assert decision("another-manager", "inbox") != "allow"

    install()
    assert rules.read_text() == installed, "repeated configuration must not duplicate rules"
    # An obsolete managed block is refreshed, while the authored prompt survives.
    start = installed.index("# BEGIN dotfiles Octo Manager rules\n")
    end = installed.index("# END dotfiles Octo Manager rules\n")
    stale = installed[:start] + "# BEGIN dotfiles Octo Manager rules\n" + installed[end:]
    rules.write_text(stale)
    install()
    assert rules.read_text() == installed

    rules.write_text(installed.replace("# END dotfiles Octo Manager rules\n", ""))
    broken = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                            text=True, timeout=60)
    assert broken.returncode != 0 and "malformed managed Octo rules block" in broken.stderr
    assert config.read_text() == original
