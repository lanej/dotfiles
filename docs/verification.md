# Verification reference

Choose checks for the behavior and risks being changed. Follow explicit repository
requirements; routine prose and configuration edits usually need diff review and
applicable syntax or structural checks. Software construction follows Builder.

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

## Acceptance checks and harness verification

An acceptance check uses the real entrypoint a caller uses, asserts an observable
outcome, and fails if the behavior it protects is deleted. An internal helper call or
mock invocation count alone does not establish that outcome.

Keep one regression detector per user-visible feature. A helper, input variant, or
failure mode is not a separate feature. Improve the existing detector for a regression.

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
