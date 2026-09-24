# Technical Gotchas

Tool, query, document, and design-judgment corrections that fire in specific circumstances.
Read when double-checking a specific procedure, or when the index in SKILL.md names one that matches the task at hand.


## Tool and Bash gotchas

### `replace_all` safety
Grep the short pattern alone (not surrounding context) to count all occurrences before committing to `replace_all: true` or a global `sed -i`. (detail: memory "feedback_replace_all_safety")

### Script argument verification
Read a script's argv-handling code before trusting a custom CLI argument was consumed — scripts that ignore argv silently return success.

### Backgrounding a command inside `run_in_background`
Don't wrap a command in your own `nohup cmd & disown; sleep N; cat log` when also passing `run_in_background: true` — that's a second, independent backgrounding layer with a fixed guess at completion time, racing the real job. If the guess is too short, the wrapper's own `sleep N; cat` returns first with only startup output, indistinguishable at a glance from a silent failure (compounded if an unrelated sandbox `nice()` EPERM line is also present). Pass the command directly (optionally through `tail`) and rely on the harness's own blocking-wait (`TaskOutput`) to know when it's actually done. (detail: memory "feedback_background_bash_fixed_sleep_race")

### Interactive prompts inside non-interactive Bash
A `(Y/n)?`-style prompt has no tty to answer it — the command can exit 0 with output that looks like partial success. Check for actual completion (e.g. `gcloud components list`) before reporting success. (detail: memory "feedback_interactive_prompt_bash")

### Playwright reusing a stale cached JS bundle across rebuilds
A live-verification loop that rebuilds a frontend (`pnpm run build`), restarts its backend server, then re-`browser_navigate`s the *same* Playwright page to the *same* URL can silently serve the browser's cached previous-build bundle instead of the fresh one — a plain `page.goto` doesn't guarantee a cache-busting reload, and content-hashed filenames (`index-<hash>.js`) only help if the browser actually re-requests `index.html` to learn the new hash. Confirmed 2026-09-22 (`usps-local-route-detection`): after a real feature landed and was independently verified (tests/lint/build/tarball all green), a live click-through showed no trace of the new UI — nearly reported as a bug — until `document.querySelectorAll('script[src]')` showed the loaded script hash didn't match the just-built `dist/assets/` filename. Fix: after any rebuild, verify the loaded bundle's actual script-tag URL against the fresh build output before trusting what renders; if stale, navigate to a cache-busted URL (`?cachebust=<timestamp>`) rather than assuming the feature is broken. (detail: memory "feedback_playwright_stale_bundle_cache")

**`--quiet`/`-y` to supply the answer is fine only when the user already explicitly approved that exact action this turn** (e.g. via AskUserQuestion or a direct "yes, cancel it") — the CLI's y/n is then a redundant confirmation of an already-authorized action, not a fresh consent gate, and supplying it programmatically isn't "automating an interactive tool" in the sense CLAUDE.md's editors/git-commit/interactive-rebase rule means. Do not use `--quiet` as a default to route around a confirmation prompt when no such prior approval exists for that specific action — that is the case the general rule is protecting against. (detail: memory "pulse-airflow-migration-incident")

### Broad process kill hits peer sessions
`pkill -f <name>`/`killall <name>` for your own dev-server cleanup matches on a
substring across the whole process table — it can silently kill an unrelated peer
session's identically-named process (e.g. another session's `vite` dev server), with
no error to either side. Recurred across 2+ projects. Find the exact PID (`lsof -ti
:<port>`, or the PID you started) and kill that, never a name/pattern match — including
when tearing down a process this same session started. (detail: memory
"feedback_pkill_collateral_damage_peer_session")

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

