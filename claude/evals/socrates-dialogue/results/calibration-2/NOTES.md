# Second calibration — not an adoption result

Baseline: `71a4f0fcf72a408eb5302f90a965361d1ec0402c`; candidate: `52edfa3`.
Both arms used `claude-sonnet-5[1m]`, medium effort, one trial per scenario and four
workers. The fixtures and prompt hashes are retained in the manifest.

This comparison is invalid as an adoption result: the new `hidden_choice` call
failed at the CLI structured-output boundary after five internal schema retries.
It produced no valid second-turn result. Both arms of that pair were retried once
with the exact saved prompts and settings, preserving the first attempt; the
pair retry was diagnostic and is not substituted into this run's summary.

Other candidate failures still required changes:

- `new-new_evidence-1` placed the full revised specification in `reply`, then put
  a "see above" reference in `spec`. The mechanical artifact checks correctly
  failed. It also asked about a backlog deadline absent from the fixture, then
  asserted full-scan purge behavior that had not been supplied as evidence.
- `new-legacy_scores-1` corrected the deletion-authority error and preserved the
  historical evidence, but stopped at `specification_complete` and offered to
  plan later. `/socrates` must automatically enter planning after this migration.
  Its historical heading "Pass 4" preserved the pass value, so the separate
  literal `Current Pass` check was overly strict. The next checker accepts either
  label; the failed endpoint remains a real failure.
- `new-unsupported_premise-1` retained the concrete operation, narrow reporting,
  and stop conditions, but called a speculative instrumentation limitation
  "accepted" without a supporting user statement. The evidence rule now applies
  explicitly to Risks and Known Blind Spots as well as the decision table.

The next candidate reinforces automatic planning after legacy adaptation and the
evidence labels throughout the artifact. The common schema/driver more clearly
separates the conversational reply from the complete specification. The new-policy
fixture now supplies the observed purge behavior and the policy's effective point
so a real rollout decision is not left implicit. Both arms are rerun with identical
revised fixtures, driver, model, and effort. Neither calibration is counted as a pass.
