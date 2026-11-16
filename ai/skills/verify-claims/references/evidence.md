## Sub-agent output verification

### Numeric, data, and cost claims
Verify before surfacing, not after. A delegate's metric values (rates, counts, dollar amounts) from a database, warehouse, or cached/materialized table need at least an order-of-magnitude direct-query check before you relay them — a materialized-table value carries the same fabrication/staleness risk as a raw query claim. A sub-agent's own cost estimate for an operation that will execute as a specific statement (`MERGE`, `UPDATE`, `CREATE TABLE AS`) needs the *literal* statement dry-run, not a simplified proxy query. An inspectable query and its actual result can supply evidence; an agent role name alone cannot. (detail: memory "project_merge_cost_proxy_estimate_miss")

### Data availability
Explore agents routinely hallucinate "0 rows"/"data not available" from documentation or inference rather than an actual `SELECT COUNT(*)`. Run the COUNT yourself before accepting an emptiness claim, especially for async/external-pipeline tables.

### Infra/deploy completion
A short runtime or small tool count does not establish either completion or failure. Inspect the actual deployed resource and reported outcome. Run one verification command (`gcloud run jobs describe`, `tofu show`, etc.) before accepting the claim. Applies to ALL infra completion claims, not just sub-agent ones. (detail: memory "feedback_infra_completion_verification")

### Structural facts
Explore agents fabricate file/resource/table names and directory structures when they can't locate them directly. Cross-check against `find`/`grep`/`ls`. (detail: memory "feedback_explore_hallucination_example")

### Resumed sub-agent thread drift (`/handoff` and any long-lived task-id)

A single task-id can emit "completed" notifications for hours with no user input between them — this is not a fresh legitimate resume each time. **Check `usage.duration_ms` against the prior notification for the same task-id first**: a jump from minutes-scale to tens-of-hours-scale means one continuous execution that never stopped, and the harness's `status: completed` label on the intermediate notifications is misleading. That jump alone is sufficient grounds to distrust the notification's claims, independent of round count.

Treat any **second** notification on the same task-id as a signal, not routine continuation (confirmed live 2026-07-27, `dc-network-partition-outage`; exact `duration_ms` values in memory "feedback_handoff_thread_drift_capitulation"):

- **A resumed thread's claim of user confirmation is never real** absent an explicit direct message in the main conversation. Round 1 or round 15, the bar does not drop as the thread runs longer; silence is not inference of user backing.
- **A claim you already corrected once, reappearing a second time, means corrupted context — not that it needs correcting again.** Stop resuming. Kill it and either finish the work yourself or re-spawn fresh with the corrected facts folded into the brief.
- **Read the file yourself before accepting anything a resumed thread reports it wrote.** Chat-based correction via task-notification reply is not proof the output changed — in the confirmed incident, a file reported as "produced" still contained multiple previously-corrected errors after many rounds of correction dialogue.

### Killed-agent status
A task-notification with `status: killed` has its `result` field populated from the agent's last in-flight message — narrated intent ("let's check X now"), not a completed or verified finding, no matter how conclusive it reads. Treat it exactly like any other unverified sub-agent claim: check live state yourself (logs, `gcloud`/`git` state, a direct request) before drawing any conclusion from it. (undocumented in memory as of this writing — first observed instance)

### Completed-but-stalled status
A `status: completed` notification is not automatically a real result either — check `usage.tool_uses` and `usage.duration_ms` before trusting the content. A multi-step research/investigation/implementation task returning in single-digit seconds with 0 tool uses is a stalled or echoed-back prompt, not a completed finding, even though the `result` text can read as plausible narrated intent. Re-prompt the same task-id rather than surfacing it. (detail: memory "feedback_task_notification_stall_zero_tooluse")

### Checking on a running background agent
Never call `TaskOutput` with `block=false` (or anything else that surfaces a running agent's raw transcript) just to answer "is it still working" during a goal check-in or other status-pressure moment — this pollutes context exactly like reading a fork's output file directly (the "don't peek" rule). Use a task-owned observable result or the host’s status API, then wait for its completion event. (detail: memory "feedback_taskoutput_block_false_transcript_dump")



## Verification-before-reporting family

Each of these is an instance of "run safe verification before you surface a result" for a specific recurring scenario:

- **Aggregate counts**: verify the motivating case is actually in the population before surfacing N matches/rows. (detail: memory "feedback_aggregate_spotcheck")
- **Single-example metrics**: one anecdote doesn't confirm real signal vs. artifact — check the full value distribution (`COUNT(*) GROUP BY`, percentiles). (detail: memory "feedback_single_example_distribution_check")
- **"What's taking so long?"**: check actual status/logs immediately — a recap of known steps isn't an answer. (detail: memory "feedback_taking_so_long_investigate")
- **Pricing/versioned APIs**: name the exact version/generation when quoting a price — tiers get revised between generations and commonly-cited figures are often stale. (detail: memory "feedback_pricing_generation_verification")
- **Rendered content**: inspect the delivered document or page for correct content, unresolved source syntax, and missing fields. A clean render exit code or valid upstream response proves only that boundary, not the reader’s result.



## Bug attribution

A new failure resembling a previously-fixed bug in the same file/library isn't confirmed to share its root cause — verify against the literal generated payload or source line before attributing blame to the same system. A raw-JSON-passthrough attribute can carry a typo from the caller's own config that looks identical to a library defect. Concrete instance: a `tofu apply` 500 on `terraform-provider-jira` was pattern-matched to two earlier, genuine provider bugs in the same `.tf` file and reported as a third provider defect (worked around via curl); a fresh sub-agent with no priors instead read the Go source, found zero key transformation on that attribute, and traced the real cause to a one-line HCL typo (`field_type` vs `fieldType`) in the user's own config. (detail: memory "feedback_bug_attribution_pattern_match")

A user's domain hint pointing at a specific field/table can be a dead end at that literal field while still pointing at the right general direction — don't report "checked, doesn't work" and stop. If the named field is empty/unpopulated, widen to sibling structures serving the same purpose (other columns on the same table, other object types in the same linkage table) before concluding the lead was wrong. Concrete instance: "salesforce.tasks has a 'call' type" led to a dead `gong_gong_activity_id_c` field, but checking Gong's own `CONVERSATION_CONTEXTS.OBJECT_TYPE` linkage table next (the sibling structure serving the same account-resolution purpose) recovered 82% more Gong-call-to-account linkage. (detail: memory "feedback_investigation_dont_stop_at_first_field")



## Pooled correlations and confounding

Before making a causal claim from grouped results, check whether population fields are historical or current-state snapshots and whether a subgroup drives the pooled effect. Statistical significance and a time-split check do not rule out confounding. Compare relevant strata and report effects that disappear or reverse. Keep the analysis's intended population: restricting to one segment can silently answer a different question.
