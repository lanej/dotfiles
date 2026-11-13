---
name: socrates
description: Develop an evidence-backed specification through Socratic dialogue, then draft an execution-ready plan. Use when asked to invoke Socrates, interrogate a proposed task, or resume a Socrates session.
---

# Socrates

Read [the shared dialogue procedure](references/dialogue.txt) before initializing or resuming. It owns session resolution, evidence, decision records, questions, readiness, freezing, reopening, and legacy migration. Read [the specification scaffold](references/spec-scaffold.tpl) when initializing. These are the canonical shared sources; Claude command companions are compatibility links to them.

## Invocation and session resolution

`$socrates Task title` initializes a session; `$socrates` continues one. An explicit `.socrates/<timestamp>/` path selects that session. Preserve the existing `.socrates/YYYYMMDD-HHMMSS/` artifacts and lifecycle states.

Apply the shared procedure's host-specific session and question routing. A fully specified request can pass readiness immediately. Respect active write restrictions and identify any artifact that has not been persisted.

## Planning endpoint

Once readiness passes, draft the plan in the same turn. Do not stop at `Validated` or ask permission merely to draft. For a `Planned`, `Executing`, or `Verified` session, preserve that state and follow the current request unless new evidence requires reopening.

Read [the planning companion](references/phases-2-3.txt) and follow its native host handoff. It owns draft persistence, independent critique when warranted, approval, and transition to `Planned`. Readiness or a saved draft does not authorize execution.
