---
description: Analyze session behavior against CLAUDE.md and apply improvements. Spawned as a background sub-agent by plan mode with argument 'auto' to apply changes without user interaction. Also invoke manually after a session where Claude misunderstood requests, ignored instructions, or needed repeated correction.
argument-hint: [auto]
allowed-tools: Read, Edit, Write, Glob, Bash(find:*), Bash(which:*), Skill, Agent, TodoWrite, Bash(git:*), mcp__plugin_claude-mem_mcp-search__search, mcp__plugin_claude-mem_mcp-search__get_observations
---

## Step 1 — Analyze Chat History

Review the conversation history in your context window. Identify patterns indicating missing, incomplete, or incorrect instructions across all eligible targets: **user-level CLAUDE.md, project-level CLAUDE.md, skill files** (`~/.files/claude/skills/*/SKILL.md`), and **auto-memory** (`~/.claude/projects/…/memory/`). These are all first-class targets — the goal is putting guidance where it will be read, not stuffing everything into CLAUDE.md.

- Requests Claude misunderstood
- Behaviors the user had to correct more than once
- Tool preferences or workflows used repeatedly that are absent from any config file
- Instructions that exist but were ignored or applied inconsistently
- Edge cases that produced wrong behavior
- Tool-specific patterns that belong in a skill file rather than CLAUDE.md

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

Before invoking any improver, classify each finding by where it belongs. Ask the critical question first: **is this a bug/gap in the tool itself, or is it a documentation gap in how Claude uses the tool?**

**Tool repo** — the finding is a fixable bug, missing feature, or incorrect behavior in a locally-installed tool:
- The tool itself does the wrong thing, is missing a flag/option, or has a defect
- A workaround currently lives in CLAUDE.md or a skill file because the tool wasn't fixed
- Fix belongs in the tool's source repo, not in documentation

Local tool repos (canonical mapping):
| Tool | Repo path |
|---|---|
| `epq` | `~/src/analysis-doc` |
| `qmd` | check `which qmd` to find install path; if local repo, use it |

If the tool has no local repo (e.g., `xlsx`, `bigquery` CLI, external SaaS), the fix cannot go here — document the workaround in the skill file instead.

**Skill file** (`~/.files/claude/skills/<name>/SKILL.md`) — usage guidance, gotchas, patterns, and workarounds for things that can't be fixed upstream:
- Usage details and edge cases for a specific tool (epq, gspace, jira, bigquery, qmd, etc.)
- Patterns that only apply when that skill is active
- Workarounds for tool behaviors that are correct but surprising
- **Rule**: if a finding is about how to use a specific tool and that tool has a skill file, it goes in the skill file — not CLAUDE.md. CLAUDE.md should only contain the trigger/invocation rule (when to load the skill), not the tool's usage detail.
- **Do NOT add a caveat to the skill file for something that should be fixed in the tool** — document → fix, not document → workaround.

**User-level** (`~/.claude/CLAUDE.md`) — global, applies unconditionally across all sessions:
- Session-wide behaviors that must be active before any skill loads (e.g., first-look protocol, `--no-rerank` rule)
- Tool preferences without a dedicated skill (CLI flags, command substitutions)
- Communication style and operational guidelines
- Cross-project workflows that apply regardless of context
- **Not**: tool-specific detail that already has a skill home

**Project-level** (`~/.files/CLAUDE.md`) — dotfiles repo only, checked in:
- Conventions specific to this repository
- Repo architecture and structure knowledge
- Workflows that only make sense in this codebase

**Project-local** (`~/.files/CLAUDE.local.md`) — dotfiles repo, not checked in:
- Machine-specific setup or paths
- Local development commands

**Auto-memory** (`~/.claude/projects/…/memory/`) — soft preferences, feedback, and project context:
- Corrections or preferences stated once that don't yet rise to a hard rule (type: `feedback`)
- User-specific context that shapes future collaboration but isn't universally prescriptive (type: `user`)
- Project state or decision context discovered during the session (type: `project`)
- References to external systems, dashboards, or data sources (type: `reference`)
- One-offs worth recording so the pattern can be detected if it recurs — capturing it in memory without promoting it to a global rule

**Decision order**:
1. Is this a fixable bug/gap in a locally-installed tool? → `tool-repo:<path>`
2. Does a skill file exist for this tool? → `skill:<name>`
3. Must it apply before any skill loads or has no skill home? → `user-claude-md`
4. Is it dotfiles-repo-specific? → `project-claude-md` or `project-local`
5. Is it a soft preference, one-off correction, or project context — not a hard rule? → `memory:<type>`

Add the scoping classification to your findings brief:

```
Missing instructions: <list or "none">
Incorrect instructions: <list or "none">
Ignored instructions: <list or "none">
Classification: <finding → one-off | recurring | regressed>
Scope decisions: <finding → tool-repo:<path> | skill:<name> | user-claude-md | project-claude-md | project-local | memory:<type>>
```

## Step 4 — Apply Improvements to the Right Target

Split findings by scope and dispatch each group appropriately.

**For tool-repo findings** — spawn a sub-agent into the tool's repo to fix the issue directly. Brief the sub-agent with:
- **Context**: what the reflection found; why this is a bug or gap in the tool, not just a documentation issue
- **Domain**: the tool's purpose, the project's conventions (read its CLAUDE.md first), its test/lint workflow
- **Sub-problem**: exactly what to change — the specific behavior to add, fix, or correct
- **Success**: the fix is implemented, tests pass (or tests are added), and the change is committed
- **Constraints**: follow the repo's own protocols; do not just add a workaround — actually fix the root cause
- **Output**: report what was changed and the commit SHA

Do NOT add a corresponding caveat to the skill file after fixing the tool — the fix is the artifact, not the note.

**For skill file findings** — invoke `skill-creator`, passing:
- Which skill file to update (path)
- The specific finding and what to add/change
- Whether to run autonomously (if `$ARGUMENTS` contains `auto`)

**For CLAUDE.md findings** — invoke `claude-md-management:claude-md-improver`, passing your findings brief (including scope decisions) as the `args`.

**For memory findings** — write the memory directly using the auto-memory format:
- Memory directory: derive from the active working directory — `~/.claude/projects/<escaped-path>/memory/` where `<escaped-path>` replaces `/` with `-` in the absolute project path. Check `MEMORY.md` exists there before writing.
- Write each finding as a new markdown file with frontmatter (`name`, `description`, `type`) and body structured per type (`feedback`: rule + **Why:** + **How to apply:**; `project`: fact + **Why:** + **How to apply:**)
- Append a one-line pointer to `MEMORY.md` under 150 characters
- In interactive mode, invoke the `remember` skill instead and let the user review before writing

If `$ARGUMENTS` contains `auto`:
- Run all dispatches autonomously — apply all improvements without interactive approval

Otherwise:
- Present your findings and scope decisions to the user first, then dispatch the appropriate agents interactively
