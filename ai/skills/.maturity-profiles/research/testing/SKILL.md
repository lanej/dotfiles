---
name: testing
description: Use when selecting, writing, running, or reviewing verification for a research project. Apply minimum effective testing for its current maturity and preserve repository gates.
---

# Testing: research

## Protect the experiment’s steel thread

Start with one useful steel-thread check through the experiment's real entrypoint, enough to notice a surprising backward step. A small executable smoke check may suffice; do not build a broad suite before the experiment can answer its question. Compile/typecheck and exercise the relevant real boundary where applicable.

A truly disposable experiment may justify no durable automated tests when their maintenance or setup cost outweighs useful protection. State the observed result and limits. Retained or repeatedly used work should keep its narrow regression check so later iterations do not silently undo the useful result. Do not speculate about every error path or future architecture.

Read [minimum effective testing](references/principles.md) for test selection, diagnostic assertions, and verification boundaries. This entrypoint is selected by source-code setup for the installed stage. Preserve authored project requirements.

For installed generated language profiles, run `python3 scripts/check-source-code.py LANGUAGE` for the configured gate. Use existing repository commands and the applicable language guidance otherwise. Run affected checks after relevant changes and distinguish local evidence from hosted and external outcomes.
