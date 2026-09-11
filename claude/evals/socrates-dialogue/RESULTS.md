# Socrates dialogue comparison

The revised instructions pass all eight scenario-specific readiness and
preservation checks in the final paired run. The old instructions pass two.
This is one reviewed sample per scenario, not a general performance estimate.

## Final comparison

Both arms received identical scenario context and scripted user answers, with the
same model and settings. Future answers and review rubrics were withheld. Each arm
made 12 turn calls across eight scenarios. No infrastructure errors occurred.

| Setting | Value |
|---|---|
| Baseline | `71a4f0fcf72a408eb5302f90a965361d1ec0402c` |
| Candidate | `6cbd3a45d80802f75d6a7a2d60f762157a301424` |
| Requested and observed model | `claude-sonnet-5[1m]` |
| Effort | `high` |
| CLI | Claude Code 2.1.268 |
| Samples | One paired trial per scenario |
| Concurrency / timeout | Four jobs / 360 seconds per call |

The [manifest](results/final/manifest.json) identifies commits and prompt/fixture
hashes. The [fixture snapshot](results/final/scenarios.json) preserves exactly what
was tested. Subsequent report, capture, and review-command permission changes do
not alter the tested `/socrates` or `/specify` prompt bundles.

| Scenario | Old | Revised | Observed difference |
|---|---|---|---|
| Simple, clear request | Fail | Pass | Old flow blocks on a hypothetical anchor and reconfirms explicit scope; revised flow proceeds from the supplied criteria. |
| Hidden consequential choice | Fail | Pass | Both find the missing duration; old flow then reopens authorization/notification after it is settled. |
| Conflicting requirements | Fail | Pass | Both find the conflict; old flow adds questions and a latency allowance that weakens the chosen exact cutoff. |
| Unsupported premise | Fail | Pass | Both challenge the premise; old final spec contradicts its accepted failure branch with escalation instructions. |
| Accepted tradeoff | Pass | Pass | Both preserve the manual process, accepted seven-day delay, and one-time review after two Fridays. |
| Genuinely new evidence | Fail | Pass | Old flow treats a ceiling as the target and reopens implementation scope; revised flow asks for the replacement value and preserves other choices. |
| Resolved critique on resume | Pass | Pass | Both retain the incorporated finding and approved v3 plan without restarting reconciliation. |
| Legacy confidence scores | Fail | Pass | Old flow asks the user to reaffirm an authoritative answer; revised flow corrects the unsupported note, preserves history, and versions once. |

Each scenario must pass endpoint/fact checks **and** all four documented review
checks: readiness and endpoint, seeded blockers, decision preservation, and an
executable specification. These are conjunctive requirements, not averaged scores.

| Measure | Old | Revised |
|---|---:|---:|
| Completed scenarios | 8 | 8 |
| Mechanical endpoint/fact passes | 4 | 8 |
| Scenarios passing every check | 2 | 8 |
| Unnecessary questions | 9 | 0 |
| Repeated questions | 5 | 0 |
| Premature planning turns | 1 | 0 |

Question counts are assessed separately and may overlap. Independent information
requests count separately even when bundled into one reply. The records and
[review notes](results/final/reviews.json) identify the questions and evidence for
every judgment. Both arms received the same scripted turns; fewer turns alone is
not evidence of improvement. Captured `record.json` files are collapsed as generated
content in GitHub diffs; the review notes remain visible.

The [review gate output](results/final/review-summary.json) reports
`candidate_passes_all_checks: true`. Reproduce that gate without model calls:

```sh
python3 claude/evals/socrates-dialogue/review.py \
  claude/evals/socrates-dialogue/results/final \
  --reviews claude/evals/socrates-dialogue/results/final/reviews.json
```

## Calibration and retained failures

Four earlier full comparisons did not establish readiness. Their manifests,
fixture snapshots, records, and explanations remain under
[calibration](results/calibration/NOTES.md),
[calibration-2](results/calibration-2/NOTES.md),
[calibration-3](results/calibration-3/NOTES.md), and
[calibration-4](results/calibration-4/NOTES.md). A diagnostic pair retry is retained
inside calibration-2 and was not substituted into that aggregate.

The first candidate passed mechanical checks but failed semantic review. Subsequent
runs exposed contradictory outcome handling, premature selection of a retention
target, incorrect legacy versioning, and incomplete planning handoffs. Fixes also
removed scaffold prompts that encouraged invented requirements and accepted risks.
Fixture corrections established already-known timing and implementation facts,
and made the selected retention value different from the policy ceiling; both
arms were rerun after each change. Individual notes explain those changes.

The first three full runs used medium effort; the last two used high effort.
Timeouts in the fourth run invalidated its aggregate; the final run used a longer
timeout for both arms. The final result compares the two flows **within that final
run**. Differences across calibration runs cannot be attributed to instruction
changes alone because fixtures and runtime settings also changed. This change
does not alter the user's configured model or effort.

## Verification and limits

The deterministic suite has 31 passing tests for dialogue replay boundaries,
model/error handling, immutable evidence review, and the shared command contract.
Combined with the existing repository tests, 130 tests pass with four live tmux
tests excluded. Those four tests also failed against unchanged master in this
environment; their implementation is outside this change.

The implementing agent reviewed every final reply and proposed specification.
This is not independent review, and one sample per scenario cannot establish
reliability across tasks or model settings. Evidence is retained for human audit.

The comparison is tool-free. It verifies proposed decisions, specifications, and
handoffs; it does not exercise actual session writes, sockets, native plan mode,
or approval UI. In the revised new-evidence case, an interim reply misspells a
snapshot filename while the final history records the correct `spec-v2` path.
Physical history preservation still requires integration validation. No claim of
installed-command or native end-to-end testing is made.
