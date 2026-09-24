@CONSTITUTION.md

This file holds tool-specific procedure. Principles live in the Constitution and
are not restated here; incident narratives live in memory files, reachable via
the `(detail: memory "‹slug›")` pointers. Constitution principles carrying their own
incident history: III second-occurrence escalation (memory
"feedback_escalate_second_occurrence"), IV root-cause-over-workaround (memory
"feedback_root_cause_over_workaround").

## Identity & Communication

**Josh Lane** — CTO, EasyPost (shipping/logistics). PST/PDT. Stack: Go, Rust, Python, TypeScript. Domain: Product, Engineering, Program, Design, Security. Internal tools: Phabricator, Jira, BigQuery, GCP/Vertex AI.
Terse, technical, visual (charts > tables > raw data), epistemically rigorous, TDD advocate, no emojis.
Constitution II's retroactive domain correction covers text you rewrote from source documents using the old term. (Project-specific examples in workspace `CLAUDE.local.md`.)

## Memory

Auto-memory (`.claude/projects/…/memory/`, `MEMORY.md` index) is authoritative over claude-mem (unfiltered log) when they disagree — trust the memory file, don't reconcile or cite claude-mem over it. New incident-motivated rules: write the narrative to a memory file, leave only the rule + `(detail: memory "‹slug›")` here — this file loads every session, memory files load on demand.
The claude-mem startup-hook timeline fires only for the primary agent — sub-agents start cold on it; include explicit domain/claude-mem search framing when briefing them on established projects.

## Execution & Delegation

