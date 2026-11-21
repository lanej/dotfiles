# typescript: installed check profile

Run `python3 scripts/check-source-code.py typescript` for the installed lifecycle gate. The selected stage entrypoint controls required checks; standalone modes describe available tools and do not add another stage’s gates. Preserve stronger repository requirements. Missing tools and failed checks require resolution or a reported limit, never a silent skip.

Read `rollout` from the installed `.typescript-quality.json`, then load only [strict enforcement](rollout-strict.md) for `strict` or [ratcheted enforcement](rollout-ratchet.md) for `ratchet`. Do not infer rollout from project age or lifecycle stage. Resolve missing or unknown rollout before changing enforcement or claiming a baseline allowance.

When the selected stage requires lint, use Biome alongside typed ESLint and the existing formatter. Standalone `lint`, `typecheck`, `test`, and `audit` modes isolate checks; `fmt` requires explicit TypeScript paths and is the only source-writing mode. Treat parser errors, uncovered source, failing project checks, and suppression-policy violations as failures. Read [the correctness guide](correctness.md) when adopting, tuning, or explaining the profile.
