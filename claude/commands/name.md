---
description: "Generate and register a short descriptive name for this session — entirely inside a sub-agent so the main session's context and token budget are untouched."
allowed-tools:
  - Agent
---

# /name

Delegate session naming entirely to a sub-agent. The main session must not read the transcript, derive the name, or run any bash itself — its only job is to spawn the agent and relay its final line back to the user.

Spawn `Agent(subagent_type: "general-purpose", model: "haiku", run_in_background: false)` with this prompt verbatim:

````
You are naming a Claude Code session for tmux/session-list display. Do the whole thing yourself — no clarifying questions.

1. Find the session transcript:
   ls -t ~/.claude/projects/$(echo "$PWD" | sed 's|/|-|g; s|^-||')/*.jsonl 2>/dev/null | head -1
   The filename without extension is the session ID. If that glob finds nothing, find the most recently modified file matching `~/.claude/projects/*/*.jsonl` instead.

2. Extract a compact digest of the conversation — do NOT cat/Read the raw transcript, it's large:
   jq -r 'select(.type=="user" or .type=="assistant") | .message.content as $c | if ($c|type)=="string" then $c else [$c[] | if .type=="text" then .text elif .type=="tool_use" then "[tool_use] " + .name else empty end] | join(" ") end' <transcript-path> | tail -c 8000

3. From the digest, summarize the core topic in 2-4 kebab-case words (e.g. `vertex-ai-setup`, `dotfile-hook-refactor`). No explanation, no punctuation beyond hyphens.

4. Register the name:
   mkdir -p ~/.claude/session-names
   echo -n "<name>" > ~/.claude/session-names/<session_id>

5. Rename the tmux window if inside tmux (direct `rename-window`, not an OSC escape — `allow-rename` is off during Claude Code sessions so OSC title sequences are ignored):
   if [ -n "$TMUX_PANE" ]; then
     tmux rename-window -t "$TMUX_PANE" "✻ <name>"
     tmux set-option -w -t "$TMUX_PANE" @claude_named "✻ <name>"
   else
     printf '\033]0;%s\007' "<name>" > /dev/tty
   fi

6. Return exactly one line, nothing else: `Session named: <name>`
````

Relay the sub-agent's final line back to the user verbatim.
