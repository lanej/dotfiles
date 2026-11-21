---
name: testing
description: Use when selecting, writing, running, or reviewing verification for a alpha project. Apply minimum effective testing for its current maturity and preserve repository gates.
---

# Testing: alpha

## Protect the main happy paths

Protect the working steel thread and the main happy paths users can actually exercise. Favor a small set of readable checks through real entrypoints over broad helper-level coverage. Extend coverage when a new happy path becomes meaningful retained behavior.

Comprehensive error and boundary testing is not the default here. Add a failure case early when its consequence or uncertainty makes it part of the minimum useful protection. Keep fixtures and setup small enough to support rapid changes to provisional interfaces.

Read [minimum effective testing](references/principles.md) for test selection, diagnostic assertions, and verification boundaries. This entrypoint is selected by source-code setup for the installed stage. Preserve authored project requirements.

For installed generated language profiles, run `python3 scripts/check-source-code.py LANGUAGE` for the configured gate. Use existing repository commands and the applicable language guidance otherwise. Run affected checks after relevant changes and distinguish local evidence from hosted and external outcomes.
