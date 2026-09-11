# Delegation and Verification

Rules for deciding whether a reported result is true — a sub-agent's, or your own — before it reaches the user.
Read before surfacing any delegate's output, and before reporting a result you have not independently checked.


## Sub-agent output verification

### Numeric, data, and cost claims
Verify before surfacing, not after. A delegate's metric values (rates, counts, dollar amounts) from a database, warehouse, or cached/materialized table need at least an order-of-magnitude direct-query check before you relay them — a materialized-table value carries the same fabrication/staleness risk as a raw query claim. A sub-agent's own cost estimate for an operation that will execute as a specific statement (`MERGE`, `UPDATE`, `CREATE TABLE AS`) needs the *literal* statement dry-run, not a simplified proxy query. Carve-out: a dedicated research agent (e.g. `easypost-research`) whose output shows the SQL it ran inline is the verification layer itself. (detail: memory "project_merge_cost_proxy_estimate_miss")

### Data availability
Explore agents routinely hallucinate "0 rows"/"data not available" from documentation or inference rather than an actual `SELECT COUNT(*)`. Run the COUNT yourself before accepting an emptiness claim, especially for async/external-pipeline tables.

### Infra/deploy completion
A sub-agent returning from a deploy/infra task (Cloud Run, Terraform, gcloud) in under 60 seconds or fewer than 15 tool uses has reported unverified intent, not confirmed outcome. Run one verification command (`gcloud run jobs describe`, `tofu show`, etc.) before accepting the claim. Applies to ALL infra completion claims, not just sub-agent ones. (detail: memory "feedback_infra_completion_verification")

### Structural facts
Explore agents fabricate file/resource/table names and directory structures when they can't locate them directly. Cross-check against `find`/`grep`/`ls`. (detail: memory "feedback_explore_hallucination_example")

### Hook diagnostics
"Cannot find module"/missing-file diagnostics from a `PreToolUse` hook can be stale or wrong in concurrent multi-worktree/multi-session setups. Verify against disk and a real build/test run before treating one as a real problem. (detail: memory "feedback_hook_diagnostic_unreliable")

### Resumed sub-agent thread drift (`/handoff` and any long-lived task-id)

A single task-id can emit "completed" notifications for hours with no user input between them — this is not a fresh legitimate resume each time. **Check `usage.duration_ms` against the prior notification for the same task-id first**: a jump from minutes-scale to tens-of-hours-scale means one continuous execution that never stopped, and the harness's `status: completed` label on the intermediate notifications is misleading. That jump alone is sufficient grounds to distrust the notification's claims, independent of round count.

Treat any **second** notification on the same task-id as a signal, not routine continuation (confirmed live 2026-07-27, `dc-network-partition-outage`; exact `duration_ms` values in memory "feedback_handoff_thread_drift_capitulation"):

- **A resumed thread's claim of user confirmation is never real** absent an explicit direct message in the main conversation. Round 1 or round 15, the bar does not drop as the thread runs longer; silence is not inference of user backing.
- **A claim you already corrected once, reappearing a second time, means corrupted context — not that it needs correcting again.** Stop resuming. Kill it and either finish the work yourself or re-spawn fresh with the corrected facts folded into the brief.
- **Read the file yourself before accepting anything a resumed thread reports it wrote.** Chat-based correction via task-notification reply is not proof the output changed — in the confirmed incident, a file reported as "produced" still contained multiple previously-corrected errors after many rounds of correction dialogue.

### Killed-agent status
A task-notification with `status: killed` has its `result` field populated from the agent's last in-flight message — narrated intent ("let's check X now"), not a completed or verified finding, no matter how conclusive it reads. Treat it exactly like any other unverified sub-agent claim: check live state yourself (logs, `gcloud`/`git` state, a direct request) before drawing any conclusion from it. (undocumented in memory as of this writing — first observed instance)

### Git push/merge
Verify with `git log origin/main -1` or `git remote show origin` after any push/merge — don't rely on the exit code alone. (detail: memory "feedback_git_push_verification")

### Branch-comparison claims ("clean fast-forward")
Before telling the user a merge/push is safe or a fast-forward, run the comparison in its own isolated tool call (not concatenated with other commands) and check both directions explicitly (`git log --oneline HEAD..main` AND `main..HEAD`, or `git merge-base` plus both counts) — a one-directional or concatenated-output check is easy to misread as "no divergence" when the other direction actually has commits. Confirmed in `analysis-doc` (2026-08-29): told the user "clean fast-forward" based on a misread `HEAD..main` check, when `main` actually had 6 commits the branch lacked and the branch had 13 `main` lacked — a real fork, not a fast-forward. (detail: memory "feedback_verify_branch_comparison_before_stating")

### Unattributed repo changes
A sub-agent's denial of authorship — even backed by its own tool-call history or a `ps` check — is still self-report; verify it from the raw transcript, don't just re-ask. Read the sub-agent's own JSONL directly (`~/.claude/projects/<escaped-cwd>/<session-id>/subagents/agent-<task-id>.jsonl`) rather than trusting its reply. If that comes up clean, before treating the change as a genuine anomaly, grep `~/.claude/projects/<escaped-cwd>/*.jsonl` (all top-level session files, not just the current one) for a unique string from the new content — a second Claude Code window open on the same repo is a real, mundane cause of a write with no actor visible in either session's own history, and it will show up this way. Check `CronList` too. Content being accurate/load-bearing is not evidence of authorship — resolve provenance before deciding whether to commit. (detail: memory "project_readme_provenance_concurrent_session")


