# Agent operating procedures

Read the section selected by global instructions when that workflow applies. Preserve host instruction precedence and existing user authorization.

# Markdown formatting

Keep each Markdown paragraph on one source line. Do not hard-wrap prose to a fixed column width; let editors and renderers wrap it.

# Code comments

For source-comment decisions, use the project's installed `code-comments` skill when present; preserve repository conventions when no project profile is installed. Routine edits do not require loading the full specification; follow the skill's conditional reference triggers. Honor the target repository's conventions and do not rewrite unrelated comments.

# Browser automation

Default local pages and UI validation to headless Playwright MCP. Headless browsers avoid macOS window focus and accidental keyboard input. Launch visible browsers only when the user explicitly requests them. Use CUA/native integration for explicitly requested real, signed-in browser work. Close agent-owned MCP browsers gracefully when finished. For raw Playwright, set `headless: true`; close contexts and browsers in `finally`. On macOS, use approved shell escalation before raw browser launches. Sandboxed macOS launches can abort during application registration and trigger crash alerts.

# Project engineering

Follow the target repository's instructions and explicitly installed source-code profile for engineering, review, and publication policy. A workstation tool or skill installation does not select project gates or authorize publication. Preserve the user's authorization boundaries and verify external outcomes before reporting completion.

# Bug reports

Before filing any bug report or making a substantive revision, invoke `bug-reporter` as a separate subagent. Supply the destination, supported markup, required fields, observed failure, existing evidence, and current report if revising. Its only job is to report: do not ask it to investigate, reproduce, fix, or submit. Missing reproduction alone does not block a report.

Follow `~/.files/docs/bug-reports.md`. Encourage load bearing screenshots, diagrams, and concrete output; every image and paragraph must help the reader understand or assess the failure. Omit redundant or decorative content. Resolve the reporter's blockers, use its draft, then submit through the existing authorized workflow and verify the saved report, links, and images. Distinguish drafting, filing or message delivery, and eventual repair.

The reporter must not invoke further writers or reviewers. If named selection is unavailable, use a generic drafting-only agent with the `developer_instructions` from `~/.codex/agents/bug-reporter.toml` or the shared `~/.files/ai/agents/bug-reporter.md` definition. If neither route is available, report the delegation gap explicitly. Reuse an unchanged approved draft; substantive revisions need a new pass. Feature requests keep their existing writers and workflows.

# Git worktree location

Use the `worktree` skill at `~/.agents/skills/dotfiles/worktree/SKILL.md` for task isolation and agent-created checkouts. The native manager creates `<primary-repository>/.worktrees/<agent>-<8-hex>/`; do not fall back to temporary paths or new Treehouse leases.

Reuse explicit user-selected, host-managed, and preassigned Firstmate checkouts. Do not nest worktrees or claim their leases.

# Git worktree cleanup

Finish owned manager task protection and explicitly prune through the `worktree` skill. Return outstanding pooled Treehouse leases through the legacy `treehouse` skill. Apply the following preservation rules to task-owned non-pool worktrees; never remove an active or uncertain manager task by bypassing its protection.

Treat cleanup of temporary worktrees created for the task as part of completion. This includes temporary worktrees created by subagents for the same task. Record their paths and the starting checkout so ownership stays clear across subagents and handoffs.

Before the final response, remove each task-owned temporary worktree whose work is safely retained and which no active session, process, or pending task needs. An open PR alone does not require keeping its checkout: keep the branch for review updates and recreate a worktree when needed. Preserve commits on a named branch or verified remote ref before removing a detached worktree.

Check `git status --short --untracked-files=all` and any valuable ignored files before removal. Retain a worktree with uncommitted work or needed local artifacts unless that work has been preserved elsewhere. Leave pre-existing, permanent, user-owned, and other agents' active worktrees alone; age is not proof of inactivity.

Move outside the worktree first, then use `git worktree remove <path>` from a surviving checkout. Do not force removal or delete branches as a cleanup side effect. For registrations whose directories are already gone, inspect `git worktree prune --dry-run --verbose` before running `git worktree prune`. Verify the result with `git worktree list`.

Do this cleanup within the authorized task without asking for routine confirmation. If a task-owned worktree must remain or removal is blocked, include its path and the concrete reason in the final response.

# Development storage

Use the normal shared package-manager download caches; do not create a cache per worktree. Link read-only datasets, verified package artifacts, and browser installations to their canonical locations. Keep mutable dependencies and build outputs isolated when versions differ. Remove disposable test dependencies and temporary caches at task completion while retaining useful logs and artifacts. See `~/.files/docs/development-storage.md` for the installed cache budgets.
