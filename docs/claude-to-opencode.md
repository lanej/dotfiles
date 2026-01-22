# Claude Code to OpenCode Auto-Conversion

Comprehensive automatic conversion of all Claude Code configuration to OpenCode format on startup.

## Overview

This utility performs a complete migration of your Claude Code setup to OpenCode:

**Converted Settings:**
- ✅ Global permissions (`~/.claude/settings.json` → `permission`)
- ✅ LSP servers (`enabledPlugins` → `lsp`)
- ✅ MCP servers (`.mcp.json` + `enabledMcpjsonServers` → `mcp`)
- ✅ Instructions (`CLAUDE.md` → `AGENTS.md` symlink)

**Smart Features:**
- Hash-based caching (only converts when files change)
- Silentimportant when unchanged
- Project-aware (detects project-level settings)
- Preserves existing OpenCode customizations

## Configuration Sources

### Global Settings

**Source:** `~/.claude/settings.json`

**Converts:**
1. **Permissions** → `permission` in `opencode.json`
   - `allow: ["Bash"]` → `bash: "allow"`
   - `deny: ["Bash(rm:-rf /)"]` → `bash: {"rm -rf /": "deny"}`
   - `defaultMode: "acceptEdits"` → `edit: "allow"`, `write: "allow"`

2. **LSP Servers** → `lsp` in `opencode.json`
   - `gopls-lsp@claude-plugins-official` → `gopls: {enabled: true}`
   - `rust-analyzer-lsp@...` → `rust-analyzer: {enabled: true}`

3. **CLAUDE.md** → Symlinked to `AGENTS.md`
   - `~/.claude/CLAUDE.md` ← → `~/.config/opencode/AGENTS.md`
   - Single source of truth, always in sync

### Project Settings

**Discovered by traversing up from current directory until:**
- Git root (`.git` directory)
- Home directory
- Match found

**Sources Checked (in order):**

1. **`./.claude/settings.local.json`**
   - Contains `enabledMcpjsonServers` list
   - Filters which MCP servers are enabled for this project

2. **`./.mcp.json`** or `../.mcp.json` (traverses up)
   - MCP server definitions
   - Combined with `enabledMcpjsonServers` filter

3. **`./.claude/CLAUDE.md`** or `./CLAUDE.md`
   - Project-specific instructions
   - OpenCode reads these automatically (no conversion needed)

## How It Works

### Initialization

When you run `opencode`:

1. Calculate hash of all Claude config files:
   - `~/.claude/settings.json`
   - `./.claude/settings.local.json` (if exists)
   - `./.mcp.json` (if exists)

2. Compare with cached hash (`~/.cache/opencode/claude-to-opencode.hash`)

3. **If unchanged:** Silent skip, start OpenCode immediately

4. **If changed:** Convert and merge into `opencode.json`

### Conversion Process

**Step 1: Load existing OpenCode config**
```
~/.config/opencode/opencode.json
```

**Step 2: Convert global settings**
- Parse `~/.claude/settings.json`
- Extract permissions, LSP servers
- Convert to OpenCode format

**Step 3: Convert project settings**
- Find `.claude/settings.local.json` (enabled MCP servers)
- Find `.mcp.json` (MCP server definitions)
- Merge enabled servers only

**Step 4: Setup AGENTS.md**
- Create symlink if needed:
  ```
  ~/.config/opencode/AGENTS.md → ~/.claude/CLAUDE.md
  ```

**Step 5: Merge and save**
- Deep merge with existing config (preserves customizations)
- Save to `~/.config/opencode/opencode.json`
- Update hash cache

## Setup

### Via Dotfiles Makefile (Recommended)

If you use the `.files` repository, OpenCode is fully integrated:

```bash
# Initial setup (on new machine)
cd ~/.files
make claude    # Sets up Claude Code with symlinks
make opencode  # Sets up OpenCode with symlinks + conversion

# Or run both
make claude opencode
```

**What `make opencode` does:**

1. **Creates symlinks:**
   - `~/.config/opencode/opencode.json` → `~/.files/.opencode/opencode.json`
   - `~/.config/opencode/commands` → `~/.files/.opencode/commands`
   - `~/.config/opencode/AGENTS.md` → `~/.claude/CLAUDE.md`

2. **Runs converter:**
   - Converts Claude settings to OpenCode format
   - Merges with base config
   - Uses smart caching (silent if unchanged)

