---
name: operating-lessons
description: "Situational verification and delegation-discipline rules covering sub-agent output trust (numeric claims, data availability, infra completion, hallucination), worktree and briefing gotchas, and misc technical corrections (BigQuery join fanout, replace_all safety, interactive Bash prompts, git worktree cleanup ordering). Use when reviewing sub-agent output before surfacing it, briefing an Agent call targeting a worktree, or double-checking a specific verification or safety procedure referenced from CLAUDE.md. Don't use for general TDD, git commit conventions, or domain-specific language gotchas already covered by the git, javascript, python, or bigquery skills."
---

# Operating Lessons

Situational rules pulled out of CLAUDE.md to keep it lean — each fires in a specific circumstance rather than every session. CLAUDE.md carries the general principle for each family below as an always-loaded default; this file is the detail/backstop layer, not the primary enforcement. Every rule is backed by a memory file with the full incident unless noted otherwise.

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

### Git push/merge
Verify with `git log origin/main -1` or `git remote show origin` after any push/merge — don't rely on the exit code alone. (detail: memory "feedback_git_push_verification")

## Worktree and briefing gotchas

### Structured briefings targeting a worktree
State the worktree's full absolute path explicitly in the briefing's Context, distinct from the main repo's path. Prefer `Agent(..., isolation: "worktree")` — it pins cwd at the tool level and eliminates the ambiguity structurally. `subagent-driven-development`'s sequential tasks sharing one pre-existing worktree can't use per-task isolation (it would create a different worktree each time) — for that flow, require the implementer's first tool call to confirm `pwd`/`git branch --show-current` resolves inside the worktree, and independently re-verify the reported commit SHA against `git log` before trusting a DONE report. (detail: memory "feedback_worktree_briefing_ambiguity")

### Sub-agent scope boundary
Don't kill a process you don't own, or mutate production data/schema when only asked to dry-run/verify. Port/process-cleanup briefings need ownership confirmed before killing anything, and restart+disclosure if something outside scope was killed; proactively check for orphaned killed processes yourself afterward rather than trusting the "done" report. For live cloud/DB credentials, state the negative explicitly ("dry-run only; do not create/modify/delete anything") — a brief that only states the affirmative command doesn't thereby forbid everything else those credentials permit. (detail: memory "project_subagent_port_kill_incident"; also "feedback_subagent_dry_run_scope_boundary")

### No concurrent duplicate background commands
Check `TaskList`/`TaskStop` for an equivalent long-running command before spawning another.

### Concurrent multi-session repo drift
Unexplained repo/file state with no task-notification is often a concurrent human session on this machine, not noise or injection. Verify via `git log`/`git status`/`git diff` and a claude-mem search before assuming or overwriting. (detail: memory "project_concurrent_multisession_repo_drift")

### `gh pr checkout` is not worktree-safe
It operates against the main git directory regardless of CWD, switching the main working directory's branch. For a sub-agent working a PR branch inside a worktree, use `git fetch origin <branch> && git checkout -b fix/<name> origin/<branch>` instead.

### npm/yarn workspaces in a fresh worktree
A freshly created worktree has no `node_modules` until `npm install` runs there — until then, workspace-package resolution silently walks up to the *parent checkout's* `node_modules` instead of erroring, so a worktree's edits to a shared package can appear to have no effect. Run `npm install` at the worktree root immediately after creating it, before any dev server or test command. (detail: memory "feedback_worktree_npm_workspaces_stale_resolution")

### Worktree + pytest
`cd` into the worktree before invoking `pytest` — never run it from the main repo root with paths pointing into the worktree. The main repo's `pyproject.toml` drives discovery/imports from there, not the worktree's edited files. Correct: `cd <worktree-path> && uv run pytest tests/...`. (detail: memory "feedback_worktree_pytest_verification")

### `core.hooksPath` collision across worktrees
It's a single value in the shared `.git/config`, not per-worktree — a sibling worktree running `husky init` can silently overwrite it repo-wide, defeating the pre-commit hook everywhere else with no error at commit time. Fix per worktree needing isolation: `git config extensions.worktreeConfig true && git config --worktree core.hooksPath <relative-path>`. (detail: memory "project_hookspath_worktree_collision"; mechanism also documented in `git` skill)

### `git worktree remove` ordering
Never run it via Bash before `ExitWorktree` — it deletes the directory the session's CWD points at, and Node then fails to spawn any subsequent hook with a misleading `ENOENT: posix_spawn '/bin/sh'` error. Use `ExitWorktree` with `action: "remove"` — it handles the git-level removal itself.

## Verification-before-reporting family

Each of these is an instance of "run safe verification before you surface a result" for a specific recurring scenario:

