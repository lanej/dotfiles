# OpenCode wrapper with automatic Claude Code configuration conversion
#
# This function performs a comprehensive conversion of all Claude Code settings
# to OpenCode format on startup:
# - Global settings (~/.claude/settings.json) → permissions, LSP
# - Project settings (./.claude/settings.local.json) → enabled MCP servers
# - CLAUDE.md files → AGENTS.md (symlinked)
# - .mcp.json → MCP configuration
#
# Additionally, when running in tmux, this updates the window title to match
# the opencode session title (polls every 5 seconds).
#
# The conversion is smart and only runs when needed.

opencode() {
    # Run comprehensive Claude to OpenCode conversion
    local conversion_output
    if command -v claude-to-opencode &>/dev/null; then
        conversion_output=$(claude-to-opencode 2>&1)
    else
        conversion_output=$(~/.files/bin/claude-to-opencode 2>&1)
    fi
    
    # Only show output if there was conversion activity
    if [[ -n "$conversion_output" ]]; then
        echo "$conversion_output" >&2
    fi
    
    # Start tmux title updater in background (if in tmux)
    # Pass current directory so it finds the correct project's sessions
    local title_pid
    if [[ -n "${TMUX:-}" ]]; then
        ~/.files/bin/opencode-tmux-title "$(pwd)" &>/dev/null &
        title_pid=$!
        disown $title_pid 2>/dev/null
    fi
    
    # Execute opencode with all arguments
    command opencode "$@"
    local exit_code=$?
    
    # Cleanup: kill title updater and restore automatic window naming
    if [[ -n "${title_pid:-}" ]]; then
        kill "$title_pid" 2>/dev/null
        tmux set-window-option automatic-rename on 2>/dev/null
    fi
    
    return $exit_code
}

# Short alias
alias oc=opencode
