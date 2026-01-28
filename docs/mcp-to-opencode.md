# OpenCode Auto-Configuration

Automatically configures OpenCode to match your existing Claude Code and project setups.

## Features

1. **MCP Server Conversion** - Converts `.mcp.json` files to OpenCode MCP configuration
2. **CLAUDE.md Symlink** - `~/.config/opencode/AGENTS.md` → `~/.claude/CLAUDE.md` (always in sync)

## Overview

This setup provides seamless integration between OpenCode and your existing Claude Code configuration:

**MCP Servers:** Many tools (like Claude Desktop, Cline, etc.) use `.mcp.json` format. This utility automatically detects and converts these files to OpenCode's `opencode.json` format.

**Rules/Instructions:** `~/.config/opencode/AGENTS.md` is symlinked to `~/.claude/CLAUDE.md`, so both tools use the same rules automatically. Edit `~/.claude/CLAUDE.md` and both Claude Code and OpenCode see the changes immediately.

## How It Works

1. When you run `opencode` in a directory with `.mcp.json`
2. The script checks if `.mcp.json` has changed since last conversion (using SHA256 hash)
3. **If unchanged:** Silent skip, starts OpenCode immediately (no output)
4. **If changed:** Converts MCP servers and merges into `~/.config/opencode/opencode.json`
5. Starts OpenCode with the updated configuration

**Smart Caching:** Conversions are tracked in `~/.cache/opencode/mcp-conversions.json` to avoid redundant work.

## Installation

Already installed! The following components are set up:

**Scripts:**
- `~/.files/bin/mcp-to-opencode` - Conversion utility
- `~/.files/shell/functions/opencode.zsh` - Shell wrapper function

**Configuration:**
- `~/.zshrc` - Sources the opencode function automatically

## Usage

### Automatic Conversion

Just use `opencode` normally:

```bash
cd ~/workspace  # Has .mcp.json with gspace, pkm, bigquery, jira
opencode        # Auto-converts on first run or when .mcp.json changes
```

**First run or when .mcp.json changed:**
```
🔄 Converting .mcp.json to OpenCode format...
📖 Reading MCP servers from: /Users/user/workspace/.mcp.json
  Found 4 server(s): gspace, pkm, bigquery, jira
  ✓ Converted 'gspace'
  ✓ Converted 'pkm'  
  ✓ Converted 'bigquery'
  ✓ Converted 'jira'

[OpenCode starts with MCP servers available]
```

**Subsequent runs (file unchanged):**
```
[OpenCode starts immediately - no conversion output]
```

The script is completely silent when `.mcp.json` hasn't changed, ensuring fast startup.

### Manual Conversion

Convert without starting OpenCode:

```bash
# Current directory .mcp.json (silent if unchanged)
mcp-to-opencode

# Specific file
mcp-to-opencode /path/to/.mcp.json

# Dry run (preview changes, always shows output)
mcp-to-opencode --dry-run

# Force conversion even if unchanged
mcp-to-opencode --force
```

## Format Conversion

### Input Format (.mcp.json)

```json
{
  "mcpServers": {
    "server-name": {
      "command": "command-name",
      "args": ["arg1", "arg2"],
      "env": {
        "KEY": "value"
      }
    }
  }
}
```

### Output Format (opencode.json mcp section)

```json
{
  "mcp": {
    "server-name": {
      "type": "local",
      "command": ["command-name", "arg1", "arg2"],
      "enabled": true,
      "environment": {
        "KEY": "value"
      }
    }
  }
}
```

## Examples

### Example 1: Simple Command

**.mcp.json:**
```json
{
  "mcpServers": {
    "gspace": {
      "command": "gspace",
      "args": ["mcp", "stdio"]
    }
  }
}
```

**Converts to:**
```json
{
  "mcp": {
    "gspace": {
      "type": "local",
      "command": ["gspace", "mcp", "stdio"],
      "enabled": true
    }
  }
}
```

### Example 2: With Environment Variables

**.mcp.json:**
```json
{
  "mcpServers": {
    "my-server": {
      "command": "my-server",
      "args": ["start"],
      "env": {
        "API_KEY": "secret",
        "DEBUG": "true"
      }
    }
  }
}
```

**Converts to:**
```json
{
  "mcp": {
    "my-server": {
      "type": "local",
      "command": ["my-server", "start"],
      "enabled": true,
      "environment": {
        "API_KEY": "secret",
        "DEBUG": "true"
      }
    }
  }
}
```

### Example 3: Docker/Podman Container

**.mcp.json:**
```json
{
  "mcpServers": {
    "jira": {
      "command": "podman",
      "args": [
        "run", "-i", "--rm",
        "-v", "/Users/user/.config/mcp/jira.env:/etc/mcp/jira.env",
        "ghcr.io/sooperset/mcp-atlassian:latest",
        "--env-file", "/etc/mcp/jira.env"
      ]
    }
  }
}
```

