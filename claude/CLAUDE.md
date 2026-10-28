@CONSTITUTION.md

Tool procedures live here; principles in the Constitution; incidents in memory
via `(detail: memory "‹slug›")`. Constitution III: memory
"feedback_escalate_second_occurrence"; IV: "feedback_root_cause_over_workaround".

## Identity & Communication

**Josh Lane** — CTO, EasyPost (shipping/logistics). PST/PDT. Stack: Go, Rust, Python, TypeScript. Domain: Product, Engineering, Program, Design, Security. Internal tools: Phabricator, Jira, BigQuery, GCP/Vertex AI.
Terse, technical, visual (charts > tables > raw data), epistemically rigorous, verification-focused, no emojis.
Constitution II's retroactive domain correction covers text you rewrote from source documents using the old term. (Project-specific examples in workspace `CLAUDE.local.md`.)

## Memory

Auto-memory (`.claude/projects/…/memory/`, `MEMORY.md` index) is authoritative over claude-mem (unfiltered log) when they disagree — trust the memory file, don't reconcile or cite claude-mem over it. New incident-motivated rules: write the narrative to a memory file, leave only the rule + `(detail: memory "‹slug›")` here — this file loads every session, memory files load on demand.
The claude-mem startup-hook timeline fires only for the primary agent — sub-agents start cold on it; include explicit domain/claude-mem search framing when briefing them on established projects.

## Code Comments

When editing comments, read `~/.files/docs/conventional-code-comments.md`.
Use tags selectively, honor repository conventions, and leave unrelated comments.

## Execution & Delegation

