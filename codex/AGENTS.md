<!-- builder:start -->
# Default software guidance: Builder

For software design, implementation, modification, debugging and review, use the project's explicitly selected repository-local Builder core when available; otherwise read `~/.local/share/software-standards/builder/SKILL.md`. Load detailed references by its task triggers; preserve project constraints and instruction precedence.
<!-- builder:end -->

# Shared practices

Keep Markdown paragraphs on one source line. For changed source comments, read `~/.files/docs/conventional-code-comments.md`; use selective `TAG: explanation` for rationale/constraints/consequences, respecting ordinary comments/docstrings and repository conventions. Leave unrelated comments alone.

Follow ESR's Unix rules in software design: modularity, clarity, composition, separation of policy/mechanism and interface/engine, simplicity, parsimony, transparency, robustness, representation of knowledge as data, least surprise, silence without useful output, early clear failure/repair, programmer economy, generation, working behavior before optimization, diversity and extensibility.

# Conditional workflows

Read the relevant section of `~/.files/docs/agent-operating-procedures.md` when performing a workflow below; the safeguards and exceptions there remain binding.

- **Browser automation:** Default local/UI checks to headless Playwright MCP. Visible browsers require explicit request; use native/CUA for requested real signed-in work. Close owned browsers gracefully. Raw Playwright uses `headless: true` and `finally` cleanup; macOS raw launches require approved shell escalation.
- **PRs and reviews:** Every GitHub PR creation/title/body revision needs separate `github-pr-writer`, including documentation-only PRs. Resolve blockers and use its draft; procedures specify inputs/fallbacks. Other platforms use `pull-request-writer`. Complex behavior needs independent `code-reviewer`, actionable fixes and review of material fixes; line count is irrelevant. Writers/reviewers must not recurse.
- **PR descriptions:** Explain final behavior and why concisely; omit duplicate automated results, unused sections, checklists and implementation history. Mention material manual evidence/gaps. Screenshots, when useful, show the actual result through a verified durable inline image URL.
- **Go:** Read the repository-local Go skill or `~/.agents/skills/dotfiles/go/SKILL.md`. New Go repositories adopt its portable correctness profile through `repo-bootstrap --go`; preserve and reconcile existing project checks. Run the same committed checks locally and in CI.
- **Bug reports:** Before filing/substantive revision use separate drafting-only `bug-reporter` and read `~/.files/docs/bug-reports.md`. Procedures specify inputs/fallbacks. Resolve blockers, submit with authorization and verify saved links/images. Missing reproduction alone is not blocking; reuse unchanged approved drafts. Reporter must not investigate, fix, submit or recurse; feature requests keep their writers.
- **Worktrees:** Use `~/.agents/skills/dotfiles/treehouse/SKILL.md`; reuse user-selected/host-assigned/Firstmate checkouts without nesting or claiming leases. Return owned pool leases through Treehouse. Clean up task-owned non-pool worktrees before finishing only after preserving work, inspecting tracked/untracked/valuable ignored files and confirming no active need. Preserve other checkouts; never force removal or delete branches as a cleanup side effect. Read the full cleanup procedure before removal/pruning; report retained paths and concrete reasons.
- **Storage:** Share download caches/verified read-only artifacts; isolate mutable dependencies/builds when versions differ. Remove task disposables; read `~/.files/docs/development-storage.md`.
- **Slack:** Read `~/.agents/skills/dotfiles/slack/SKILL.md`; use its CLI/MCP and `josh-slack-voice` when writing as Josh. Do not use native Slack connector skills, automatic Plugin Management or OpenAI connector key setup. Chrome is only for explicitly requested signed-in work.
- **Google Workspace:** Read applicable GSpace skills/references under `~/.agents/skills/<product>/`; use installed `gspace` CLI through shell. Cross-product/setup uses `google-workspace`. Skills/help are authoritative; no built-in Workspace knowledge, plugins/connectors, app/MCP tools (including GSpace MCP), direct APIs or browser automation. Do not discover alternate integrations; report unsupported operations without switching tools or inventing commands.

# Codex MCP configuration

Codex MCP servers are manually curated. Preserve user removals, disabled flags, and custom settings. Prefer installed CLIs when available. Do not import servers from Claude, plugins, backups, or other configs, or add or re-enable a server, unless the user explicitly requests that change.
