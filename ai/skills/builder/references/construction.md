# Software construction

First make it work, then make it good, then make it fast. "Work" means the
smallest meaningful behavior, not the entire system or merely compiling.

This policy governs how software is developed. The accompanying
[Pragmatic Hexagonal Architecture standard](standard.md) governs properties of
the resulting software. Neither a development sequence nor a passing checklist
establishes those properties. TDD is optional; verification is not.

## Begin with a steel thread

A **steel thread** is one narrow, executable path through a capability: from its real entrypoint, through the decisions and necessary integration boundaries, to an observable result. It connects the pieces needed to establish one meaningful outcome before broadening their individual capabilities. A small utility may need only standard input, a transformation and standard output; an existing service should extend its established path rather than rebuild its stack.

Choose a representative input and expected outcome. Identify the consequential question and what observation could contradict the proposed answer. Implement only what connects that path and exercise it before expanding scope. Prefer a real, observable result over broad scaffolding, speculative abstractions, or a comprehensive implementation that has not been exercised. The first useful result may be a clear failure.

Keep scope narrow while retaining the boundaries needed to support the claim. For example, a document-import capability can begin with one supported document:

1. Submit it through the actual command or upload entrypoint.
2. Parse and validate the minimum supported content.
3. Persist it through the intended storage integration.
4. Retrieve the stored result through the capability's read path and compare it with the expected content.
5. Protect that behavior, then add the next format, validation failure or recovery condition.

A parser test alone cannot establish that import and retrieval work together. An in-memory substitute cannot establish compatibility with the intended storage. Equally, the first document does not justify building a general parser framework, every format or a complete management interface.

Choose the initial feedback mechanism to resolve the consequential question. Direct execution, manual inspection, a small harness, or an automated test can each be appropriate. If one boundary's feasibility is uncertain, use a focused experiment there, then connect what is learned into the thread. A mock cannot resolve uncertainty about the real boundary it replaces. When a boundary is unavailable, name the substitution and remaining gap; do not present the complete path as verified. Use a safe sandbox, representative fixture, or authorized integration experiment; never bypass permissions or production protections to get a result.

## Protect the thread, then expand

As understanding emerges, turn it into repeatable checks. Do not wait for the whole feature to be complete or the implementation to stabilize. Once meaningful behavior is established and will be retained, protect it before substantial expansion or material restructuring. Prefer extending an existing behavioral detector over creating parallel harnesses.

Work in small loops: establish a behavior, verify it, protect it, and simplify. Expand the protected thread with the next meaningful behavior, failure condition or integration, verifying each increment before further expansion. Plan these increments together, not "implement everything" followed by "add tests." This is not a prescribed commit sequence or a report per loop.

## When tests enter

During early development, favor a small number of checks through the steel thread, starting with a representative happy path. Aim for maximum meaningful protection with minimum testing machinery. A check through the real entrypoint can protect several connected behaviors while interfaces are still changing. Avoid chasing coverage percentages, exhaustive input variations or speculative internals.

Add failure and boundary checks early when they affect safety, feasibility or the credibility of the result. For an importer writing to a disposable store, one document's successful import and retrieval can justify the next increment. If import overwrites valuable records, protection against destructive writes belongs in the initial thread. If retries are introduced, their consequences become part of what needs verification. A happy-path result supports only the conditions exercised.

Unit tests are useful when isolating a stable decision improves protection or failure diagnosis. They are not an initial development requirement. Add focused checks where the thread cannot expose a consequential defect or produces ambiguous failures; avoid introducing interfaces solely to make mocking possible. Explicit project test-first requirements still apply.

| Situation | Guidance |
|---|---|
| The first connected behavior is taking shape. | Start with a representative happy-path check through the real entrypoint; keep the harness light. |
| A decision has a stable contract or needs isolated diagnosis. | Add a focused unit test when it improves feedback or protection. It may precede implementation. |
| A failure or boundary condition affects safety, feasibility or confidence in the result. | Check it in the initial thread, even while other cases remain deferred. |
| Integration or approach feasibility is uncertain. | Run the smallest credible experiment against the relevant real boundary; state what remains unverified. |
| A meaningful path works and will be retained. | Capture a repeatable check before substantial expansion or material restructuring. |
| A failure reveals a missed condition. | Preserve the counterexample in the existing regression detector where practical. |

Tests constrain intended behavior while allowing implementation to change.
Avoid cementing speculative interfaces, internal call sequences, or incidental
structure. For example, a timed-out external operation may need to remain
"outcome unknown" even while its interfaces, persistence, and control flow are
being redesigned. Protect that distinction rather than one implementation of it.

An existing implementation may need characterization checks before refactoring.
Label observed behavior separately from required behavior: reproducing what the
old code does is not evidence that its assumptions or outcomes are correct.

## Exploration is not a testing exemption

A discarded experiment does not automatically deserve a permanent test suite.
The obligation increases when its behavior is retained, its conclusions are
relied upon, or further work is built on it. Do not use "prototype" or "still
changing" to postpone protection of established behavior.

Manual verification can answer an early question, but a one-off demonstration is
not a repeatable regression check. Automate retained, consequential behavior
where practical. When automation is impractical, preserve a reproducible check
and its limitations rather than silently treating the behavior as protected.

"Make it work" does not mean the mocks agree or the happy path looked right
once. Define success against the actual requirement. Where security,
performance, or failure handling determines viability, address it in the initial
experiment, not a later cleanup phase. Never defer protections against
irreversible harm in the name of exploration.

## Delivery and review

Construction feedback and delivery gates answer different questions. Keeping early testing light does not waive broader verification, review, or CI required before delivery. Follow explicit project requirements and documented instruction precedence, including a project mandate for test-first work.

Review whether retained behavior has meaningful, proportionate protection.
Missing protection is a finding; writing the test after the initial
implementation is not, unless the project explicitly requires test-first work.
Identify unsupported claims and remaining verification gaps without mistaking
passing checks for proof of every solution property.