- **Aggregate counts**: verify the motivating case is actually in the population before surfacing N matches/rows. (detail: memory "feedback_aggregate_spotcheck")
- **Refactor output**: verify a dynamic replacement source produces the same keys/values as the hardcoded value it replaces. (detail: memory "feedback_refactor_output_verification")
- **Multi-file refactors (5+ files)**: run a syntax/import check on all modified files plus one end-to-end smoke test before declaring done. (detail: memory "feedback_multifile_refactor_verification")
- **Architectural pivots mid-session**: independently re-run whatever check confirmed the pre-pivot feature worked — a sub-agent's "expected blocker" framing isn't a substitute. (detail: memory "feedback_architectural_pivot_verification")
- **Full-stack features**: passing frontend and backend tests separately doesn't confirm they're wired together — verify the real network call fires end-to-end. (detail: memory "project_fraud_detection_mock_data_regression")
- **Single-example metrics**: one anecdote doesn't confirm real signal vs. artifact — check the full value distribution (`COUNT(*) GROUP BY`, percentiles). (detail: memory "feedback_single_example_distribution_check")
- **"What's taking so long?"**: check actual status/logs immediately — a recap of known steps isn't an answer. (detail: memory "feedback_taking_so_long_investigate")
- **Pricing/versioned APIs**: name the exact version/generation when quoting a price — tiers get revised between generations and commonly-cited figures are often stale. (detail: memory "feedback_pricing_generation_verification")

## Technical gotchas

### `replace_all` safety
Grep the short pattern alone (not surrounding context) to count all occurrences before committing to `replace_all: true` or a global `sed -i`. (detail: memory "feedback_replace_all_safety")

### Script argument verification
Read a script's argv-handling code before trusting a custom CLI argument was consumed — scripts that ignore argv silently return success.

### Interactive prompts inside non-interactive Bash
A `(Y/n)?`-style prompt has no tty to answer it — the command can exit 0 with output that looks like partial success. Check for actual completion (e.g. `gcloud components list`) before reporting success. (detail: memory "feedback_interactive_prompt_bash")

### API result ownership
When an API returns multiple candidate resources (Jira schemes, GCP resources, IAM policies), trace the full association chain from the target to the resource before acting on the first plausible result. (Project-specific example logged in workspace `CLAUDE.local.md`.)

### BigQuery event-level join fanout
Joining an event-level table (trackers, scan events, audit records) to a billing/invoice table inflates aggregates by the average event count per entity. DISTINCT the entity identifier before joining, and sanity-check against the known entity count. Applies to both sub-agent output and queries run directly — the failure mode recurs because column names match and the error is silent. (Project-specific example in workspace `CLAUDE.local.md`.)

### Vertex fast-mode limitation
`/fast` requires direct Anthropic API and is unavailable on Vertex. Use the model picker (`meta+p`) to switch to Opus instead.

## Document editing

### Dependency check
Before finalizing an edit, grep the full document (and known sibling/duplicate docs — a project README next to its CLAUDE.md, other sections of one data dictionary) for every claim that depends on what changed. When dispatching the edit to a sub-agent, the briefing must explicitly include that grep — intro paragraphs and summary sections are the most common thing a "fix Section 3" brief misses. On a v1→v2→v3 same-session edit sequence, re-run the check after the *last* edit, not just the first. (detail: memory "feedback_iterative_edit_dependency_check"; also "feedback_sibling_document_check")

### Citations in externally-shareable artifacts
Memos, reports, proposals, comms: cite sources (URLs, not internal-only links) for quantitative, comparative, or external-behavior claims that could be challenged outside the company.

## Architecture and design judgment

### Architectural layer analysis
Before implementing a new feature, name which layer is optimal (Python / BQ view / middleware / application) based on access patterns, join costs, and freshness requirements — don't default to wherever related code already lives.

### Data-driven design
For thresholds/caps/bucketing boundaries, query the actual distribution (p50/p75/p90/p95/max) first rather than picking a round number.

## Misc

- **Dockerfile COPY check**: adding a new source directory needs a matching `COPY <newdir>/ <newdir>/` line, or it's silently absent from the image until a runtime `FileNotFoundError`.
- **TOML files**: comments on their own line above the config, not inline after the value.
- **`subagent-driven-development` task briefs**: the `task-brief` extractor only pulls text under a Task's own `## Task N` heading — cross-references like "per the config above" are silently dropped. Inline all referenced config/decisions/constraints literally into each Task section. (detail: memory "feedback_task_brief_self_contained")
- **Markdown line wrapping**: don't hard-wrap at 80 columns — write prose/list items as single long lines, let the viewer wrap.

## Error Handling

- If a cited memory file no longer exists, treat the rule as still in force and note the missing citation — don't drop the rule on that basis alone.
- If a rule here conflicts with something newer in CLAUDE.md, CLAUDE.md wins — this file is the detail layer, not the source of truth.
- If unsure whether a specific check applies to the current task, run it — the cost of an unnecessary verification is far lower than a fabricated or stale claim reaching the user.
