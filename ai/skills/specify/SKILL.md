---
name: specify
description: Develop or resume an evidence-backed Socrates specification and stop before planning. Use when asked to specify a task, invoke specify, or reconcile a specification's critique findings.
---

# Specify

Read [the shared dialogue procedure](../socrates/references/dialogue.txt) before initializing or resuming. It owns session resolution, evidence, decisions, questions, critique reconciliation, readiness, freezing, reopening, and legacy adaptation. Read [the specification scaffold](../socrates/references/spec-scaffold.tpl) when initializing.

A task title initializes a new session; an explicit spec path or session directory selects an existing one; no arguments continue the bound session or invoke the shared picker. Use `$specify` in Codex or `/specify` in Claude Code. Preserve settled decisions and saved artifacts.

Stop when the shared readiness gate passes: `Status: Validated`, `Frozen: true`. Briefly state what is settled and any explicitly accepted uncertainty. Do not draft an implementation plan or execute work as part of this endpoint. If consequential ambiguity remains, ask the relevant question and wait for its answer.

On continuation of a `Planned`, `Executing`, or `Verified` session, retain that state unless new evidence requires reopening. Do not repeat planning or execution merely because the session was resumed. Respect the host's active write restrictions and identify any draft that could not be persisted.