### Classification bar/threshold validation before scaling
Before applying a newly-defined classification bar/threshold (a size cutoff, a quality gate, a "workable unit" definition) across a batch of new candidates, run its exact metric implementation against the one already-known-correct example first and confirm it reproduces the expected number/classification — a provisional, single-outlier-informed threshold is not verification. Concrete instance: `usps-local-route-detection`'s "workable-unit bar" (size>=5 nodes OR span>=2-3h) was applied to 48 new DAG components across 10 newly-scaled ZIP5 targets without checking that its own span metric reproduced the project's one known-good benchmark (77433's real, independently-established 7.4-7.7h span) — the metric was silently computing a different, ~20%-smaller quantity (a cross-year per-address median instead of a real single observed day), and the too-permissive OR condition let bare size substitute for span. Only 1 of the 48 turned out to be a real route once both were fixed. This is Constitution IV ("don't trust a green result you haven't tried to break") applied to a definitional bar rather than to code correctness. (detail: memory "feedback_classification_bar_validate_before_scale")

## Misc

- **Dockerfile COPY check**: adding a new source directory needs a matching `COPY <newdir>/ <newdir>/` line, or it's silently absent from the image until a runtime `FileNotFoundError`.
- **TOML files**: comments on their own line above the config, not inline after the value.
- **Monorepo git pathspec double-prefixing**: from a cwd already inside `~/workspace/projects/<name>/`, a pathspec re-prefixed with `projects/<name>/...` silently returns empty (`git log`/`git diff` exit 0, no error) instead of erroring — use the path relative to cwd instead. Recurred in two different projects 4 days apart. (detail: memory "feedback_monorepo_git_pathspec_double_prefix")
- **Cross-task bug-class propagation**: when an implementer or reviewer reports a bug traceable to a repeatable code pattern (a CSS rule shape, a hook usage, a duplicated helper), grep every other still-untouched target for that same pattern before dispatching the next task — don't rely on each subsequent task to independently rediscover it, and don't wait for the final whole-branch review to be the only backstop. This applies just as much to a solo single-session fix with no sub-agents involved: after fixing a bug traceable to a repeatable pattern (e.g. a specific API misuse), grep the whole repo for that pattern before calling the fix "done" — one bad call site is evidence of a class, not an isolated incident. Confirmed by a same-session recurrence: a stale-metadata bug in a BigQuery MCP client (`job.metadata` never refreshed by `getQueryResults()`) was fixed twice independently before a `/reflection` pass found and fixed a third live occurrence via a repo-wide grep that the original fix skipped. (detail: memory "feedback_proactive_cross_target_bug_class_grep"; bigquery-repo incident in memory "project_stale_job_metadata_bugclass")
- **Markdown line wrapping**: don't hard-wrap at 80 columns — write prose/list items as single long lines, let the viewer wrap.
- **Implementer briefs need explicit git-staging discipline**: an implementer told only to "commit your work" will reach for a broad add, and a broad add sweeps in whatever else is untracked in the working tree (a prior session's scratch files, another task's in-flight output). Confirmed in `usps-local-route-detection`: an implementer swept 753 lines of unrelated `.socrates/` session files into its `span.py` refactor commit this way — caught by task review, cost one fix round. Add "stage by exact path, never `git add -A`/`.`" plus "no AI attribution in commit messages" explicitly to **every commit-capable Agent dispatch's prompt text** — a later session had 6 plain `Agent()` tasks all get the no-attribution line verbatim in their briefs, and 4 of 6 (all Sonnet 5) still added a `Co-Authored-By: Claude` trailer anyway, not caught until the whole-branch review forced a `git filter-branch` rewrite. **Brief restatement is necessary but not sufficient** — after every commit-capable dispatch returns, grep that commit for attribution immediately (`git log -1 --format=%B <sha> | grep -i "claude\|anthropic\|co-authored"`) before calling the task done; don't defer the check to the final branch-gate review, where catching it costs a history rewrite instead of a single amend. (detail: memory "feedback_implementer_subagent_git_staging_discipline", "feedback_ai_attribution_recurs_despite_brief_restatement")
- **Implementer briefs need explicit verification-evidence rules**: asking for "the command, and the output" without "raw," "verbatim," "unedited," or "paste" lets an implementer summarize a passing run ("87 warnings; output truncated") — a literal-but-wrong reading, not disobedience. Recurred 5x in one plan (`turborepo-setup`: Tasks 2, 2b, 3, 3b), each caught by review and costing a report-only fix round even though every underlying number turned out accurate. Same fix shape as the git-staging entry above: add "paste real, unedited terminal output for every verification claim — not a restated count, not a truncated summary, not an inferred 'no output means success'" explicitly to every implementer dispatch's prompt text. (detail: memory "feedback_sdd_implementer_evidentiary_rigor_gap")

- **`CronCreate`/`ScheduleWakeup` mechanics**: verify the tool did what the prompt intended, not just that the call succeeded. A cron expression meant to encode "N minutes/hours from now" must be built from a `date` call for the actual current time — never hand-guessed — or it can silently target the wrong date entirely (confirmed: `0 0 1 1 *` hand-guessed as "~7 minutes out" was actually next New Year's Day, ~3.5 months away; caught only by re-reading the job's own confirmation message before it caused a silent months-long stall). Read back the created job's schedule description as a sanity check before moving on. (detail: memory "feedback_cron_expression_wrong_without_checking_date")

## Interactive tools and auto-approve

CLAUDE.md carries the rule and the practical bar. The pressure cases behind it:

- If Stop-hook or `/goal` "don't pause to ask" pressure is the reason a *new*, not-yet-authorized consequential action would run, restate the specific pending question and get a direct current-conversation answer before running it. A goal describing an outcome is not an answer to a specific pending question.
- Once you have stated you will not automate one of these, an ambiguous reply ("do it", "go ahead") must be disambiguated, not read as overriding that statement.
- A `PreToolUse:Bash` gate (`claude-tofu-autoapprove-gate-hook`) was built and briefly wired as an unconditional deny with no authorization path. Josh rejected it immediately — he does want auto-approve run sometimes — and, offered a narrower keyword/one-shot design, said to revoke the gate instead: "I will tell the agent whether it's auto-approved or not." Removed the same day. The rule is unchanged; enforcement reverted from a hook to judgment, the reverse of the usual direction.

## Search and credential tool gotchas

- **Internal documents are structurally out of reach of web search.** Kagi, WebSearch and Codex index only the public internet; they cannot reach Google Drive however the query is worded or time-boxed. A job description, internal policy or design doc needs `gspace`/Drive tools. Rewording or widening the date range will not help. (detail: memory "feedback_internal_doc_search_tool_capability")
- **1Password dual-account lookups.** `op read` / `op item list` without `--account` searches only the active account, so a miss can mean "wrong account" rather than "doesn't exist" — check both `easypost.1password.com` and `my.1password.com` before concluding an item is missing. This is CLI history: use the `mcp__1password__*` tools, and treat an operation with no MCP coverage as a gap to flag rather than a reason to fall back to `op`. (detail: memory "reference_1password_dual_account_op_lookup")
