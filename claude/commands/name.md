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

1. Resolve the session ID and transcript path using the extracted resolver script. Do not
   reimplement this logic inline — it was pulled out of this file because embedded bash here
   caused the 2026-08-07 regression (a `sed` cwd-encoding bug plus an `ls -t | head -1` race
   across same-cwd sessions).
     resolved="$($HOME/.files/bin/claude-session-resolve)" || { echo "resolve failed"; exit 1; }
     eval "$resolved"
     echo "session_id=$SESSION_ID transcript_path=$TRANSCRIPT_PATH"
   If the resolver exits non-zero, stop and report failure rather than guessing — do not fall
   through to steps 2-6 with empty values. Otherwise use the exact `session_id`/`transcript_path`
   values from the echoed line verbatim below.

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
