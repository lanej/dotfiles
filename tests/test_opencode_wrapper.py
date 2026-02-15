#!/usr/bin/env python3
"""Tests for opencode-wrapper script."""

import subprocess
import tempfile
from pathlib import Path


def test_wrapper_suppresses_output_with_mcp_json():
    """Verify opencode-wrapper produces no output when .mcp.json exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create a minimal .mcp.json
        mcp_json = tmppath / ".mcp.json"
        mcp_json.write_text('{"mcpServers": {}}')

        # Run wrapper with --version to avoid actually starting opencode
        # (wrapper will convert .mcp.json then exec opencode --version)
        result = subprocess.run(
            ["opencode-wrapper", "--version"],
            cwd=tmppath,
            capture_output=True,
            text=True,
        )

        # Should have no conversion messages in stderr
        assert "🔄" not in result.stderr, "Wrapper should not output conversion message"
        assert "Found .mcp.json" not in result.stderr
        assert "✓" not in result.stderr
        assert "Converting" not in result.stderr

        # opencode --version output should still appear in stdout
        assert "opencode" in result.stdout.lower() or result.returncode == 0


def test_wrapper_uses_project_only_flag():
    """Verify wrapper calls claude-to-opencode with --project-only flag."""
    # Read the wrapper script
    wrapper_path = Path.home() / ".files" / "bin" / "opencode-wrapper"
    wrapper_content = wrapper_path.read_text()

    # Verify it uses --project-only flag
    assert "--project-only" in wrapper_content, "Wrapper should use --project-only flag"
    assert "claude-to-opencode --project-only" in wrapper_content


def test_wrapper_runs_without_mcp_json():
    """Verify opencode-wrapper works normally when .mcp.json doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["opencode-wrapper", "--version"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )

        # Should work fine without .mcp.json
        assert result.returncode == 0 or "opencode" in result.stdout.lower()

        # No conversion messages
        assert "🔄" not in result.stderr
        assert ".mcp.json" not in result.stderr