**Converts to:**
```json
{
  "mcp": {
    "jira": {
      "type": "local",
      "command": [
        "podman", "run", "-i", "--rm",
        "-v", "/Users/user/.config/mcp/jira.env:/etc/mcp/jira.env",
        "ghcr.io/sooperset/mcp-atlassian:latest",
        "--env-file", "/etc/mcp/jira.env"
      ],
      "enabled": true
    }
  }
}
```

## Behavior

### Smart Caching

The utility tracks converted files using SHA256 hashes stored in `~/.cache/opencode/mcp-conversions.json`:

- **File unchanged:** Silent skip (no conversion, no output)
- **File changed:** Automatic conversion with output
- **Cache miss:** First-time conversion with output

**Performance Benefits:**
- Zero overhead when `.mcp.json` hasn't changed
- Fast OpenCode startup (no unnecessary JSON parsing/merging)
- Automatic detection of changes (edit .mcp.json → auto-reconverts)

**Force Reconversion:**
```bash
mcp-to-opencode --force  # Bypass cache, always convert
```

**Clear Cache:**
```bash
rm ~/.cache/opencode/mcp-conversions.json  # Reset all conversion tracking
```

### Merging Strategy

- **New servers:** Added to OpenCode config automatically
- **Existing servers:** Skipped with warning (preserves your OpenCode customizations)
- **Conflicts:** Shows `⚠️ Skipping 'name' (already exists in config)`

**Example:** If `gspace` already exists in OpenCode config with custom settings, conversion won't overwrite it.

### To Override Existing Servers

If you want to update an existing server:

1. Remove it from `~/.config/opencode/opencode.json` manually, or
2. Use `--force` flag and manually edit the result

## Troubleshooting

### Script Not Found

If `mcp-to-opencode` command not found:

```bash
# Ensure .files/bin is in PATH
echo $PATH | grep ".files/bin"

# Or use direct path
~/.files/bin/mcp-to-opencode
```

### No Auto-Conversion

If opencode doesn't auto-convert:

```bash
# Reload shell configuration
source ~/.zshrc

# Verify function is loaded
type opencode
# Should show: "opencode is a shell function"

# If shows: "opencode is /path/to/opencode"
# Then function isn't loaded, check ~/.zshrc
```

### Conversion Errors

Check the error message:

```bash
# Dry run to see what would happen
mcp-to-opencode --dry-run

# Check .mcp.json format
cat .mcp.json | jq .

# Verify OpenCode config is valid JSON
cat ~/.config/opencode/opencode.json | jq .
```

## Configuration Options

### Disable Auto-Conversion

If you don't want automatic conversion:

**Option 1:** Remove function from ~/.zshrc
```bash
# Comment out or remove these lines:
# if [[ -f ~/.files/shell/functions/opencode.zsh ]]; then
#     source ~/.files/shell/functions/opencode.zsh
# fi
```

**Option 2:** Use command directly
```bash
command opencode  # Bypasses shell function
```

### Convert on Demand Only

```bash
# Use alias for manual conversion
alias oc-convert='mcp-to-opencode'

# Then manually convert when needed
oc-convert && opencode
```

## Integration with Other Tools

This utility is compatible with `.mcp.json` files created by:

- **Claude Desktop** - Official Anthropic desktop app
- **Cline** - VSCode extension  
- **Continue** - VSCode/JetBrains extension
- **Zed AI** - Zed editor
- **Any tool** using standard MCP JSON format

## Advanced Usage

### Batch Convert Multiple Projects

```bash
# Find all .mcp.json files and convert
find ~/src -name ".mcp.json" -exec mcp-to-opencode {} \;
```

### Create Project-Specific Config

Instead of global conversion, create project-specific OpenCode config:

1. Copy converted MCP section
2. Create `.opencode/` directory in project
3. Save as `<project>/.opencode/config.json`

```bash
# In project directory
mcp-to-opencode --dry-run | jq .mcp > .opencode/mcp-servers.json
```

## See Also

- OpenCode MCP Documentation: https://opencode.ai/docs/mcp-servers/
- MCP Specification: https://modelcontextprotocol.io
- Your MCP Servers: `~/.config/opencode/opencode.json`

## CLAUDE.md Symlink

### Setup

OpenCode's `AGENTS.md` is symlinked to your Claude Code `CLAUDE.md`:

```bash
~/.config/opencode/AGENTS.md -> ~/.claude/CLAUDE.md
```

**Benefits:**
- Single source of truth - edit `~/.claude/CLAUDE.md`
- Always in sync - no conversion needed
- Zero overhead - instant updates
- Works across both tools

### Verification

Check the symlink:
```bash
ls -la ~/.config/opencode/AGENTS.md
# Should show: lrwxr-xr-x ... AGENTS.md -> /Users/user/.claude/CLAUDE.md
```

### Usage

Just edit your CLAUDE.md - both tools see changes immediately:

```bash
vim ~/.claude/CLAUDE.md
# Changes are live in both Claude Code and OpenCode instantly
```

### Recreate Symlink

If the symlink gets broken:

```bash
rm ~/.config/opencode/AGENTS.md
ln -s ~/.claude/CLAUDE.md ~/.config/opencode/AGENTS.md
```

