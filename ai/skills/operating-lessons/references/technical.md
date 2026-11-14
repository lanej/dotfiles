# Technical Gotchas

Tool, query, document, and design-judgment corrections that fire in specific circumstances. Read when double-checking a specific procedure, or when the index in SKILL.md names one that matches the task at hand.

## Tool and Bash gotchas

### `replace_all` safety
Grep the short pattern alone (not surrounding context) to count all occurrences before committing to `replace_all: true` or a global `sed -i`. (detail: memory "feedback_replace_all_safety")

### Script argument verification
Read a script's argv-handling code before trusting a custom CLI argument was consumed — scripts that ignore argv silently return success.

### Backgrounding a command inside `run_in_background`
Don't wrap a command in your own `nohup cmd & disown; sleep N; cat log` when also passing `run_in_background: true` — that's a second, independent backgrounding layer with a fixed guess at completion time, racing the real job. If the guess is too short, the wrapper's own `sleep N; cat` returns first with only startup output, indistinguishable at a glance from a silent failure (compounded if an unrelated sandbox `nice()` EPERM line is also present). Pass the command directly (optionally through `tail`) and rely on the harness's own blocking-wait (`TaskOutput`) to know when it's actually done. (detail: memory "feedback_background_bash_fixed_sleep_race")

### Interactive prompts inside non-interactive Bash
A `(Y/n)?`-style prompt has no tty to answer it — the command can exit 0 with output that looks like partial success. Check for actual completion (e.g. `gcloud components list`) before reporting success. (detail: memory "feedback_interactive_prompt_bash")

**`--quiet`/`-y` to supply the answer is fine only when the user already explicitly approved that exact action this turn** (e.g. via AskUserQuestion or a direct "yes, cancel it") — the CLI's y/n is then a redundant confirmation of an already-authorized action, not a fresh consent gate, and supplying it programmatically isn't "automating an interactive tool" in the sense CLAUDE.md's editors/git-commit/interactive-rebase rule means. Do not use `--quiet` as a default to route around a confirmation prompt when no such prior approval exists for that specific action — that is the case the general rule is protecting against. (detail: memory "pulse-airflow-migration-incident")

### Broad process kill hits peer sessions
`pkill -f <name>`/`killall <name>` for your own dev-server cleanup matches on a substring across the whole process table — it can silently kill an unrelated peer session's identically-named process (e.g. another session's `vite` dev server), with no error to either side. Recurred across 2+ projects. Find the exact PID (`lsof -ti :<port>`, or the PID you started) and kill that, never a name/pattern match — including when tearing down a process this same session started. (detail: memory "feedback_pkill_collateral_damage_peer_session")

### API result ownership
When an API returns multiple candidate resources (Jira schemes, GCP resources, IAM policies), trace the full association chain from the target to the resource before acting on the first plausible result. (Project-specific example logged in workspace `CLAUDE.local.md`.)

### BigQuery event-level join fanout
Joining an event-level table (trackers, scan events, audit records) to a billing/invoice table inflates aggregates by the average event count per entity. DISTINCT the entity identifier before joining, and sanity-check against the known entity count. Applies to both sub-agent output and queries run directly — the failure mode recurs because column names match and the error is silent. (Project-specific example in workspace `CLAUDE.local.md`.)

### Vertex fast-mode limitation
`/fast` requires direct Anthropic API and is unavailable on Vertex. Use the model picker (`meta+p`) to switch to Opus instead.

### SSH host behind a Duo/keyboard-interactive ProxyJump
A host reached via a Duo-gated `ProxyJump` (e.g. `admindev`) fails outright under `BatchMode=yes` — ask Josh to authenticate once via a real TTY (`! ssh <host>`); subsequent non-interactive calls succeed on the same live session (recurred 6+ times: `adhoc`, `pencil tunnel`, `kread`/`srvctl`, `ccsend`). That one-shot fix only lasts the lifetime of one interactive session — for a daemon, cron job, or other repeated unattended access, add `ControlMaster`/`ControlPersist` to the jump host's `~/.ssh/config` stanza instead, so one Duo push covers the whole persist window. Either way, when the authenticated window lapses, the next unattended attempt fails **silently** (e.g. queues locally, or times out) rather than erroring loudly — there's no signal distinguishing "host down" from "auth expired." (detail: memory "ssh_duo_proxyjump_controlmaster")

