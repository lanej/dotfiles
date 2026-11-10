---
name: data-change-planning
description: Use when preparing or reviewing software plans that change data structures or interfaces. Show how data representation and exchange change, and how the proposed boundaries contain complexity, before deriving implementation steps.
---

# Plan data and interface changes

Make the plan explain how the work changes data representation and exchange. Start with the behavior or problem motivating the change so the reader knows why the model and interfaces matter before seeing type names. A list of components or implementation tasks alone does not convey the proposed design.

## Show the change

Inspect the relevant existing model, interfaces and callers. Distinguish observed contracts from proposed ones; mark missing context as an assumption. For new capabilities, identify existing representations or exchanges being replaced or extended, or state that they are new.

Show a focused before-and-after using concrete types, schemas or representative values, along with affected function signatures, commands, events or request/response shapes. Highlight additions, removals, changed meanings and relationships. Use the project's language when known, otherwise readable pseudocode. Include only enough surrounding structure to make the change understandable; explain concepts before expanding their hierarchy.

Explain the consequences that matter: identity and references, containment and independent access, ownership and lifecycle, cardinality, valid states and invariants. Follow real operations through the proposed structure to check whether the data needed by each caller is available. Conceptual containment does not by itself settle storage layout or the need for a reference back to the parent.

Use questions about the model to resolve consequential choices with Josh. For example, whether an attempt needs a job reference depends on whether callers receive it independently. Investigate existing callers and recommend a choice with its reason; avoid reflexively accepting a suggestion or presenting a questionnaire of hypothetical concerns. Keep unresolved decisions explicit rather than silently treating them as settled.

## Bound complexity through representation and exchange

Prefer containing complexity within a capability over relying on every caller to manage it correctly. Name the responsibility that owns it, the details that remain internal, and the data and obligations that cross its interface. This applies to ordinary functions and modules as well as service boundaries; it does not require new layers or interface declarations.

Trace a representative exchange from caller input through the boundary to its returned result or emitted event. Show who validates the input, owns state transitions and handles failures where these affect the design. Look for complexity leaking through exposed mutable internals, persistence or provider details, and protocols that require callers to coordinate hidden steps. Narrow the contract or relocate the responsibility when doing so simplifies the whole workflow.

Do not hide meaningful distinctions to make an interface look simple. Preserve the outcomes, errors and evidence callers need to act correctly. Challenge a boundary with a plausible internal change: explain which callers would need to change and why. Keep intentional coupling explicit, and avoid general wrappers that only move complexity or erase useful capabilities.

## Derive the plan

Connect implementation steps to the structural and exchange changes and the behavior they enable. Include compatibility, migration, defaults and treatment of existing records and callers when relevant. Identify a focused check that can expose a broken relationship, boundary contract, invariant or retained behavior. Keep agreed choices and open questions distinct as the plan evolves.

Scale to the work. Reuse existing types and interfaces when they fit. If the proposal changes behavior without changing structure or exchange contracts, say so briefly and explain how the existing contracts support it. Do not invent a schema change, abstraction or separate approval gate for routine edits. This planning guidance does not authorize implementation or replace project architecture and verification requirements.

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

The request and its identity stay on `Job`; execution outcomes move to `Attempt`. One job has many attempts, identified by `(jobId, number)`. Here the proposed coordinator receives an attempt independently, so it needs `jobId` to retrieve the request. If existing callers always pass a containing job, revisit whether that reference is needed. These types are a focused structural delta, not a complete retry design.

For job J42, a failed attempt 1 and successful attempt 2 remain separate records. Existing jobs retain their latest known result as an imported attempt; older execution history cannot be recovered from the current model.

The worker previously received the full job:

```typescript
execute(job: Job): Promise<ExecutionOutcome>
```

Give it only the payload needed for one execution; the coordinator owns job lookup and attempt history:

```typescript
execute(payload: JobPayload): Promise<ExecutionOutcome>
```

The coordinator resolves the attempt's job, supplies its payload to the worker and records the returned outcome against that attempt. The worker contract keeps meaningful execution outcomes, while changes to attempt storage and numbering stay inside the coordinator and persistence boundary. Existing direct worker callers need updating to pass the payload. Do not widen the worker input merely to mirror the new storage structure.

The resulting plan changes persistence to retain attempts, preserves existing outcomes during migration, updates the coordinator and worker exchange, and updates result readers to use attempt history. Verify that a retry preserves the first failure, each attempt resolves to the correct request, and the worker can execute with the supplied payload without access to attempt storage. Retry scheduling and uncertain external outcomes remain separate design decisions to resolve before implementing those behaviors.
