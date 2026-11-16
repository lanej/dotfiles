---
name: testing
description: Use when selecting, writing, running, or reviewing verification for a production project. Apply minimum effective testing for its current maturity and preserve repository gates.
---

# Testing: production

## Cover consequential behavior and recovery

Cover consequential supported behavior comprehensively: important happy paths, errors, boundaries, affected integrations, compatibility, and recovery. Verify relevant rollback, retry, concurrency, or operational behavior when the change depends on it. Preserve explicit release and repository gates, and obtain independent review for consequential interactions.

Comprehensive protection does not mean testing every implementation detail or every combination. Consolidate redundant coverage, remove obsolete fixtures deliberately, and keep checks diagnostic and maintainable. A small clear suite can provide more useful protection than a large brittle one. State what automation establishes, what was observed manually, and what remains unverified; a maturity label does not establish reliability.

Read [minimum effective testing](references/principles.md) for test selection, diagnostic assertions, and verification boundaries. Confirm the current stage in `.source-code.json`; this entrypoint is selected by source-code setup. Preserve authored project requirements.

For installed generated language profiles, run `python3 scripts/check-source-code.py LANGUAGE` for the configured gate. Use existing repository commands and the applicable language guidance otherwise. Run affected checks after relevant changes and distinguish local evidence from hosted and external outcomes.
