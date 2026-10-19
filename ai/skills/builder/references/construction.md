# Software construction

First make it work, then make it good, then make it fast. "Work" means the
smallest meaningful behavior, not the entire system or merely compiling.

This policy governs how software is developed. The accompanying
[Pragmatic Hexagonal Architecture standard](standard.md) governs properties of
the resulting software. Neither a development sequence nor a passing checklist
establishes those properties. TDD is optional; verification is not.

## Establish a working path, then preserve what is learned

Begin with the smallest executable path that can establish whether the approach
works. Prefer a real, observable result over broad scaffolding, speculative
abstractions, or a comprehensive implementation that has not been exercised.
Identify the consequential question and what observation could contradict the
proposed answer. The first useful result may be a clear failure.

Choose the initial feedback mechanism to resolve that question. Direct
execution, manual inspection, a small harness, or an automated test can each be
appropriate. A mock cannot resolve uncertainty about the real boundary it
replaces. Use a safe sandbox, representative fixture, or authorized integration
experiment; never bypass permissions or production protections to get a result.

As understanding emerges, turn it into repeatable checks. Do not wait for the
whole feature to be complete or the implementation to stabilize. Once meaningful
behavior is established and will be retained, protect it before expanding the
scope or materially restructuring the path. Prefer extending an existing
behavioral detector over creating parallel harnesses.

Work in small loops: establish a behavior, verify it, protect it, and simplify.
Expand from a working foundation rather than accumulating unverified
construction. Plan these increments together, not "implement everything" followed
by "add tests." This is not a prescribed commit sequence or a report per loop.

## When tests enter

When a meaningful success can be distinguished from a plausible failure, there
is something worth testing. This often occurs before the implementation feels
stable. Unknown implementation is not the same as unknown required behavior.

| Situation | Guidance |
|---|---|
| Required behavior is clear; implementation is uncertain. | Write the test early when it provides the clearest feedback. It may precede implementation. |
| Integration or approach feasibility is uncertain. | Run the smallest credible experiment against the relevant real boundary; state what remains unverified. |
| A meaningful path works and will be retained. | Capture a repeatable check before expanding or materially restructuring it. |
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

Construction feedback and delivery gates answer different questions. Introducing
tests after an exploratory first step does not waive broader verification,
review, or CI required before delivery. Follow explicit project requirements and
documented instruction precedence, including a project mandate for test-first
work. Do not infer a reduced verification posture from task size or uncertainty.

Review whether retained behavior has meaningful, proportionate protection.
Missing protection is a finding; writing the test after the initial
implementation is not, unless the project explicitly requires test-first work.
Identify unsupported claims and remaining verification gaps without mistaking
passing checks for proof of every solution property.
