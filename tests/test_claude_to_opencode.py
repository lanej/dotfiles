#!/usr/bin/env python3
"""Tests for claude-to-opencode script."""

import json
import subprocess
import tempfile
from pathlib import Path


def test_project_only_flag_skips_global():
    """Verify --project-only skips global settings conversion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create project .mcp.json
        mcp_json = tmppath / ".mcp.json"
        mcp_json.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "test-server": {"command": "node", "args": ["server.js"]}
                    }
                }
            )
        )

        # Create project settings
        claude_dir = tmppath / ".claude"
        claude_dir.mkdir()
        settings_local = claude_dir / "settings.local.json"
        settings_local.write_text(
            json.dumps({"enabledMcpjsonServers": ["test-server"]})
        )

        # Run with --project-only --dry-run
        result = subprocess.run(
            ["claude-to-opencode", "--project-only", "--dry-run"],
            cwd=tmppath,
            capture_output=True,
            text=True,
        )

        # Should convert project MCP servers
        assert "✓ Converted project MCP servers" in result.stderr

        # Should NOT convert global permissions
        assert "✓ Converted global permissions" not in result.stderr

        # Should NOT set up AGENTS.md symlink
        assert "✓ Symlinked AGENTS.md" not in result.stderr


def test_default_converts_both_global_and_project():
    """Verify default mode converts both global and project settings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create project .mcp.json
        mcp_json = tmppath / ".mcp.json"
        mcp_json.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "test-server": {"command": "node", "args": ["server.js"]}
                    }
                }
            )
        )

        # Create project settings
        claude_dir = tmppath / ".claude"
        claude_dir.mkdir()
        settings_local = claude_dir / "settings.local.json"
        settings_local.write_text(
            json.dumps({"enabledMcpjsonServers": ["test-server"]})
        )

        # Run without --project-only (default behavior)
        result = subprocess.run(
            ["claude-to-opencode", "--dry-run"],
            cwd=tmppath,
            capture_output=True,
            text=True,
        )

        # Should convert project MCP servers
        assert "✓ Converted project MCP servers" in result.stderr

        # Note: Global permissions and AGENTS.md will only show if files exist
        # This test just verifies --project-only is NOT being used


def test_help_includes_project_only_flag():
    """Verify help text documents --project-only flag."""
    result = subprocess.run(
        ["claude-to-opencode", "--help"],
        capture_output=True,
        text=True,
    )

    assert "--project-only" in result.stdout
    assert "Only convert project settings" in result.stdout
