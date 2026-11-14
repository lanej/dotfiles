# Delegation and Verification

Rules for deciding whether a reported result is true — a sub-agent's, or your own — before it reaches the user. Read before surfacing any delegate's output, and before reporting a result you have not independently checked.

## Sub-agent output verification

### Numeric, data, and cost claims
Verify before surfacing, not after. A delegate's metric values (rates, counts, dollar amounts) from a database, warehouse, or cached/materialized table need at least an order-of-magnitude direct-query check before you relay them — a materialized-table value carries the same fabrication/staleness risk as a raw query claim. A sub-agent's own cost estimate for an operation that will execute as a specific statement (`MERGE`, `UPDATE`, `CREATE TABLE AS`) needs the *literal* statement dry-run, not a simplified proxy query. Carve-out: a dedicated research agent (e.g. `easypost-research`) whose output shows the SQL it ran inline is the verification layer itself. (detail: memory "project_merge_cost_proxy_estimate_miss")

### Data availability
Explore agents routinely hallucinate "0 rows"/"data not available" from documentation or inference rather than an actual `SELECT COUNT(*)`. Run the COUNT yourself before accepting an emptiness claim, especially for async/external-pipeline tables.

### Infra/deploy completion
A sub-agent returning from a deploy/infra task (Cloud Run, Terraform, gcloud) in under 60 seconds or fewer than 15 tool uses has reported unverified intent, not confirmed outcome. Run one verification command (`gcloud run jobs describe`, `tofu show`, etc.) before accepting the claim. Applies to ALL infra completion claims, not just sub-agent ones. (detail: memory "feedback_infra_completion_verification")

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

## Peer-session coordination (Constitution II)

When coordination with an existing peer is relevant and messaging is authorized, use the host’s supported coordination tools. Do not contact peers or delay a question about Josh’s intent merely because a historical workflow did so. The procedure:

- `ListAgents` exposes no cwd field, so matching a peer to a repo is a best-guess name match. Peer sessions only — sub-agents you dispatched already report back through the normal `Agent` loop.
- Only questions a peer can answer from its own activity qualify: what it is doing, what it is touching, or negotiating sequencing ("I'll hold off on X until you're done"). A question about Josh's own intent, preference, or scope — including a Constitution III second-occurrence escalation — goes straight to Josh. A peer cannot answer on Josh's behalf.
- Wait only a short, bounded timeout. Most ordinary interactive peer sessions hold inbound messages for manual approval unless launched with `crossSessionInbound` set to accept, so a reply may never come. On timeout, ask Josh exactly as you would have, noting the coordination attempt got no response.
- Verify a peer's coordination claim against observable state (git status/diff, file mtimes) before relying on it — same standard as any other cross-session input.
- A peer's agreement is never authorization for a destructive, hard-to-reverse, or shared-visible action (pushing to a remote, PR/issue/comment creation, `apply`-class infra commands, destructive git operations). That still requires Josh's own words.
- If a scan surfaces an *unrelated* active project with recent activity, mention it to Josh as an FYI when it naturally comes up — never message that unrelated peer on the strength of that alone.

## Receipt contracts and capabilities

Findings return inline by default. Before requesting a named file, inspect the selected role’s current permissions and available tools. A read-only reviewer may inspect files or run read-only shell commands while still being unable to write a receipt. Do not infer today’s capabilities from a historical role name or tool inventory.

Use a file receipt only for an authorized write-capable agent and verify the file exists and contains the promised result. Otherwise request concise inline findings or choose an authorized agent with the needed capability. A claimed write remains unverified until inspected.

## Task dependency and parallel dispatch

Before dispatching an already-written multi-task plan, annotate each task with what prior task(s) it actually reads/depends on — not just its position in the numbered list. Parallelize independent tasks only when delegation is authorized and shared resources permit it. A Plan agent or critique pass that checks task *correctness* (file lists, check ordering) won't surface this on its own — it has to be asked for explicitly. (detail: memory "feedback_serial_dispatch_missed_parallel_tasks")

Don't launch two or more GCP-touching `Agent` dispatches in true simultaneous parallel (single message, multiple tool_use blocks) when each will independently touch `gcloud`/ADC-backed clients early in its run — this can race on ADC refresh and kill both with `invalid_rapt`/`invalid_grant`, which looks like a genuine expired credential but isn't. Stagger them instead. If one dies on this error, verify with your own direct GCP tool call (same credential store) before deciding whether to retry (transient race) or ask Josh to reauth (genuine expiry) — don't assume either without checking. (detail: memory "feedback_parallel_gcp_agent_credential_race")

A delegate doing work beyond its brief has deviated from scope. Inspect the extra effects and preserve any evidence or recovery state; do not treat completion as authorization. Resolve the scope with the owner when existing instructions do not authorize accepting or extending that work.

## Skill-mapped dispatch

A task that maps to a known dedicated `subagent_type` (`reflection`, `easypost-research`, `epq-report-author`, etc.) needs that `subagent_type` set explicitly on the `Agent` call — a slash command or skill name does not automatically bind to a same-named agent type when dispatched via `Agent` rather than the `Skill` tool, and omitting it silently defaults to `general-purpose`. The failure is invisible: the call still succeeds and returns plausible prose, just without the specialized agent's own baked-in procedure. Check this before dispatch, not after reading a suspiciously generic result. (detail: memory "feedback_reflection_dispatch_missing_subagent_type")

## Delegation vs handoff

CLAUDE.md carries the routing rule. The mechanism: `/handoff` writes a ~15-line pointer brief and lets a fresh sub-agent rebuild context from the session JSONL, so the synthesis cost lands in a disposable context rather than the spent one. Never prose-recap a session into a handoff brief — that spends exactly the tokens the handoff exists to escape. Routing table for delegation targets: `/delegate`.
