---
name: testing
description: Use when selecting, writing, running, or reviewing verification for a beta project. Apply minimum effective testing for its current maturity and preserve repository gates.
---

# Testing: beta

## Broaden behavior and important failures

Broaden happy-path coverage across the behavior people are adopting. Deliberately exercise important errors, boundaries, and integration failures, choosing cases by consequence and uncertainty. Protect compatibility and migrations where changes affect existing users or data; verify real integration behavior at affected boundaries.

Run the full applicable language profile and preserve existing repository gates. Use independent expected outcomes and real counterexamples. Avoid mechanically enumerating every branch or multiplying equivalent cases; each addition should improve confidence enough to justify its execution, diagnosis, and maintenance cost.

Read [minimum effective testing](references/principles.md) for test selection, diagnostic assertions, and verification boundaries. This entrypoint is selected by source-code setup for the installed stage. Preserve authored project requirements.

For installed generated language profiles, run `python3 scripts/check-source-code.py LANGUAGE` for the configured gate. Use existing repository commands and the applicable language guidance otherwise. Run affected checks after relevant changes and distinguish local evidence from hosted and external outcomes.
