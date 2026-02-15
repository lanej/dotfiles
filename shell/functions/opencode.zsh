# OpenCode wrapper with automatic Claude Code configuration conversion
#
# This function performs a comprehensive conversion of all Claude Code settings
# to OpenCode format on startup:
# - Global settings (~/.claude/settings.json) → permissions, LSP
# - Project settings (./.claude/settings.local.json) → enabled MCP servers
# - CLAUDE.md files → AGENTS.md (symlinked)
# - .mcp.json → MCP configuration
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
    # Uses a PID file for reliable cleanup
    local pidfile=""
    if [[ -n "${TMUX:-}" ]]; then
        pidfile="/tmp/opencode-tmux-title.$$"
        ~/.files/bin/opencode-tmux-title "$(pwd)" "$pidfile" &>/dev/null &
    fi
    
    # Execute opencode with all arguments
    command opencode "$@"
    local exit_code=$?
    
    # Cleanup: kill title updater via PID file
    if [[ -n "$pidfile" && -f "$pidfile" ]]; then
        local pid
        pid=$(<"$pidfile")
        kill "$pid" 2>/dev/null
        rm -f "$pidfile"
        tmux set-window-option automatic-rename on 2>/dev/null
    fi
    
    return $exit_code
}

# Short alias
alias oc=opencode
