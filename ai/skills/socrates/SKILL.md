---
name: socrates
description: Develop an evidence-backed specification and an execution-ready plan, with a handoff to execution when explicitly authorized. Use when asked to invoke Socrates, interrogate a proposed task, or resume a Socrates session.
---

# Socrates

Read [the shared dialogue procedure](references/dialogue.txt) before initializing or resuming. It owns session resolution, evidence, decision records, questions, readiness, freezing, reopening, and legacy migration. Read [the specification scaffold](references/spec-scaffold.tpl) when initializing. These are the canonical shared sources; Claude command companions are compatibility links to them.

## Invocation

`$socrates Task title` initializes a session. `$socrates` continues one. An explicit path under `.socrates/` selects that session, including an existing timestamp path. Preserve its artifacts and lifecycle state.

Keep the session's `progress.md` current using the shared dialogue procedure. For a progress-only request, compare the saved checkpoint with the available session artifacts and report the last evidenced milestone and the next action or blocker. Keep the request read-only, even when the checkpoint is absent or stale.

## Turn flow and outcomes

1. **Open the session.** The outcome is a selected session with a draft or saved specification that captures the goal, constraints, and observable success criteria. Resolve the path with the shared procedure and carry forward settled decisions. Preserve a supported `Planned`, `Executing`, or `Verified` state unless new evidence or changed scope requires reopening.
2. **Resolve blockers.** The outcome is a frozen `Validated` specification with evidence for the applicable readiness properties, recorded decisions, and observable acceptance criteria. Resolve facts directly. When a blocker needs the user, ask the next concrete question with the host's available question tool as directed by the dialogue procedure. If the tools cannot present it, end the reply with the question in chat. Record each answer and recheck readiness immediately. A clear request can pass without an interview.
3. **Draft the plan.** The outcome is a concrete draft for the frozen version that a fresh executor can follow through verification. Read and apply [the planning companion](references/phases-2-3.txt) in the same turn. On resuming `Validated`, use the matching draft if present or draft the missing plan. Complete any required critique before presenting the draft.
4. **Handle the plan decision.** The outcome of approval is an exact, approved `plan.md` and a matching `Planned` spec when writes are permitted. Apply requested plan revisions and present the revised draft. A changed frozen requirement returns through reopening and readiness. Approval alone ends at the execution handoff. When the user explicitly authorizes execution as well, read and apply [Shape's execution and verification procedure](../shape/SKILL.md) without another confirmation.
5. **Deliver when authorized.** The outcome is the requested deliverables and a verification report against the approved version. Carry the work through the task checks and final acceptance. A matching successful result ends at `Verified`. Report the specific incomplete or failed outcome when an actual blocker prevents completion.

Carry the work forward to the next real blocker or the endpoint in the current turn. Yield for a pending answer, a decision on the concrete plan, or a gate that cannot be satisfied within current authority or host capabilities. Keep doing permitted work such as drafting in Codex Plan mode, and identify any session files still awaiting persistence.