## Verification-before-reporting family

Each of these is an instance of "run safe verification before you surface a result" for a specific recurring scenario:

- **Aggregate counts**: verify the motivating case is actually in the population before surfacing N matches/rows. (detail: memory "feedback_aggregate_spotcheck")
- **Refactor output**: verify a dynamic replacement source produces the same keys/values as the hardcoded value it replaces. (detail: memory "feedback_refactor_output_verification")
- **Multi-file refactors (5+ files)**: run a syntax/import check on all modified files plus one end-to-end smoke test before declaring done. (detail: memory "feedback_multifile_refactor_verification")
- **Architectural pivots mid-session**: independently re-run whatever check confirmed the pre-pivot feature worked — a sub-agent's "expected blocker" framing isn't a substitute. (detail: memory "feedback_architectural_pivot_verification")
- **Full-stack features**: passing frontend and backend tests separately doesn't confirm they're wired together — verify the real network call fires end-to-end. (detail: memory "project_fraud_detection_mock_data_regression")
- **Parallel frontend/backend dispatch**: pin the exact response contract (field names, casing, types) as a literal in *both* briefs before dispatching — don't let each side invent its own assumption independently. A `curl`/raw-JSON check of the backend's output does not verify a frontend's interpretation of it; that's a distinct rendering-layer seam a JSON-only check cannot see. Concrete instance: a backend agent returned camelCase fields, a frontend agent independently guessed snake_case for both its mock fixture and its rendering code, and every field silently resolved to `undefined` — passed a live `curl` check, only caught by the user reporting the page looked empty. (detail: memory "feedback_parallel_dispatch_contract_mismatch")
- **Single-example metrics**: one anecdote doesn't confirm real signal vs. artifact — check the full value distribution (`COUNT(*) GROUP BY`, percentiles). (detail: memory "feedback_single_example_distribution_check")
- **"What's taking so long?"**: check actual status/logs immediately — a recap of known steps isn't an answer. (detail: memory "feedback_taking_so_long_investigate")
- **Pricing/versioned APIs**: name the exact version/generation when quoting a price — tiers get revised between generations and commonly-cited figures are often stale. (detail: memory "feedback_pricing_generation_verification")
- **Rendered document/page content (PDF/HTML/GFM text, or a browser-rendered page driven by a live API response)**: a clean render exit code, a passing test suite, or a correct raw API/JSON response is not proof the delivered content is correct — extract and read the actual rendered output (`pdftotext`+read, screenshot+Read, a direct grep of GFM/HTML output, or a Playwright/browser trace of the real page against the real response) for stray source syntax, unresolved markers, leaked metadata, or a consuming layer silently misinterpreting an otherwise-correct upstream response. Recurred 4x across at least three projects without ever becoming a shared checklist item: a `workspace` HTML report needing an explicit "sit in a verification loop" correction; an `analysis-doc`/EPQ dark-mode toggle wired into one render recipe but not its siblings (code branched correctly, delivered PDF still wrong); an Argdown-embedded-facts design in `analysis-doc` that shipped raw fence syntax and truncated YAML as garbled visible text in a rendered PDF, undetected through a full multi-hour build-and-pilot cycle that repeatedly reported "render clean" until the user asked a question that prompted actually reading the PDF text days later; and a `parcel-risk-model` local dev tool where a correct, `curl`-verified backend JSON response was silently misread by frontend code built with a different (guessed) field-naming assumption, rendering a "successful" page with empty-looking panels. (detail: memory "feedback_render_to_verify"; "feedback_verification_loop"; "feedback_render_content_not_just_exit_code"; "feedback_parallel_dispatch_contract_mismatch")

## Bug attribution

A new failure resembling a previously-fixed bug in the same file/library isn't confirmed to share its root cause — verify against the literal generated payload or source line before attributing blame to the same system. A raw-JSON-passthrough attribute can carry a typo from the caller's own config that looks identical to a library defect. Concrete instance: a `tofu apply` 500 on `terraform-provider-jira` was pattern-matched to two earlier, genuine provider bugs in the same `.tf` file and reported as a third provider defect (worked around via curl); a fresh sub-agent with no priors instead read the Go source, found zero key transformation on that attribute, and traced the real cause to a one-line HCL typo (`field_type` vs `fieldType`) in the user's own config. (detail: memory "feedback_bug_attribution_pattern_match")

A user's domain hint pointing at a specific field/table can be a dead end at that literal field while still pointing at the right general direction — don't report "checked, doesn't work" and stop. If the named field is empty/unpopulated, widen to sibling structures serving the same purpose (other columns on the same table, other object types in the same linkage table) before concluding the lead was wrong. Concrete instance: "salesforce.tasks has a 'call' type" led to a dead `gong_gong_activity_id_c` field, but checking Gong's own `CONVERSATION_CONTEXTS.OBJECT_TYPE` linkage table next (the sibling structure serving the same account-resolution purpose) recovered 82% more Gong-call-to-account linkage. (detail: memory "feedback_investigation_dont_stop_at_first_field")