**Symlink Chain:**

```
~/.files/claude/CLAUDE.md (master, versioned)
    ↓ (created by `make claude`)
~/.claude/CLAUDE.md (symlink)
    ↓ (created by `make opencode`)
~/.config/opencode/AGENTS.md (symlink)
```

**Result:** Single source of truth - edit `~/.files/claude/CLAUDE.md` and both tools see changes immediately.

## Usage

### Automatic (Recommended)

Just use `opencode` - conversion happens automatically:

```bash
# First run or after editing Claude settings
opencode
# Output:
# 🔄 Converting Claude Code configuration to OpenCode...
#   ✓ Converted global permissions and LSP settings
#   ✓ Converted project MCP servers
#   💾 Saved to ~/.config/opencode/opencode.json

# Subsequent runs (nothing changed)
opencode
# [silent - starts immediately]
```

### Manual Conversion

```bash
# Convert now
claude-to-opencode

# Preview changes without applying
claude-to-opencode --dry-run

# Force conversion even if unchanged
claude-to-opencode --force

# Only convert global settings
claude-to-opencode --global
```

## Example Conversions

### Example 1: Basic Permissions

**Claude Code (`~/.claude/settings.json`):**
```json
{
  "permissions": {
    "allow": ["Bash"],
    "deny": [
      "Bash(rm:-rf /)",
      "Bash(sudo:rm:*)"
    ],
    "defaultMode": "acceptEdits"
  }
}
```

**OpenCode (`~/.config/opencode/opencode.json`):**
```json
{
  "permission": {
    "bash": {
      "rm -rf /": "deny",
      "sudo rm *": "deny"
    },
    "edit": "allow",
    "write": "allow"
  }
}
```

### Example 2: LSP Servers

**Claude Code:**
```json
{
  "enabledPlugins": {
    "gopls-lsp@claude-plugins-official": true,
    "rust-analyzer-lsp@claude-plugins-official": true,
    "typescript-lsp@claude-plugins-official": true
  }
}
```

**OpenCode:**
```json
{
  "lsp": {
    "gopls": {"enabled": true},
    "rust-analyzer": {"enabled": true},
    "typescript": {"enabled": true}
  }
}
```

### Example 3: Project MCP Servers

**Claude Code (`./.claude/settings.local.json`):**
```json
{
  "enabledMcpjsonServers": ["gspace", "pkm"]
}
```

**Claude Code (`./.mcp.json` - parent directory):**
```json
{
  "mcpServers": {
    "gspace": {
      "command": "gspace",
      "args": ["mcp", "stdio"]
    },
    "pkm": {
      "command": "pkm",
      "args": ["mcp"]
    },
    "jira": {
      "command": "podman",
      "args": ["run", "-i", "..."]
    }
  }
}
```

**OpenCode (only enabled servers):**
```json
{
  "mcp": {
    "gspace": {
      "type": "local",
      "command": ["gspace", "mcp", "stdio"],
      "enabled": true
    },
    "pkm": {
      "type": "local",
      "command": ["pkm", "mcp"],
      "enabled": true
    }
  }
}
```

Note: `jira` is NOT included because it's not in `enabledMcpjsonServers`.

## File Structure

### With Dotfiles Integration (Recommended)

```
~/.files/                         # Dotfiles repository
├── claude/
│   ├── CLAUDE.md                 # Master instructions (edit this, versioned)
│   ├── agents/                   # Agent definitions
│   ├── commands/                 # Slash commands
│   └── skills/                   # Skill documentation
├── .claude/
│   └── settings.json             # Global settings (versioned)
├── .opencode/
│   ├── opencode.json             # Base config (versioned)
│   └── commands/                 # Writing commands (versioned)
└── bin/
    └── claude-to-opencode        # Converter script

~/.claude/                        # Created by `make claude`
├── CLAUDE.md → ~/.files/claude/CLAUDE.md  # Symlink
├── settings.json → ~/.files/.claude/settings.json  # Symlink
├── agents/ → ~/.files/claude/agents/      # Symlink
├── commands/ → ~/.files/claude/commands/  # Symlink
└── skills/ → ~/.files/claude/skills/      # Symlink

~/.config/opencode/               # Created by `make opencode`
├── opencode.json → ~/.files/.opencode/opencode.json  # Symlink
├── commands/ → ~/.files/.opencode/commands/          # Symlink
├── skills/ → ~/.claude/skills/                       # Symlink
└── AGENTS.md → ~/.claude/CLAUDE.md                   # Symlink

~/.cache/opencode/
└── claude-to-opencode.hash       # Conversion cache

Project/.claude/                  # Project-specific config
├── CLAUDE.md                     # Project instructions
└── settings.local.json           # Enabled MCP servers

Project/
├── .mcp.json                     # MCP server definitions
└── CLAUDE.md                     # Alternative location
```

