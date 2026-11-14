# Shared practices

Keep Markdown paragraphs on one source line. Honor repository instructions and explicitly installed project guidance.

# Agent coordination

Use Codex's native agent tools to delegate and communicate with other Codex agents. Paseo is used with Pi; do not use Paseo to create, delegate to, or message Codex agents.

# Conditional workflows

Read the relevant section of `~/.files/docs/agent-operating-procedures.md` when performing a workflow below; the safeguards and exceptions there remain binding.

- **Zellij collaboration:** Recognize shared terminal context proactively. When running in Zellij, or task context indicates a shared Zellij session, read `~/.agents/skills/dotfiles/zellij/SKILL.md` and use its collaboration helpers. Interpret “show me” in context and present relevant content in a suitable existing pane or task-owned shared view when useful. Inspect the session before targeting panes. For images over SSH, use the skill's streamed display workflow. Missing environment variables or restricted socket access do not establish that Zellij is unavailable.
- **Browser automation:** Default local/UI checks to headless Playwright MCP. Visible browsers require explicit request; use native/CUA for requested real signed-in work. Close owned browsers gracefully. Raw Playwright uses `headless: true` and `finally` cleanup; macOS raw launches require approved shell escalation.
- **Bug reports:** Before filing/substantive revision use separate drafting-only `bug-reporter` and read `~/.files/docs/bug-reports.md`. Procedures specify inputs/fallbacks. Resolve blockers, submit with authorization and verify saved links/images. Missing reproduction alone is not blocking; reuse unchanged approved drafts. Reporter must not investigate, fix, submit or recurse; feature requests keep their writers.
- **Worktrees:** Use `~/.agents/skills/dotfiles/treehouse/SKILL.md`; reuse user-selected/host-assigned/Firstmate checkouts without nesting or claiming leases. Return owned pool leases through Treehouse. Clean up task-owned non-pool worktrees before finishing only after preserving work, inspecting tracked/untracked/valuable ignored files and confirming no active need. Preserve other checkouts; never force removal or delete branches as a cleanup side effect. Read the full cleanup procedure before removal/pruning; report retained paths and concrete reasons.
- **Storage:** Share download caches/verified read-only artifacts; isolate mutable dependencies/builds when versions differ. Remove task disposables; read `~/.files/docs/development-storage.md`.
- **Slack:** Read `~/.agents/skills/dotfiles/slack/SKILL.md`; use its CLI/MCP and `josh-slack-voice` when writing as Josh. Do not use native Slack connector skills, automatic Plugin Management or OpenAI connector key setup. Chrome is only for explicitly requested signed-in work.
- **Google Workspace:** Read applicable GSpace skills/references under `~/.agents/skills/<product>/`; use installed `gspace` CLI through shell. Cross-product/setup uses `google-workspace`. Skills/help are authoritative; no built-in Workspace knowledge, plugins/connectors, app/MCP tools (including GSpace MCP), direct APIs or browser automation. Do not discover alternate integrations; report unsupported operations without switching tools or inventing commands.

# Codex MCP configuration

Codex MCP servers are manually curated. Preserve user removals, disabled flags, and custom settings. Prefer installed CLIs when available. Do not import servers from Claude, plugins, backups, or other configs, or add or re-enable a server, unless the user explicitly requests that change.