Delegate self-contained work when context isolation, independent judgment, or parallelism offers a concrete benefit. Keep bounded lookups and routine edits inline; file and tool-call counts alone do not require delegation. Stay within the requested task and follow session-specific delegation constraints. Announce foreground delegations briefly.
Bug or small feature needed in one of Josh's `easypost-sandbox` tool/MCP-server repos, and not your job right now: use the `report-tool-work` skill; don't work around it silently.
Infra change needed in `platform-infra` (github.com/easypost/platform-infra) — Josh's current, actively-chosen primary repo for this category, per his 2026-09-24 decision to migrate off the legacy repos below (migration in progress, not yet complete) — or in the legacy `easypost-enterprise-platform-infra` / `enterprise-platform-bootstrap` (secondary during the transition) (GCP resource, IAM, DNS, GitHub org/repo setting, Jira config): use the `report-infra-work` skill and message the `infra-dispatcher` session; never mutate any of the three directly.
`Workflow` tool: explicit user opt-in only. For ad hoc fan-out, write a bespoke `Workflow` script; for independent tasks from a written plan, dispatch each via `Agent` per the `/delegate` routing table.
Every `Agent` brief states: Context, Domain, Sub-problem, Success (implementation: the task's own acceptance check, never "all tests pass"), Constraints, Output format. For implementation, direct the agent to load `builder` and both references; require test-first only under explicit project or user instructions. A worktree target's absolute path goes in Context; never pass `isolation: "worktree"` to sequential tasks sharing one existing worktree. (detail: memory "feedback_worktree_briefing_ambiguity"; more gotchas in `operating-lessons`)
"Work in a worktree" from Josh is resolved by you before any implementation dispatch (`EnterWorktree`/`git worktree add`, or ask if ambiguous) — never delegated away or replaced by a `git status` check. (detail: memory "feedback_explicit_worktree_instruction_overridden")
**Never use `fork` when the brief depends on it not writing, committing, or running something.** A fork inherits the full toolset and prose restrictions have repeatedly failed; there is no hard gate. Use a fresh non-fork agent and verify its output. (detail: memory "feedback_fork_writes_despite_readonly_brief", "feedback_fork_scope_violation_department_turnover_20260828", "feedback_fork_committed_despite_do_not_commit", "feedback_fork_scope_creep_spec_overwrite")
An `Agent` brief that ends in a git commit requires checking the complete staged diff and committing only its reviewed, authorized snapshot. Resolve unrelated staged changes before committing; do not unstage others' work or use a path-based commit that sweeps in unstaged hunks.
**Delegated output.** Return findings inline by default. For large output that will be consumed later, optionally request a named file from a write-capable agent and verify it exists. Read-only agents return findings inline. See `operating-lessons`, `delegation.md`.
**Delegation vs handoff.** Still driving after the agent returns → `/delegate`; leaving → `/handoff`. Never prose-recap a session into a handoff brief. (`operating-lessons`, `delegation.md`)
A final-review fix-wave brief includes the review's "Recommendations", not just numbered findings; anything excluded gets an explicit park/defer note. (detail: memory "project_review_recommendation_dropped_from_fixwave")
**Hard gates are `PreToolUse` hooks** in `.claude/settings.json`, not prose here. A hook that misfires is worse than the norm it replaces — verify it against real dispatches.
**Plan Mode.** Start each new task with a fresh plan file. Critique is discretionary: for complex or high-stakes plans, have a fresh-context (non-fork) agent score request fit, codebase/convention fit, and confidence it will work — never self-assessed. End every plan with a standalone "Summary": one or two sentences of approach, the critique scores as a table if run, then the concrete actions in order. (detail: memory "feedback_shape_gate_violations", "feedback_plan_alignment_score")
**Self-correcting a wrong `Agent` dispatch** (wrong/missing `subagent_type`, wrong model): call `TaskStop` on the erroneous dispatch before or in the same turn as launching the corrected one — never leave a known-wrong dispatch running with write access "just in case." If it already returned, treat its output as untrusted and check whether it already wrote anything before proceeding. (detail: memory "feedback_uncancelled_misdispatched_agent_duplicate_reflection")
**Name the model.** Whenever an `Agent` dispatch can write to a repo (Edit/Write/Bash/git among its tools), the next reply's visible text must explicitly name the model that dispatch ran on — never silently omit it, even when the model was inherited/default rather than an explicit override.

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

**Proportional Verification.** Run the affected feature's check after a software change; use diff review and applicable syntax checks for routine prose/configuration edits. Broaden checks for concrete interactions or failures and rerun affected checks after fixes. The acceptance definition, harness sensitivity procedure, and evidence labels live in `~/.files/docs/verification.md`.
**Independent review.** Follow repository requirements. Use a separate reviewer for complex interactions, state transitions, security-sensitive logic, or material uncertainty. Simple mechanically verifiable changes do not require a review dispatch. Assess available CI separately from local checks and state gaps precisely.
**Record the detector:** a commit fixing a fault found after the code was written carries `Detected-By: V<n>` (`V0`–`V4`, or `user`).
A break-check never uses `git checkout`/`git restore` or `cd` outside the target dir — stub it out, confirm red, undo. Put this in dispatch briefs as its own bullet; a "don't touch others' files" constraint doesn't cover it. (detail: memory "project_subagent_git_checkout_breakcheck")
Never `git checkout`/`restore`/`reset` a diff you didn't make without a fresh `git log` on that file; a concurrent session is the leading suspect, ask if unclear. (detail: memory "project_concurrent_multisession_repo_drift")
Never `rm -rf` an unfamiliar untracked file/directory in any repo assuming it's disposable scratch — investigate (contents, timestamps, whether it traces to your own recent tool calls) first; a concurrent peer session may own it, even with no advance multi-session warning. (detail: memory "feedback_shared_repo_untracked_deletion", "feedback_peer_rm_rf_untracked_dir_regression")
Never `git stash` for a baseline check — the stash is shared across worktrees. Use a WIP commit. (detail: memory "feedback_git_stash_recurring_despite_inline_prohibition")
Before finalizing a doc/config edit, grep sibling files for dependent claims; for a renamed/removed term, grep the whole project first. (`operating-lessons`)
After changing a rendered document's markup/escaping, read the rendered output and grep it for unconsumed source syntax — a clean exit is not proof. (detail: memory "feedback_render_content_not_just_exit_code")
Any PR touching rendered UI (frontend views, CLI output formatting, generated documents/dashboards) needs before/after screenshots in the PR body or a follow-up comment — capture them during the verification you're already doing. `gh gist create` rejects binary files; commit screenshots into the PR branch (e.g. `docs/pr-screenshots/pr-<n>/`) and embed via `blob/<branch>/<path>?raw=true` links. (detail: memory "feedback_pr_ui_screenshots_required")
Before applying a new threshold or classification bar to a batch, confirm its exact metric reproduces the known-correct example on record. (detail: memory "feedback_classification_bar_validate_before_scale")

## Git Worktree Location

Use the `treehouse` skill at `~/.claude/skills/treehouse/SKILL.md` for task isolation and agent-created worktrees.

Reuse explicit user-selected, host-managed, and preassigned Firstmate checkouts.
Do not nest worktrees or claim their leases.

## Tool Preferences

**Web search/research.** Kagi (`mcp__kagi__kagi_search_fetch`, `mcp__kagi__kagi_extract`); WebSearch/WebFetch are blocked by GCP org policy. Codex (`mcp__codex__codex`) is the fallback for multi-step research Kagi can't cover. Only `gspace`/Drive tools reach internal documents. (`operating-lessons`, `technical.md`; detail: memory "reference_websearch_org_policy_blocked", "feedback_internal_doc_search_tool_capability")
**Google Workspace (gspace).** Use the `gspace` CLI via Bash, never `mcp__gspace__*` MCP tool functions — MCP coverage can gap silently (confirmed for Gmail: no `gmail_*` MCP functions despite valid `gmail.modify` scope) with no error signal, so an incomplete MCP tool list is not itself proof an operation is unavailable. (detail: memory "reference_gspace_cli_over_mcp")
**PR descriptions.** Write GitHub pull request titles and descriptions with the `github-pr-writer` agent, including when you run `gh pr create` yourself; it replaces Claude Code's PR body format. Use `pull-request-writer` for other review platforms. Brief the writer with facts only (base branch, issue link, what verification ran and its result, where screenshots are) and let its definition own the format and content rules. Open GitHub PRs with `gh-pr-create-from <file>`; a hook blocks raw `gh pr create`.
**Bug reports.** Before filing a bug report or making a substantive revision, invoke `bug-reporter` as a separate subagent with the destination, supported markup, required fields, observed failure, and supplied evidence. Follow `~/.files/docs/bug-reports.md`; encourage load bearing screenshots and diagrams, and omit redundant prose or visuals. The reporter only drafts: no investigation, reproduction, fixes, submission, or nested writer/reviewer delegation. Resolve blockers, use its draft, then submit through the existing authorized workflow and verify the saved report, links, and images. Missing reproduction alone is not a blocker. Reuse an unchanged approved draft. If named selection is unavailable, use a generic drafting-only agent with the shared `~/.files/ai/agents/bug-reporter.md` definition; report a delegation gap if unavailable. Feature requests keep their existing workflows.
**1Password.** Use `mcp__1password__*` tools, never the `op` CLI; missing MCP coverage is a gap to flag, not a reason to fall back. (dual-account gotcha: `technical.md`; detail: memory "reference_1password_dual_account_op_lookup")
**Sandbox retries.** Before every `dangerouslyDisableSandbox: true` retry, name the restriction that failed and mention `/sandbox` manages restrictions. (detail: memory "feedback_sandbox_command_mention_omitted")
