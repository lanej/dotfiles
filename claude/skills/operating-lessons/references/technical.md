# Technical Gotchas

Tool, query, document, and design-judgment corrections that fire in specific circumstances.
Read when double-checking a specific procedure, or when the index in SKILL.md names one that matches the task at hand.


### `replace_all` safety
Grep the short pattern alone (not surrounding context) to count all occurrences before committing to `replace_all: true` or a global `sed -i`. (detail: memory "feedback_replace_all_safety")

### Script argument verification
Read a script's argv-handling code before trusting a custom CLI argument was consumed — scripts that ignore argv silently return success.

### Backgrounding a command inside `run_in_background`
Don't wrap a command in your own `nohup cmd & disown; sleep N; cat log` when also passing `run_in_background: true` — that's a second, independent backgrounding layer with a fixed guess at completion time, racing the real job. If the guess is too short, the wrapper's own `sleep N; cat` returns first with only startup output, indistinguishable at a glance from a silent failure (compounded if an unrelated sandbox `nice()` EPERM line is also present). Pass the command directly (optionally through `tail`) and rely on the harness's own blocking-wait (`TaskOutput`) to know when it's actually done. (detail: memory "feedback_background_bash_fixed_sleep_race")

### Interactive prompts inside non-interactive Bash
A `(Y/n)?`-style prompt has no tty to answer it — the command can exit 0 with output that looks like partial success. Check for actual completion (e.g. `gcloud components list`) before reporting success. (detail: memory "feedback_interactive_prompt_bash")

**`--quiet`/`-y` to supply the answer is fine only when the user already explicitly approved that exact action this turn** (e.g. via AskUserQuestion or a direct "yes, cancel it") — the CLI's y/n is then a redundant confirmation of an already-authorized action, not a fresh consent gate, and supplying it programmatically isn't "automating an interactive tool" in the sense CLAUDE.md's editors/git-commit/interactive-rebase rule means. Do not use `--quiet` as a default to route around a confirmation prompt when no such prior approval exists for that specific action — that is the case the general rule is protecting against. (detail: memory "pulse-airflow-migration-incident")

### API result ownership
When an API returns multiple candidate resources (Jira schemes, GCP resources, IAM policies), trace the full association chain from the target to the resource before acting on the first plausible result. (Project-specific example logged in workspace `CLAUDE.local.md`.)

### BigQuery event-level join fanout
Joining an event-level table (trackers, scan events, audit records) to a billing/invoice table inflates aggregates by the average event count per entity. DISTINCT the entity identifier before joining, and sanity-check against the known entity count. Applies to both sub-agent output and queries run directly — the failure mode recurs because column names match and the error is silent. (Project-specific example in workspace `CLAUDE.local.md`.)

### Vertex fast-mode limitation
`/fast` requires direct Anthropic API and is unavailable on Vertex. Use the model picker (`meta+p`) to switch to Opus instead.

## Document editing

### Dependency check
Before finalizing an edit, grep the full document (and known sibling/duplicate docs — a project README next to its CLAUDE.md, other sections of one data dictionary) for every claim that depends on what changed. When dispatching the edit to a sub-agent, the briefing must explicitly include that grep — intro paragraphs and summary sections are the most common thing a "fix Section 3" brief misses. On a v1→v2→v3 same-session edit sequence, re-run the check after the *last* edit, not just the first. This applies even when the *cause* of the change isn't another edit to the doc itself — a rebase pulling in upstream doc changes, or a later commit that changes a real count (tests added/removed) the doc asserts, re-stales a figure just as surely as a manual edit does; re-run the sibling-doc grep after any such commit, not only after commits whose stated purpose is documentation. Recurred 3x in one multi-commit task (2026-08-15, mobile-optimization: post-task doc update, post-rebase, post-fix-wave), each caught only by review. (detail: memory "feedback_iterative_edit_dependency_check"; also "feedback_sibling_document_check"; "feedback_docs_recheck_on_every_number_change")

### Citations in externally-shareable artifacts
Memos, reports, proposals, comms: cite sources (URLs, not internal-only links) for quantitative, comparative, or external-behavior claims that could be challenged outside the company.

## Architecture and design judgment

### Check existing codebase idiom before proposing heavier architecture
Before designing a new layer or pipeline stage (a new transform language, a Python/DuckDB post-processing step, a service boundary) to handle added complexity, check whether the existing codebase's current idiom — the pattern already used by sibling queries/modules for the same class of problem — can be extended to cover it first. A real BigQuery example: asked to bucket customers into 5 sequential magnitude tiers with cross-tier carryover, the first instinct was to propose replacing the project's pure-SQL cohort-definition pattern with a new "broad BigQuery extract + DuckDB/Python wave-assignment" architecture — before confirming the existing all-SQL idiom (chained CTEs, recomputed inline per query) couldn't just be extended with a few more CTEs. The user redirected to "just make a SQL query do it," and it worked once restructured (a BigQuery multi-statement script was still needed for planner-complexity reasons, but that's a much smaller deviation than a new pipeline layer). Propose the extension-of-existing-idiom approach first and name the heavier architecture only as a fallback if the extension provably can't work — don't lead with the rewrite. (detail: memory "feedback_extend_idiom_before_new_layer")

