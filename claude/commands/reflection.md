---
description: Analyze session behavior against CLAUDE.md and apply improvements. Spawned as a background sub-agent by plan mode with argument 'auto' to apply changes without user interaction. Also invoke manually after a session where Claude misunderstood requests, ignored instructions, or needed repeated correction.
argument-hint: [auto]
allowed-tools: Read, Edit, Skill, TodoWrite, Bash(git:*), mcp__plugin_claude-mem_mcp-search__search, mcp__plugin_claude-mem_mcp-search__get_observations
---

## Step 1 — Analyze Chat History

Review the conversation history in your context window. Identify patterns indicating missing, incomplete, or incorrect CLAUDE.md instructions:

- Requests Claude misunderstood
- Behaviors the user had to correct more than once
- Tool preferences or workflows used repeatedly that are absent from CLAUDE.md
- Instructions that exist but were ignored or applied inconsistently
- Edge cases that produced wrong behavior

Structure your initial findings as a brief:

```
Missing instructions: <list or "none">
Incorrect instructions: <list or "none">
Ignored instructions: <list or "none">
```

## Step 2 — Cross-Reference with claude-mem

Search claude-mem for each finding to determine whether it is a one-off or a recurring pattern:

```
mcp__plugin_claude-mem_mcp-search__search(query="<finding keyword>")
```

Use the results to classify each finding:

| Classification | Meaning | Priority |
|---|---|---|
| `one-off` | Appears only in this session | Low — may be context-specific |
| `recurring` | Appears in 2+ past sessions | High — confirmed pattern, fix it |
| `regressed` | Was previously fixed in CLAUDE.md but recurs now | Critical — the fix didn't hold; instruction needs to be stronger or moved |

Add the classification to each finding in your brief. Deprioritize one-offs unless they represent a clear gap. Escalate regressions — note specifically that the previous fix failed.

## Step 3 — Scope Each Finding

Before invoking the improver, classify each finding by which CLAUDE.md it belongs in:

**User-level** (`~/.claude/CLAUDE.md`) — global, applies across all projects:
- Tool preferences and CLI patterns
- Communication style corrections
- Cross-project workflow behaviors
- Operational guidelines that should always apply

**Project-level** (`~/.files/CLAUDE.md`) — dotfiles repo only, checked in:
- Conventions specific to this repository
- Repo architecture and structure knowledge
- Workflows that only make sense in this codebase

**Project-local** (`~/.files/CLAUDE.local.md`) — dotfiles repo, not checked in:
- Machine-specific setup or paths
- Local development commands

If a finding could apply anywhere, it belongs at user-level. Only put findings at project-level if they are meaningless outside this repo.

Add the scoping classification to your findings brief:

```
Missing instructions: <list or "none">
Incorrect instructions: <list or "none">
Ignored instructions: <list or "none">
Classification: <finding → one-off | recurring | regressed>
Scope decisions: <finding → file>
```

## Step 4 — Invoke the CLAUDE.md Improver

Invoke the `claude-md-management:claude-md-improver` skill, passing your findings brief (including scope decisions) as the `args`.

If `$ARGUMENTS` contains `auto`:
- Run the skill autonomously — apply all improvements without interactive approval

Otherwise:
- Present your findings and scope decisions to the user first, then invoke the skill interactively
