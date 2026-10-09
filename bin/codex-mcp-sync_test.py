"""One detector for sharing Claude user and enabled plugin MCP servers with Codex."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def test_make_codex_shares_servers_and_preserves_local_configuration(tmp_path):
    repo = tmp_path / "dotfiles"
    home = tmp_path / "user"
    executables = tmp_path / "bin"
    executables.mkdir()
    (repo / "bin").mkdir(parents=True)
    (repo / ".claude").mkdir()
    (repo / "claude").mkdir()
    (repo / "codex").mkdir()
    (home / ".claude/plugins").mkdir(parents=True)
    (home / ".codex").mkdir()

    for name in ("sync-codex-mcp-servers", "sync-codex-skills",
                 "sync-codex-agents", "claude-remove-blocked-plugins"):
        (repo / "bin" / name).symlink_to(ROOT / "bin" / name)
    shutil.copy2(ROOT / "bin/sync-codex-tmux-hooks", repo / "bin/sync-codex-tmux-hooks")
    shutil.copy2(ROOT / "codex/tmux-hooks.json", repo / "codex/tmux-hooks.json")
    shutil.copy2(ROOT / "codex/AGENTS.md", repo / "codex/AGENTS.md")
    (repo / "scripts").mkdir()
    (repo / "scripts/install-agent-status-broker").symlink_to(ROOT / "scripts/install-agent-status-broker")
    (repo / "bin/sync-agent-status-hooks").symlink_to(ROOT / "bin/sync-agent-status-hooks")
    # The external project's installer is a package boundary for this MCP
    # configuration workflow; its own tests exercise real installation.
    broker = executables / "agent-status-broker"
    broker.write_text("#!/bin/sh\n[ \"$1\" = install ] && [ \"$2\" = --no-start ]\n")
    broker.chmod(0o755)
    # Exercise macOS's bundled Bash too; the Codex CLI boundary is simulated below.
    (executables / "bash").symlink_to("/bin/bash")
    (executables / "python3").symlink_to(sys.executable)
    (executables / "uv").symlink_to(shutil.which("uv"))
    (executables / "jq").symlink_to(shutil.which("jq"))
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
    (repo / ".claude/mcp-servers.json").write_text(json.dumps({
        "workspace": {"command": "tool with spaces", "args": ["mcp", "arg with space", ""],
                      "env": {"REGION": "us west"}},
        "no-args": {"command": "standalone"},
        "qmd": {"type": "http", "url": "http://localhost:8181/mcp"},
        "kagi": {"type": "http", "url": "https://mcp.kagi.com/mcp",
                 "headers": {"Authorization": "Bearer ${KAGI_MCP_BEARER}"}},
    }))
    (home / ".claude.json").write_text(json.dumps({
        "mcpServers": {"codex": {"command": "codex", "args": ["mcp-server"]}},
    }))
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
               AGENT_STATUS_INSTALL_FLAGS="--no-start",
               AGENT_STATUS_BIN=str(broker),
               UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache/uv")),
               HOME=str(home), CODEX_HOME=str(home / ".codex"),
               PASEO_HOME=str(home / ".paseo"), CLAUDE_CONFIG_DIR=str(home / ".claude"))
    command = [shutil.which("make"), "-f", str(ROOT / "Makefile"), "codex",
               f"DOTFILES={repo}", f"HOME={home}"]
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert json.loads((home / ".paseo/config.json").read_text())["daemon"] == {
        "enableTerminalAgentHooks": False, "retained": "kept"}
    assert (home / "paseo-reloaded").exists()
    installed_hooks = (home / ".codex/hooks.json").read_text()
    assert "printf retained" in installed_hooks and "PASEO_HOOK_CLI" not in installed_hooks

    servers = json.loads(state.read_text())
    assert servers["workspace"]["transport"] == {
        "type": "stdio", "command": "tool with spaces", "args": ["mcp", "arg with space", ""],
        "env": {"REGION": "us west"},
    }
    assert servers["no-args"]["transport"]["args"] == []
    assert servers["kagi"]["transport"]["bearer_token_env_var"] == "KAGI_MCP_BEARER"
    assert servers["qmd"] == qmd
    assert servers["search"]["transport"] == {
        "type": "stdio", "command": "python3", "args": [str(plugin / "server.py")],
        "env": {"CLAUDE_PLUGIN_ROOT": str(plugin)},
    }
    assert "codex-only" in servers and "codex" not in servers and "disabled-tool" not in servers

    servers["workspace"]["enabled"] = False
    state.write_text(json.dumps(servers))
    previous_state = state.read_bytes()
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert state.read_bytes() == previous_state
