---
name: data-change-planning
description: Use when preparing or reviewing software plans that change data structures, types, schemas or relationships. Explain the current-to-proposed structural changes and their consequences before deriving implementation steps.
---

# Plan data changes

Make the plan explain how the work changes the data's structure. Start with the behavior or problem motivating the change so the reader knows why the model matters before seeing type names. A list of components or implementation tasks alone does not convey the proposed design.

## Show the change

Inspect the relevant existing model and its callers. Distinguish observed structures from proposed ones; mark missing context as an assumption. For new capabilities, identify any existing representation being replaced or extended, or state that the model is new.

Show a focused before-and-after using concrete types, schemas or representative values. Highlight additions, removals, changed meanings and relationships. Use the project's language when known, otherwise readable pseudocode. Include only enough surrounding structure to make the change understandable; explain concepts before expanding their hierarchy.

Explain the consequences that matter: identity and references, containment and independent access, ownership and lifecycle, cardinality, valid states and invariants. Follow real operations through the proposed structure to check whether the data needed by each caller is available. Conceptual containment does not by itself settle storage layout or the need for a reference back to the parent.

Use questions about the model to resolve consequential choices with Josh. For example, whether an attempt needs a job reference depends on whether callers receive it independently. Investigate existing callers and recommend a choice with its reason; avoid reflexively accepting a suggestion or presenting a questionnaire of hypothetical concerns. Keep unresolved decisions explicit rather than silently treating them as settled.

## Derive the plan

Connect implementation steps to the structural changes and the behavior they enable. Include compatibility, migration, defaults and treatment of existing records when relevant. Identify a focused check that can expose a broken relationship, invariant or retained behavior. Keep agreed choices and open questions distinct as the plan evolves.

Scale to the work. Reuse existing types when they fit. If the proposal changes behavior without changing structure, say so briefly and explain how the existing model supports it. Do not invent a schema change or require a separate modeling approval for routine edits. This planning guidance does not authorize implementation or replace project architecture and verification requirements.

## Example: adding retry history

Retries need to preserve each execution's result. The current job stores only the latest result, so another execution overwrites the previous failure.

Before:

```typescript
type Job = {
  id: JobId
  payload: JobPayload
  outcome: ExecutionOutcome
}
```

Proposed:

```typescript
type Job = {
  id: JobId
  payload: JobPayload
}

type Attempt = {
  jobId: JobId
  number: number
  outcome: ExecutionOutcome
}
```

The request and its identity stay on `Job`; execution outcomes move to `Attempt`. One job has many attempts, identified by `(jobId, number)`. Here the proposed worker input is an attempt passed independently, so it needs `jobId` to retrieve the request. If existing callers always pass a containing job, revisit whether that reference is needed. These types are a focused structural delta, not a complete retry design.

For job J42, a failed attempt 1 and successful attempt 2 remain separate records. Existing jobs retain their latest known result as an imported attempt; older execution history cannot be recovered from the current model.

The resulting plan changes persistence to retain attempts, preserves existing outcomes during migration, updates the worker to associate each execution with its job, and updates result readers to use attempt history. Verify that a retry preserves the first failure and that each attempt resolves to the correct request. Retry scheduling and uncertain external outcomes remain separate design decisions to resolve before implementing those behaviors.