### Architectural layer analysis
Before implementing a new feature, name which layer is optimal (Python / BQ view / middleware / application) based on access patterns, join costs, and freshness requirements — don't default to wherever related code already lives.

### Data-driven design
For thresholds/caps/bucketing boundaries, query the actual distribution (p50/p75/p90/p95/max) first rather than picking a round number.

## Misc

- **Dockerfile COPY check**: adding a new source directory needs a matching `COPY <newdir>/ <newdir>/` line, or it's silently absent from the image until a runtime `FileNotFoundError`.
- **TOML files**: comments on their own line above the config, not inline after the value.
- **`subagent-driven-development` task briefs**: the `task-brief` extractor only pulls text under a Task's own `## Task N` heading — cross-references like "per the config above" are silently dropped. Inline all referenced config/decisions/constraints literally into each Task section. (detail: memory "feedback_task_brief_self_contained")
- **`subagent-driven-development` forbids parallel dispatch**: if a plan will execute under this skill, author it directly in sequential `## Task N` form — don't let a Plan agent (dispatched before the execution mechanism is confirmed) design a "parallel execution" phasing recommendation into the plan document, since it has to be discarded/restructured once the skill's sequential-only constraint surfaces. (detail: memory "feedback_sdd_plan_no_parallel_phasing")
- **`subagent-driven-development` workspace directory keys off the plan-file basename**: `.superpowers/sdd/<plan-basename>/` is meant to isolate one plan's ledger/briefs from another's, but Plan Mode's random plan-file naming is session-scoped, not content-derived — re-entering Plan Mode in the same session and overwriting the same plan file (per the "always start fresh" convention) reuses the old SDD workspace directory too, so a completely unrelated new plan can start execution against a stale `progress.md` describing a different, already-finished plan. Before dispatching SDD execution, check whether `.superpowers/sdd/<basename>/progress.md` already exists and describes a different plan; archive it first if so. (detail: memory "feedback_sdd_workspace_plan_basename_collision")
- **`subagent-driven-development` review-package BASE in this shared monorepo**: never derive BASE via a path-filtered `git log` — `~/workspace`'s concurrent multi-project commit volume means the first path-filtered hit going backward is often far older than the actual parent, pulling the whole intervening history into the diff (confirmed 2x in one session: 88 unrelated commits captured once, a 1MB vs. 415KB diff another time). Record `git rev-parse HEAD` synchronously before the implementer's first commit; if BASE wasn't pre-recorded, recover it via `<first-known-commit>^` or `git merge-base` against the ledger's stated starting commit, never a path-filtered log — and sanity-check diff size/file count before dispatching a reviewer on it. (detail: memory "feedback_sdd_review_package_base_monorepo")
- **Monorepo git pathspec double-prefixing**: from a cwd already inside `~/workspace/projects/<name>/`, a pathspec re-prefixed with `projects/<name>/...` silently returns empty (`git log`/`git diff` exit 0, no error) instead of erroring — use the path relative to cwd instead. Recurred in two different projects 4 days apart. (detail: memory "feedback_monorepo_git_pathspec_double_prefix")
- **Cross-task bug-class propagation**: when an implementer or reviewer reports a bug traceable to a repeatable code pattern (a CSS rule shape, a hook usage, a duplicated helper), grep every other still-untouched target for that same pattern before dispatching the next task — don't rely on each subsequent task to independently rediscover it, and don't wait for the final whole-branch review to be the only backstop. This applies just as much to a solo single-session fix with no sub-agents involved: after fixing a bug traceable to a repeatable pattern (e.g. a specific API misuse), grep the whole repo for that pattern before calling the fix "done" — one bad call site is evidence of a class, not an isolated incident. Confirmed by a same-session recurrence: a stale-metadata bug in a BigQuery MCP client (`job.metadata` never refreshed by `getQueryResults()`) was fixed twice independently before a `/reflection` pass found and fixed a third live occurrence via a repo-wide grep that the original fix skipped. (detail: memory "feedback_proactive_cross_target_bug_class_grep"; bigquery-repo incident in memory "project_stale_job_metadata_bugclass")
- **Markdown line wrapping**: don't hard-wrap at 80 columns — write prose/list items as single long lines, let the viewer wrap.

