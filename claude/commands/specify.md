---
description: "Develop an evidence-backed specification through consequential dialogue; stop before planning"
argument-hint: '"Task Title" (init) or empty (continue)'
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
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

# /specify — Dialogue to a Validated Specification

Read `$HOME/.claude/commands/socrates/dialogue.txt` before initializing or resuming.
It is the canonical procedure for session resolution, evidence and decisions,
question selection, critique reconciliation, readiness, and legacy sessions.
Follow it with this command's endpoint below; do not recreate a competing procedure.

## Invocation and endpoint

- A task title in `$ARGUMENTS` initializes a session.
- Empty `$ARGUMENTS` continues the session selected by the shared resolution procedure.
- Preserve the existing `.socrates/YYYYMMDD-HHMMSS/` artifacts and per-session pointers.

When the shared readiness gate passes, stop at `Status: Validated` and `Frozen: true`. Briefly state what is settled and any explicitly accepted uncertainty. Do not enter plan mode, generate an implementation plan, or execute work; `/shape` or `/socrates` owns the next phase.

On continuation of a `Planned`, `Executing`, or `Verified` session, retain that state
unless new evidence requires reopening. Do not repeatedly plan or execute because
the command was resumed. Follow the user's current request against the saved state.

## Companion files

The shared procedure and `spec-scaffold.tpl` live under
`$HOME/.claude/commands/socrates/`, linked by `make claude` from the dotfiles repo.
Planning is deliberately outside this command.
If a required companion cannot be read, explain which file is missing and that
`make claude` restores the link; do not reconstruct its contents from memory.

## Usage

```text
/specify "Task title"   # initialize
/specify                # continue the bound session, or resolve via the picker
```
