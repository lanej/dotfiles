# Verification

Run `python3 scripts/check-source-code.py typescript` for the installed lifecycle gate. The selected stage entrypoint controls required checks; standalone modes describe available tools and do not add another stage’s gates. Preserve stronger repository requirements. Missing tools and failed checks require resolution or a reported limit, never a silent skip.

<!-- source-code:legacy-routing -->
Read the installed `references/rollout.md` in this skill package for enforcement and baseline obligations. Preserve that enforcement; changing lifecycle stage does not change rollout.
<!-- /source-code:legacy-routing -->

When the selected stage requires lint, use Biome alongside typed ESLint and the existing formatter. Standalone `lint`, `typecheck`, `test`, and `audit` modes isolate checks; `fmt` requires explicit TypeScript paths and is the only source-writing mode. Treat parser errors, uncovered source, failing project checks, and suppression-policy violations as failures. Read [the correctness guide](correctness.md) when adopting, tuning, or explaining the profile.
