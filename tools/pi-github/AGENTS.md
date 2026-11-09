# Development

Use Builder at `~/.local/share/software-standards/builder/SKILL.md`. Use Bun 1.4.4 and the committed bun.lock. Run `bun run check` and `bun run build` before handoff. Keep Markdown paragraphs on one source line.

The coordinator owns durable state and all GitHub/Git effects. Workers receive only typed scoped tools. Do not add unrestricted shell tools, load project extensions, copy Codex credentials, or write to remote GitHub objects as part of the demo.
