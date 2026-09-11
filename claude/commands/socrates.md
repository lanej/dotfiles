---
description: "Interrogate consequential decisions into an evidence-backed specification, then enter plan mode"
argument-hint: '"Task Title" (init) or empty (continue)'
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
  - Agent
  - ExitPlanMode
  - EnterPlanMode
  - Bash(date:*)
  - Bash(mkdir:*)
  - Bash(grep:*)
  - Bash(find:*)
  - Bash(printenv:*)
  - Bash(sort:*)
tags:
  - specification
  - dialogue
---

# /socrates — Dialogue to an Execution-Ready Plan

Read `$HOME/.claude/commands/socrates/dialogue.txt` before initializing or resuming.
It is the canonical procedure for session resolution, evidence and decisions,
question selection, critique reconciliation, readiness, and legacy sessions.
Follow it with this command's endpoint below; do not recreate a competing procedure.

## Invocation and endpoint

- A task title in `$ARGUMENTS` initializes a session.
- Empty `$ARGUMENTS` continues the session selected by the shared resolution procedure.
- Preserve the existing `.socrates/YYYYMMDD-HHMMSS/` artifacts and per-session pointers.

When the shared readiness gate passes, read `$HOME/.claude/commands/socrates/phases-2-3.txt` and proceed directly into planning. Do not add a permission question just to draft the plan. Approval of the resulting plan remains separate.

On continuation of a `Planned`, `Executing`, or `Verified` session, retain that state
unless new evidence requires reopening. Do not repeatedly plan or execute because
the command was resumed. Follow the user's current request against the saved state.

## Companion files

The shared procedure and `spec-scaffold.tpl` live under
`$HOME/.claude/commands/socrates/`, linked by `make claude` from the dotfiles repo.
The planning companion is `phases-2-3.txt` in that same directory.
If a required companion cannot be read, explain which file is missing and that
`make claude` restores the link; do not reconstruct its contents from memory.

## Usage

```text
/socrates "Task title"   # initialize
/socrates                # continue the bound session, or resolve via the picker
```
