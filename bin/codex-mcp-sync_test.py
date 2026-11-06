"""One detector for sharing Claude user and enabled plugin MCP servers with Codex."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parent.parent


def test_make_codex_preserves_curated_servers_and_local_configuration(tmp_path):
    repo = tmp_path / "dotfiles"
    home = tmp_path / "user"
    executables = tmp_path / "bin"
    executables.mkdir()
    (repo / "bin").mkdir(parents=True)
    (repo / ".claude").mkdir()
    (repo / "claude").mkdir()
    (repo / "codex").mkdir()
    (repo / "ai/skills").mkdir(parents=True)
    (repo / "ai/agents").mkdir()
    shutil.copytree(ROOT / "ai/skills/builder", repo / "ai/skills/builder")
    (home / ".claude/plugins").mkdir(parents=True)
    machine_config = home / ".config/dotfiles/config.toml"
    machine_config.parent.mkdir(parents=True)
    machine_config.write_text('sets = ["easypost"]\n')
    (home / ".codex").mkdir()
    (home / ".codex/config.toml").write_text(
        '# Local settings\nmodel = "local-model"\n'
        'developer_instructions = """\n[Review guidance]\n'
        'approval_policy = "leave this instruction alone"\n"""\n'
        'approval_policy = "never"\napprovals_reviewer = "user"\n'
        'sandbox_mode = "read-only"\n'
        '[apps.local]\napprovals_reviewer = "user"\n'
        '[apps.connector_76869538009648d5b282a4bb21c3d157]\n'
        'enabled = true # local GitHub setting\nopen_world_enabled = false\n'
        '[apps.connector_5f3c8c41a1e54ad7a76272c89e2554fa]\n'
        'enabled = true # local Drive setting\nopen_world_enabled = false\n'
        '[apps.asdk_app_69a1d78e929881919bba0dbda1f6436d]\n'
        'enabled = true # local Slack setting\nopen_world_enabled = false\n'
        '[apps.connector_openai_plugin_management]\nenabled = true\n'
        '[apps.connector_2de447f3f15448ebab48783d7e4f5d81]\nenabled = true\n'
        '[plugins."github@openai-curated"]\nenabled = true\n'
        '[plugins."github@openai-curated-remote"]\nenabled = true\n'
        '[plugins."google-drive@openai-curated-remote"]\nenabled = true\n'
        '[plugins."slack@openai-curated"]\nenabled = true\n'
        '[plugins."browser@openai-bundled"]\nenabled = true\n'
        '[plugins."plugin-management@openai-curated-remote"]\nenabled = true\n'
        '[plugins."openai-developers@openai-curated-remote"]\nenabled = true\n'
        '[plugins."chrome@openai-bundled"]\nenabled = true\n'
        '[plugins."retained@local"]\nenabled = false\n')

    for name in ("sync-codex-permissions", "sync-codex-mcp-servers", "sync-codex-skills",
                 "sync-codex-agents", "sync-claude-shared", "claude-remove-blocked-plugins"):
        (repo / "bin" / name).symlink_to(ROOT / "bin" / name)
    shutil.copy2(ROOT / "bin/sync-codex-tmux-hooks", repo / "bin/sync-codex-tmux-hooks")
    shutil.copy2(ROOT / "bin/codex-worktree-config", repo / "bin/codex-worktree-config")
    shutil.copy2(ROOT / "bin/codex-worktree-exit-hook", repo / "bin/codex-worktree-exit-hook")
    shutil.copy2(ROOT / "codex/tmux-hooks.json", repo / "codex/tmux-hooks.json")
    (repo / "codex/AGENTS.md").write_text("Fixture base guidance.\n")
    (repo / "codex/AGENTS.easypost.md").write_text("Fixture EasyPost guidance.\n")
    (repo / "scripts").mkdir()
    (repo / "scripts/install-software-standard.py").symlink_to(ROOT / "scripts/install-software-standard.py")
    (repo / "scripts/install-agent-status-broker").symlink_to(ROOT / "scripts/install-agent-status-broker")
    (repo / "bin/sync-agent-status-hooks").symlink_to(ROOT / "bin/sync-agent-status-hooks")
    # The external project's installer is a package boundary for this MCP
    # configuration workflow; its own tests exercise real installation.
    broker = executables / "agent-status-broker"
    # Keep the external installation in flight while make can schedule other
    # prerequisites; the hook installer must wait for the subsequent migration.
    broker.write_text("#!/bin/sh\n[ \"$1\" = install ] && [ \"$2\" = --no-start ] || exit 1\nsleep 1\n")
    broker.chmod(0o755)
    # Exercise macOS's bundled Bash too; the Codex CLI boundary is simulated below.
    (executables / "bash").symlink_to("/bin/bash")
    (executables / "python3").symlink_to(sys.executable)
    uname = executables / "uname"
    unavailable_hostname = ('#!/bin/sh\nif [ "$1" = -n ]; then\n'
                            '  exit 1\nelse\n'
                            f'  exec "{shutil.which("uname")}" "$@"\nfi\n')
    uname.write_text(unavailable_hostname)
    uname.chmod(0o755)
    # At the hook-installation boundary, migration must already have removed
    # Paseo's old handlers. Exercise that invariant with parallel make enabled.
    uv = executables / "uv"
    uv.write_text(f"#!{sys.executable}\n" + f'''
import os
from pathlib import Path
if any(argument.endswith("/sync-codex-permissions") for argument in os.sys.argv):
    enabled = os.sys.argv[os.sys.argv.index("--github-enabled") + 1]
    (Path.home() / ".codex/install-github-enabled").write_text(enabled)
else:
    assert "PASEO_HOOK_CLI" not in (Path.home() / ".codex/hooks.json").read_text(), "hook installation overlapped broker migration"
os.execv({shutil.which("uv")!r}, [{shutil.which("uv")!r}, *os.sys.argv[1:]])
''')
    uv.chmod(0o755)
    (executables / "jq").symlink_to(shutil.which("jq"))
    # This workflow has no plugins to remove; provide the Claude CLI boundary
    # required by the shared setup without invoking an installed user client.
    claude = executables / "claude"
    claude.write_text('#!/bin/sh\n[ "$*" = "plugin list --json" ] && echo "[]"\n')
    claude.chmod(0o755)
    paseo = executables / "paseo"
    paseo.write_text('#!/bin/sh\n[ "$1" = reload ] && touch "$HOME/paseo-reloaded"\n')
    paseo.chmod(0o755)
    (home / ".paseo").mkdir()
    (home / ".paseo/config.json").write_text(json.dumps({
        "daemon": {"enableTerminalAgentHooks": True, "retained": "kept"},
    }))
    (home / ".codex/hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [
        {"command": 'if [ -n "$PASEO_TERMINAL_ID" ]; then "${PASEO_HOOK_CLI:-paseo}" hooks codex PreToolUse; fi'},
        {"command": "printf retained"},
    ]}]}}))
    (repo / ".claude/settings.json").write_text(json.dumps({
        "enabledPlugins": {"search@local": True, "disabled@local": False},
    }))
    (repo / "claude/blocked-plugins.json").write_text("[]")
    plugin = home / ".claude/plugins/search/1.0"
    plugin.mkdir(parents=True)
    (plugin / ".mcp.json").write_text(json.dumps({
        "search": {"command": "python3", "args": ["${CLAUDE_PLUGIN_ROOT}/server.py"]},
        "playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]},
        "qmd": {"command": "plugin-override"},
    }))
    disabled = home / ".claude/plugins/disabled/1.0"
    disabled.mkdir(parents=True)
    (disabled / ".mcp.json").write_text(json.dumps({"disabled-tool": {"command": "disabled"}}))
    (home / ".claude/plugins/installed_plugins.json").write_text(json.dumps({
        "plugins": {
            "search@local": [{"scope": "user", "installPath": str(plugin)}],
            "disabled@local": [{"scope": "user", "installPath": str(disabled)}],
        },
    }))
    user_servers = {
        "workspace": {"command": "tool with spaces", "args": ["mcp", "arg with space", ""],
                      "env": {"REGION": "us west"}},
        "no-args": {"command": "standalone"},
        "qmd": {"type": "http", "url": "http://localhost:8181/mcp"},
        "kagi": {"type": "http", "url": "https://mcp.kagi.com/mcp",
                 "headers": {"Authorization": "Bearer ${KAGI_MCP_BEARER}"}},
    }
    (repo / ".claude/mcp-servers.json").write_text(json.dumps({
        "unwanted-default": {"command": "unwanted"},
    }))
    claude_config = {
        "mcpServers": {**user_servers, "codex": {"command": "codex", "args": ["mcp-server"]}},
        "localPreference": "retained",
    }
    (home / ".claude.json").write_text(json.dumps(claude_config))
    qmd = {"transport": {"type": "streamable_http", "url": "http://localhost:8181/mcp"},
           "enabled": False, "startup_timeout_sec": 42}
    state = home / ".codex/servers.json"
    state.write_text(json.dumps({"qmd": qmd, "codex-only": {"transport": {"command": "native"}}}))
    cli = executables / "codex"
    cli.write_text(f"#!{sys.executable}\n" + '''
import json, sys
from pathlib import Path
state = Path.home() / ".codex/servers.json"
servers = json.loads(state.read_text())
operation, name, *args = sys.argv[2:]
if operation == "get":
    if name not in servers:
        sys.exit(1)
    print(json.dumps(servers[name]))
elif operation == "add":
    if "--url" in args:
        transport = {"type": "streamable_http", "url": args[args.index("--url") + 1]}
        if "--bearer-token-env-var" in args:
            transport["bearer_token_env_var"] = args[args.index("--bearer-token-env-var") + 1]
    else:
        split = args.index("--")
        transport = {"type": "stdio", "command": args[split + 1], "args": args[split + 2:],
                     "env": dict(flag[len("--env="):].split("=", 1) for flag in args[:split])}
    servers[name] = {"transport": transport, "enabled": True}
    state.write_text(json.dumps(servers))
else:
    sys.exit(1)
''')
    cli.chmod(0o755)
    subprocess.run([shutil.which("git"), "init", "-q", str(repo)], check=True)
    env = dict(os.environ, PATH=f"{executables}:/usr/bin:/bin",
               UV="uv",
               DOTFILES_CONFIG=str(machine_config),
               AGENT_STATUS_INSTALL_FLAGS="--no-start",
               AGENT_STATUS_BIN=str(broker),
               UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache/uv")),
               HOME=str(home), CODEX_HOME=str(home / ".codex"),
               PASEO_HOME=str(home / ".paseo"), CLAUDE_CONFIG_DIR=str(home / ".claude"))
    env.pop("IS_EASYPOST", None)
    env.pop("BOOTSTRAP_MERMAID", None)
    command = [shutil.which("make"), "-j4", "-f", str(ROOT / "Makefile"),
               f"DOTFILES={repo}", f"HOME={home}"]
    original_config = (home / ".codex/config.toml").read_bytes()
    subprocess.run([*command, "codex-tmux"], cwd=repo, env=env,
                   check=True, capture_output=True, text=True)
    subprocess.run([*command, "codex"], cwd=repo, env=env,
                   check=True, capture_output=True, text=True)
    installed_config = (home / ".codex/config.toml").read_text()
    assert json.loads((home / ".claude.json").read_text()) == claude_config
    config = tomllib.loads(installed_config)
    assert (home / ".codex/AGENTS.md").read_text() == (
        "Fixture base guidance.\nFixture EasyPost guidance.\n")
    assert config["approval_policy"] == "on-request"
    assert config["approvals_reviewer"] == "auto_review"
    assert config["sandbox_mode"] == "workspace-write"
    assert config["model"] == "local-model"
    assert config["developer_instructions"] == (
        '[Review guidance]\napproval_policy = "leave this instruction alone"\n')
    assert config["apps"]["local"]["approvals_reviewer"] == "user"
    github = config["apps"]["connector_76869538009648d5b282a4bb21c3d157"]
    assert github["enabled"] is False
    assert github["open_world_enabled"] is False
    assert config["plugins"]["github@openai-curated"]["enabled"] is False
    assert config["plugins"]["github@openai-curated-remote"]["enabled"] is False
    drive = config["apps"]["connector_5f3c8c41a1e54ad7a76272c89e2554fa"]
    assert drive["enabled"] is False
    assert drive["open_world_enabled"] is False
    assert config["apps"]["connector_2128aebfecb84f64a069897515042a44"]["enabled"] is False
    assert config["apps"]["connector_947e0d954944416db111db556030eea6"]["enabled"] is False
    assert config["plugins"]["gmail@openai-curated-remote"]["enabled"] is False
    assert config["plugins"]["google-calendar@openai-curated"]["enabled"] is False
    assert config["plugins"]["google-calendar@openai-curated-remote"]["enabled"] is False
    assert config["plugins"]["google-drive@openai-curated"]["enabled"] is False
    assert config["plugins"]["google-drive@openai-curated-remote"]["enabled"] is False
    slack = config["apps"]["asdk_app_69a1d78e929881919bba0dbda1f6436d"]
    assert slack["enabled"] is False
    assert slack["open_world_enabled"] is False
    assert config["apps"]["connector_openai_plugin_management"]["enabled"] is False
    assert config["apps"]["connector_2de447f3f15448ebab48783d7e4f5d81"]["enabled"] is False
    assert config["plugins"]["slack@openai-curated"]["enabled"] is False
    assert config["plugins"]["browser@openai-bundled"]["enabled"] is False
    assert config["plugins"]["plugin-management@openai-curated-remote"]["enabled"] is False
    assert config["plugins"]["openai-developers@openai-curated-remote"]["enabled"] is False
    assert config["plugins"]["chrome@openai-bundled"]["enabled"] is True
    assert config["plugins"]["retained@local"]["enabled"] is False
    assert (home / ".codex/install-github-enabled").read_text() == "false"
    assert "# local GitHub setting" in installed_config
    assert "# local Drive setting" in installed_config
    assert "# local Slack setting" in installed_config
    assert "# Local settings" in installed_config
    assert json.loads((home / ".paseo/config.json").read_text())["daemon"] == {
        "enableTerminalAgentHooks": False, "retained": "kept"}
    assert (home / "paseo-reloaded").exists()
    installed_hooks = (home / ".codex/hooks.json").read_text()
    assert "printf retained" in installed_hooks and "PASEO_HOOK_CLI" not in installed_hooks
    desired_hooks = json.loads((repo / "codex/tmux-hooks.json").read_text())["hooks"]
    actual_hooks = json.loads(installed_hooks)["hooks"]
    assert all(group in actual_hooks[event]
               for event, groups in desired_hooks.items() for group in groups)

    servers = json.loads(state.read_text())
    assert servers == {"qmd": qmd, "codex-only": {"transport": {"command": "native"}}}
    assert json.loads((plugin / ".mcp.json").read_text())["playwright"]["args"] == [
        "@playwright/mcp@latest",
    ]

    # User removal and custom disabled settings survive repeated configuration.
    del servers["codex-only"]
    state.write_text(json.dumps(servers))
    previous_state = state.read_bytes()
    subprocess.run([*command, "codex"], cwd=repo, env=env,
                   check=True, capture_output=True, text=True)
    assert (home / ".codex/config.toml").read_text() == installed_config
    assert json.loads((home / ".claude.json").read_text()) == claude_config
    assert state.read_bytes() == previous_state
    assert (home / ".codex/hooks.json").read_text() == installed_hooks

    # NOTE: Explicit sets select integration policy and guidance without hostname detection.
    machine_config.write_text('sets = ["personal"]\n')
    (home / ".codex/config.toml").write_bytes(original_config)
    subprocess.run([*command, "codex-config"], cwd=repo,
                   env=env,
                   check=True, capture_output=True, text=True)
    personal_config = tomllib.loads((home / ".codex/config.toml").read_text())
    assert personal_config["apps"]["connector_76869538009648d5b282a4bb21c3d157"]["enabled"] is True
    assert personal_config["plugins"]["github@openai-curated"]["enabled"] is True
    assert personal_config["plugins"]["github@openai-curated-remote"]["enabled"] is True
    assert (home / ".codex/install-github-enabled").read_text() == "true"
    expected_personal = tomllib.loads(original_config.decode())
    expected_personal.update({
        "approval_policy": "on-request",
        "approvals_reviewer": "auto_review",
        "sandbox_mode": "workspace-write",
    })
    assert personal_config == expected_personal, "personal setup changed integration preferences"
    assert (home / ".codex/AGENTS.md").read_text() == "Fixture base guidance.\n"
    assert state.read_bytes() == previous_state
    assert (home / ".codex/hooks.json").read_text() == installed_hooks
    claude_config["mcpServers"] = {}
    (home / ".claude.json").write_text(json.dumps(claude_config))
    subprocess.run([*command, "claude-config"], cwd=repo, env=env,
                   check=True, capture_output=True, text=True)
    assert json.loads((home / ".claude.json").read_text()) == claude_config

    (repo / "codex-mcp").touch()
    retired = subprocess.run([*command, "codex-mcp"], cwd=repo, env=env,
                             capture_output=True, text=True)
    assert retired.returncode != 0 and "user-managed" in retired.stderr
    direct = subprocess.run([str(repo / "bin/sync-codex-mcp-servers")],
                            cwd=repo, env=env, capture_output=True, text=True)
    assert direct.returncode != 0 and "user-managed" in direct.stderr
    assert state.read_bytes() == previous_state