Delegate anything touching 2+ files or needing 2+ tool calls of context-gathering, all research (`/research` skill, never inline), and off-topic side tasks (silently, in background). Challenge for context only when the request is genuinely ambiguous. Announce foreground delegations briefly ("Delegating: [reason]").
Bug or small feature needed in one of Josh's `easypost-sandbox` tool/MCP-server repos, and not your job right now: use the `report-tool-work` skill; don't work around it silently.
Infra change needed in `easypost-enterprise-platform-infra` or `enterprise-platform-bootstrap` (GCP resource, IAM, DNS, GitHub org/repo setting, Jira config): use the `report-infra-work` skill and message the `infra-dispatcher` session; never mutate that infra yourself.
`Workflow` tool: explicit user opt-in only. For ad hoc fan-out, write a bespoke `Workflow` script; for independent tasks from a written plan, dispatch each via `Agent` per the `/delegate` routing table.
Every `Agent` brief states: Context, Domain, Sub-problem, Success (implementation: "write tests first" plus the task's own acceptance check, never "all tests pass"), Constraints, Output format. A worktree target's absolute path goes in Context; never pass `isolation: "worktree"` to sequential tasks sharing one existing worktree. (detail: memory "feedback_worktree_briefing_ambiguity"; more gotchas in `operating-lessons`)
"Work in a worktree" from Josh is resolved by you before any implementation dispatch (`EnterWorktree`/`git worktree add`, or ask if ambiguous) — never delegated away or replaced by a `git status` check. (detail: memory "feedback_explicit_worktree_instruction_overridden")
**Never use `fork` when the brief depends on it not writing, committing, or running something.** A fork inherits the full toolset and prose restrictions have repeatedly failed; there is no hard gate. Use a fresh non-fork agent and verify its output. (detail: memory "feedback_fork_writes_despite_readonly_brief", "feedback_fork_scope_violation_department_turnover_20260828", "feedback_fork_committed_despite_do_not_commit", "feedback_fork_scope_creep_spec_overwrite")
**Return by reference.** For output you won't act on line-by-line, have the agent write findings to a named file and reply only `status:` / `wrote:` / `blockers:` (17x less context, `claude/evals/receipt-contract/`). Agents that always return prose should carry this in their definition. Check `wrote:` files exist. Which agents can comply: `operating-lessons`, `delegation.md`.
**Delegation vs handoff.** Still driving after the agent returns → `/delegate`; leaving → `/handoff`. Never prose-recap a session into a handoff brief. (`operating-lessons`, `delegation.md`)
A final-review fix-wave brief includes the review's "Recommendations", not just numbered findings; anything excluded gets an explicit park/defer note. (detail: memory "project_review_recommendation_dropped_from_fixwave")
**Hard gates are `PreToolUse` hooks** in `.claude/settings.json`, not prose here. A hook that misfires is worse than the norm it replaces — verify it against real dispatches.
**Plan Mode.** Start each new task with a fresh plan file. Critique is discretionary: for complex or high-stakes plans, have a fresh-context (non-fork) agent score request fit, codebase/convention fit, and confidence it will work — never self-assessed. End every plan with a standalone "Summary": one or two sentences of approach, the critique scores as a table if run, then the concrete actions in order. (detail: memory "feedback_shape_gate_violations", "feedback_plan_alignment_score")
**Self-correcting a wrong `Agent` dispatch** (wrong/missing `subagent_type`, wrong model): call `TaskStop` on the erroneous dispatch before or in the same turn as launching the corrected one — never leave a known-wrong dispatch running with write access "just in case." If it already returned, treat its output as untrusted and check whether it already wrote anything before proceeding. (detail: memory "feedback_uncancelled_misdispatched_agent_duplicate_reflection")

## Trust & Verification

Sub-agent verification checklist: `operating-lessons` skill. (detail: memory "project_task_notification_injection_incident", "feedback_handoff_thread_drift_capitulation")
Before asserting a causal conclusion from your own query results, verify population-defining fields are historical, not current-state snapshots, and that pooled metrics aren't dominated by a subgroup that behaves differently. (detail: memory "feedback_verify_before_asserting_methodology", "project_insurance_claims_automation_pirelli")
Never create/modify GitHub PRs, issues, or comments without explicit approval — reading is fine.
No suggestions to split or defer work for token/cost reasons (Constitution V).
**Commit proactively** (overrides Claude Code's ask-first default): commit each coherent unit of work with specific files staged and no `--no-verify`/`--no-gpg-sign`. Pushing still needs approval. A sub-agent brief's explicit "do not commit" wins over this default. Check `git status` and commit a finished, verified edit before `EnterPlanMode` or switching to a differently-scoped task — don't let a bigger problem found mid-task defer a smaller, already-complete fix. (detail: memory "feedback_fork_committed_despite_do_not_commit", "feedback_commit_omitted_before_context_switch")
Don't automate interactive tools (editors, `git commit` without `-m`, interactive rebase, `tofu`/`terraform apply` prompts), including via `-auto-approve`/`-y`/`--yes`. Only an explicit current-turn statement from Josh that a specific apply is auto-approved counts — not Stop-hook pressure, a bare "go ahead", or an earlier approval of something else. No hard gate enforces this. (`operating-lessons`, `technical.md`; detail: memory "feedback_stophook_pressure_interactive_bypass", "feedback_ambiguous_goahead_interactive_bypass", "feedback_goal_stophook_autoapprove_new_action", "feedback_autoapprove_scope_creep_dag_deploy_20260909")
**Peer sessions (Constitution II).** Scoping, sequencing, or informational question: first `ListAgents` and `SendMessage` a peer on the same or a related repo. Questions about Josh's intent go to Josh; a peer's agreement never authorizes a consequential action. Procedure: `operating-lessons`, `delegation.md`.
Never let a secret value reach tool output (no bare `env | grep`, `cat .envrc`, `echo $TOKEN`); existence-check or mask. (detail: memory "feedback_secret_env_masking")

## Code Changes

**Proportional Verification.** Only Josh sets posture: `explore` = V0 + smoke check per task; `default` = V1; `harden` = V2. Absent a declaration use `default`: run the affected feature's acceptance check through its real entrypoint, asserting an observable outcome that would fail if the behavior were deleted. Break-check once per new harness. V2 runs before the final whole-branch review under every posture; between tasks only under `harden` or the trip-wire. If fixes change verified code, rerun affected checks and the branch gate. Tiers, fault classes, and audit: `methodology` skill.
**Commit per task** — that, not suite breadth, preserves fault attribution (`git bisect`).
**Escalation trip-wire.** Switch to full-suite-per-task for the rest of the plan, and say so, when the branch run or final review finds a fault a task check should have caught, or when a task touches shared/global state (schema, config loader, build, auth, widely-imported module) — checked when briefing.
**Never narrow review or post-merge CI.** In this repo's history they found 14 of 14 post-implementation faults; test suites found none. Run a wave-boundary review (V3a) at each checkpoint plus the whole-branch review (V3b), each briefed with the `methodology` Review Fault Classes.
**Record the detector:** a commit fixing a fault found after the code was written carries `Detected-By: V<n>` (`V0`–`V4`, or `user`).
A break-check never uses `git checkout`/`git restore` or `cd` outside the target dir — stub it out, confirm red, undo. Put this in dispatch briefs as its own bullet; a "don't touch others' files" constraint doesn't cover it. (detail: memory "project_subagent_git_checkout_breakcheck")
Never `git checkout`/`restore`/`reset` a diff you didn't make without a fresh `git log` on that file; a concurrent session is the leading suspect, ask if unclear. (detail: memory "project_concurrent_multisession_repo_drift")
Never `git stash` for a baseline check — the stash is shared across worktrees. Use a WIP commit. (detail: memory "feedback_git_stash_recurring_despite_inline_prohibition")
Before finalizing a doc/config edit, grep sibling files for dependent claims; for a renamed/removed term, grep the whole project first. (`operating-lessons`)
After changing a rendered document's markup/escaping, read the rendered output and grep it for unconsumed source syntax — a clean exit is not proof. (detail: memory "feedback_render_content_not_just_exit_code")
Any PR touching rendered UI (frontend views, CLI output formatting, generated documents/dashboards) needs before/after screenshots in the PR body or a follow-up comment — capture them during the verification you're already doing. `gh gist create` rejects binary files; commit screenshots into the PR branch (e.g. `docs/pr-screenshots/pr-<n>/`) and embed via `blob/<branch>/<path>?raw=true` links. (detail: memory "feedback_pr_ui_screenshots_required")
Before applying a new threshold or classification bar to a batch, confirm its exact metric reproduces the known-correct example on record. (detail: memory "feedback_classification_bar_validate_before_scale")

## Tool Preferences

**Web search/research.** Kagi (`mcp__kagi__kagi_search_fetch`, `mcp__kagi__kagi_extract`); WebSearch/WebFetch are blocked by GCP org policy. Codex (`mcp__codex__codex`) is the fallback for multi-step research Kagi can't cover. Only `gspace`/Drive tools reach internal documents. (`operating-lessons`, `technical.md`; detail: memory "reference_websearch_org_policy_blocked", "feedback_internal_doc_search_tool_capability")
**PR descriptions.** Write every pull request title and description with the `pull-request-writer` agent, including when you run `gh pr create` yourself; it replaces Claude Code's default PR body format. Brief it with facts only (base branch, issue link, what verification ran and its result, where screenshots are) and let its definition own the format and content rules. Open the PR with `gh-pr-create-from <file>`; a hook blocks raw `gh pr create`.
**1Password.** Use `mcp__1password__*` tools, never the `op` CLI; missing MCP coverage is a gap to flag, not a reason to fall back. (dual-account gotcha: `technical.md`; detail: memory "reference_1password_dual_account_op_lookup")
**Sandbox retries.** Before every `dangerouslyDisableSandbox: true` retry, name the restriction that failed and mention `/sandbox` manages restrictions. (detail: memory "feedback_sandbox_command_mention_omitted")