### Without Dotfiles Integration

```
~/.claude/
├── CLAUDE.md                     # Master instructions (edit this)
├── settings.json                 # Global permissions, LSP, hooks
└── ... (agents, commands, etc.)

~/.config/opencode/
├── opencode.json                 # Main config (auto-updated)
├── AGENTS.md → ~/.claude/CLAUDE.md  # Symlink (always in sync)
└── commands/                     # Writing commands

~/.cache/opencode/
└── claude-to-opencode.hash       # Conversion cache

Project/.claude/
├── CLAUDE.md                     # Project instructions
└── settings.local.json           # Enabled MCP servers

Project/
├── .mcp.json                     # MCP server definitions
└── CLAUDE.md                     # Alternative location
```

## Configuration Precedence

OpenCode reads instructions in this order:

1. **Project-level:**
   - `./CLAUDE.md` or `./.claude/CLAUDE.md`
   - `./.opencode/AGENTS.md`

2. **Global:**
   - `~/.config/opencode/AGENTS.md` (symlinked to `~/.claude/CLAUDE.md`)

3. **Fallback:**
   - `~/.claude/CLAUDE.md` (if symlink broken)

## Workflow Recommendations

### Single Source of Truth

**For instructions:**
- Edit `~/.claude/CLAUDE.md` for global rules
- Create `./CLAUDE.md` for project-specific rules
- OpenCode sees changes immediately via symlink

**For settings:**
- Edit `~/.claude/settings.json` for global config
- Create `./.claude/settings.local.json` for project overrides
- Next `opencode` run converts automatically

### Version Control

**Global settings:**
```bash
cd ~/.files
git add .claude/settings.json claude/CLAUDE.md
git commit -m "feat: update Claude/OpenCode settings"
```

**Project settings:**
```bash
# In project
git add .claude/settings.local.json CLAUDE.md
git commit -m "docs: configure Claude/OpenCode for this project"
```

## Troubleshooting

### Conversion Runs Every Time

Cache might be stale:
```bash
# Clear cache
rm ~/.cache/opencode/claude-to-opencode.hash

# Run once to rebuild
claude-to-opencode
```

### AGENTS.md Not Updating

Symlink might be broken:
```bash
# Check symlink
ls -la ~/.config/opencode/AGENTS.md

# Should show: AGENTS.md -> /Users/user/.claude/CLAUDE.md

# Recreate if needed
rm ~/.config/opencode/AGENTS.md
claude-to-opencode --force
```

### Project MCP Servers Not Converting

Check that both files exist:
```bash
# Enabled servers list
cat .claude/settings.local.json

# Server definitions (may be in parent dir)
find . -name ".mcp.json" -o -name "mcp.json"
```

### Permissions Not Working

OpenCode permission format is different from Claude Code:
```bash
# Check converted permissions
cat ~/.config/opencode/opencode.json | jq .permission

# Test with dry-run to see conversion
claude-to-opencode --dry-run | jq .permission
```

## Advanced Usage

### Disable Auto-Conversion

If you want separate OpenCode/Claude Code configs:
```bash
# Edit ~/.files/shell/functions/opencode.zsh
# Comment out the claude-to-opencode call

# Or use command directly
command opencode  # Bypasses shell function
```

### Convert Only Global Settings

```bash
claude-to-opencode --global
```

### Force Fresh Conversion

```bash
# Clear cache and reconvert
rm ~/.cache/opencode/claude-to-opencode.hash
claude-to-opencode --force
```

### Check What Would Be Converted

```bash
# Dry run shows config without applying
claude-to-opencode --dry-run | jq
```

## See Also

- OpenCode Documentation: https://opencode.ai/docs/
- Your OpenCode Config: `~/.config/opencode/opencode.json`
- Your Claude Settings: `~/.claude/settings.json`
- Your CLAUDE.md: `~/.claude/CLAUDE.md`
