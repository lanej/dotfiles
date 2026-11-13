# GitHub review evidence

`DORA_silver.github_pr_events` deduplicates retained deliveries by topic, GitHub delivery ID when present (otherwise Pub/Sub message ID), and projection version. `DORA.github_pr_observations` projects supported `github-evidence-v1` observations with scoped repository/PR and review/comment identity, source and observation timestamps, body availability, Unicode characters and UTF-8 bytes.

Query description, review-summary and comment histories separately through `github_pr_description_history`, `github_pr_review_history` and `github_pr_comment_history`. Edits/deletions are observations, not reconstructed historical state. Empty bodies have zero size; unavailable bodies have null size. Untimed review edits/dismissals retain publication-order ambiguity. Internal assessment/snapshot requests are retained but excluded from review metrics.

`DORA.copilot_reviews` retains Copilot verdicts, review bodies and linked inline evidence. It requires GitHub Bot type and the exact case-insensitive reviewer login `Copilot` or `copilot-pull-request-reviewer[bot]`; the analytical flag derives from retained identity so earlier false classifications are repaired. It does not evaluate correctness. Inline evidence is scoped and aggregated before joining to reviews to prevent row multiplication.

`DORA.github_pr_body_trends` derives object state at observation cutoffs, preserving deletion and newer event evidence over older snapshots. Counts and body sizes distinguish description, inline, discussion and review-summary kinds. `DORA.github_pr_cohort_trends` exposes creation/merge cohorts using each PR's latest cutoff and weighted means. History expansion can be expensive; bound query scope and billed bytes. Read the data dictionary for full column types and limits.
