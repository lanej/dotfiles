# Pi daily driver

Use the Bun version in `.bun-version` for dependency installation, commands, checks, and managed Pi hosts. Preserve the strict TypeScript profile; run `bun run check` and the native acceptance check affected by a change. Node-compatible imports do not require the Node executable.

Keep the package usable outside dotfiles. Read `EXTRACTION.md` before updating vendored clients, guidance, theme resources, or generated bindings. Preserve upstream license notices. External Beads, Zellij, worktree manager, and Octo integrations are optional and remain separate authorities. Gate their effects on explicit configuration and availability; keep core commands usable without them.

The pre-extraction driver has no database contents to migrate. Persist new attempts and recovery state during normal operation. Preserve user settings, credentials, active sessions, retained transcripts, and uncertain execution attempts. Installation and successful checks do not establish that a running session loaded the new version. Keep Markdown paragraphs on one source line.