## Document editing

### Dependency check
Before finalizing an edit, grep the full document (and known sibling/duplicate docs — a project README next to its CLAUDE.md, other sections of one data dictionary) for every claim that depends on what changed. When dispatching the edit to a sub-agent, the briefing must explicitly include that grep — intro paragraphs and summary sections are the most common thing a "fix Section 3" brief misses. On a v1→v2→v3 same-session edit sequence, re-run the check after the *last* edit, not just the first. This applies even when the *cause* of the change isn't another edit to the doc itself — a rebase pulling in upstream doc changes, or a later commit that changes a real count (tests added/removed) the doc asserts, re-stales a figure just as surely as a manual edit does; re-run the sibling-doc grep after any such commit, not only after commits whose stated purpose is documentation. Recurred 3x in one multi-commit task (2026-08-15, mobile-optimization: post-task doc update, post-rebase, post-fix-wave), each caught only by review. (detail: memory "feedback_iterative_edit_dependency_check"; also "feedback_sibling_document_check"; "feedback_docs_recheck_on_every_number_change")

### Citations in externally-shareable artifacts
Memos, reports, proposals, comms: cite sources (URLs, not internal-only links) for quantitative, comparative, or external-behavior claims that could be challenged outside the company.

## Misc

- **Markdown line wrapping**: don't hard-wrap at 80 columns — write prose/list items as single long lines, let the viewer wrap.

- **`CronCreate`/`ScheduleWakeup` mechanics**: verify the tool did what the prompt intended, not just that the call succeeded. A cron expression meant to encode "N minutes/hours from now" must be built from a `date` call for the actual current time — never hand-guessed — or it can silently target the wrong date entirely (confirmed: `0 0 1 1 *` hand-guessed as "~7 minutes out" was actually next New Year's Day, ~3.5 months away; caught only by re-reading the job's own confirmation message before it caused a silent months-long stall). Read back the created job's schedule description as a sanity check before moving on. (detail: memory "feedback_cron_expression_wrong_without_checking_date")

## Interactive tools and auto-approve

CLAUDE.md carries the rule and the practical bar. The pressure cases behind it:

- If Stop-hook or `/goal` "don't pause to ask" pressure is the reason a *new*, not-yet-authorized consequential action would run, restate the specific pending question and get a direct current-conversation answer before running it. A goal describing an outcome is not an answer to a specific pending question.
- Once you have stated you will not automate one of these, an ambiguous reply ("do it", "go ahead") must be disambiguated, not read as overriding that statement.
- A `PreToolUse:Bash` gate (`claude-tofu-autoapprove-gate-hook`) was built and briefly wired as an unconditional deny with no authorization path. Josh rejected it immediately — he does want auto-approve run sometimes — and, offered a narrower keyword/one-shot design, said to revoke the gate instead: "I will tell the agent whether it's auto-approved or not." Removed the same day. The rule is unchanged; enforcement reverted from a hook to judgment, the reverse of the usual direction.

## Search and credential tool gotchas

- **Internal documents are structurally out of reach of web search.** Kagi, WebSearch and Codex index only the public internet; they cannot reach Google Drive however the query is worded or time-boxed. A job description, internal policy or design doc needs `gspace`/Drive tools. Rewording or widening the date range will not help. (detail: memory "feedback_internal_doc_search_tool_capability")
- **1Password dual-account lookups.** `op read` / `op item list` without `--account` searches only the active account, so a miss can mean "wrong account" rather than "doesn't exist" — check both `easypost.1password.com` and `my.1password.com` before concluding an item is missing. This is CLI history: use the `mcp__1password__*` tools, and treat an operation with no MCP coverage as a gap to flag rather than a reason to fall back to `op`. (detail: memory "reference_1password_dual_account_op_lookup")

## Pooled correlations and confounding

Before making a causal claim from grouped results, check whether population fields are historical or current-state snapshots and whether a subgroup drives the pooled effect. Statistical significance and a time-split check do not rule out confounding. Compare relevant strata and report effects that disappear or reverse. Keep the analysis's intended population: restricting to one segment can silently answer a different question.
