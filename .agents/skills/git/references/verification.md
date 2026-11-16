# Verification reference

Choose checks for the behavior and risks being changed. Follow explicit repository
requirements; routine prose and configuration edits usually need diff review and
applicable syntax or structural checks. Software construction follows Builder.

## Proportionate verification

Start with the smallest check that could contradict the intended behavior. A simple alias, argument selector, or configuration edit should not require a full application environment merely because it shares a directory or Makefile with one. Retain stronger protection for work preservation, destructive operations, installation, concurrent state, and real terminal interactions.

Prefer improving an existing focused check. Add independent checks when features need independent execution or failure isolation; the number of tests is not the goal. Cover meaningful failure risks without enumerating every branch. A failed setup or unrelated assertion must not be mistaken for evidence about behavior the test never reached.

Use controlled external responses to verify local decisions, while exercising the actual caller entrypoint. Use a real dependency when establishing compatibility or behavior at that boundary. State that distinction clearly. Choose cross-platform runs for actual OS differences, and avoid making routine feedback depend on credentials, network downloads, or native builds unnecessarily.

Run the affected check once, then stop when it passes unless relevant changes, a failure, or a concrete unresolved interaction require more evidence. Consider execution time, setup cost, flakiness, and the ability to diagnose failures when retaining or expanding a test.

## Verification Rigor Tiers

These names classify evidence and `Detected-By` trailers. They do not require every
change to run every tier or invoke a reviewer at each checkpoint.

| Tier | Evidence |
|---|---|
| V0 | Diff review and applicable syntax, compile, or lint checks |
| V1 | Affected feature's acceptance check through its real entrypoint |
| V2 | Broader suite, lint, or type checks needed to assess interactions |
| V3a | Independent review of a bounded increment when complexity warrants it |
| V3b | Independent review of the assembled change when complexity warrants it |
| V4 | CI results for the merged commit, where CI exists |

Use the affected check after a change. Broaden checks when changed shared behavior,
a failure, or an unresolved interaction justifies it. After a fix, rerun checks whose
results the fix invalidated. State boundaries such as local-only or simulated validation;
a local pass does not establish a CI or live-integration pass.

## Selecting CI

Feature workflows follow their implementation, configuration, and detector paths. A shared `Makefile` edit runs setup checks rather than every feature suite. When changing a feature's Make recipe, run its affected detector explicitly; feature workflows also support manual dispatch.

Shell lint wiring has its own workflow. Small command wrappers should exercise the real wrapper with controlled external-command responses when that establishes their behavior; they do not need a terminal, editor, or native plugin build for argument selection alone. Such a check establishes the wrapper's decisions, not compatibility with the external program.

Keep independently selectable features out of long acceptance journeys. For example, `make test-zellij-attach` checks launcher selection through the `zj` alias with the Zellij CLI simulated; `make test-zellij-sessions` checks real popup, detach, and shutdown interactions.

Wait for checks relevant to the changed behavior before merging. Unrelated pending integration jobs do not automatically become merge gates; investigate failed checks and report unresolved limits. Required repository checks still apply.

## Acceptance checks and harness verification

An acceptance check uses the real entrypoint a caller uses, asserts an observable
outcome, and fails if the behavior it protects is deleted. An internal helper call or
mock invocation count alone does not establish that outcome.

Keep focused regression protection for each user-visible feature. Improve the existing detector for a regression, and keep independently selectable features independently runnable. Neither a helper nor an input variant automatically needs another test; neither a test-count target nor a shared fixture justifies combining unrelated features.

When wiring a new harness, establish sensitivity once:

1. Check independently specified behavior and confirm green.
2. Introduce a controlled defect and confirm the intended failure, not a setup error.
3. Manually undo the exact edit and confirm green.

Do not use destructive Git commands to break or restore the implementation. Work in
the target directory and preserve unrelated changes. This verifies the detector; it
does not prove every software property or mandate test-first development.

## Review Fault Classes

Use the classes relevant to the changed behavior when briefing an independent reviewer:

- Untrusted input reaching paths, identifiers, locks, or interpreters before validation.
- Errors swallowed into an apparently successful or empty result.
- Stale state or comparisons made against an outdated reference.
- Failures reported only after an irreversible effect has already occurred.
- Inconsistent behavior across platform adapters or parallel implementations.
- Cross-task drift: individually coherent changes that contradict one another.
- Validation rules that permit values their stated contract rejects.
- Local and CI environment differences that invalidate a claimed result.

Report actionable findings with evidence and locations. Follow repository rules for
when independent review is required; do not manufacture findings or assurance.

## Recording the detector

For a commit fixing a fault found after implementation, record the earliest tier that
found a corrected fault with a `Detected-By:` trailer. Valid values are `V0`, `V1`, `V2`,
`V3a`, `V3b`, `V4`, and `user`. Use `user` when a person identified the specific defect,
not when a general request prompted an automated check that found it.
