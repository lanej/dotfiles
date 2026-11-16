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
