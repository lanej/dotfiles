# Anthropic Skills

Skills published by Anthropic are not tracked in this repo. They were vendored
from https://github.com/anthropics/skills on 2026-01-17 and untracked on
2026-09-24 because frozen copies go stale and shadow the maintained versions.

Install them from the source instead:

- `skill-creator`, `frontend-design`: enabled as `claude-plugins-official`
  plugins in `.claude/settings.json`.
- Everything else (`pdf`, `docx`, `pptx`, `xlsx-python`, `algorithmic-art`,
  `canvas-design`, `theme-factory`, `slack-gif-creator`, `doc-coauthoring`,
  `internal-comms`, `brand-guidelines`, `mcp-builder`, `web-artifacts-builder`,
  `webapp-testing`): install from the anthropics/skills marketplace, or keep a
  local copy under `claude/skills/` — `.gitignore` lists every name, so a local
  copy stays untracked.

`xlsx-python` was renamed from Anthropic's `xlsx` to avoid colliding with the
repo-owned `xlsx` CLI skill, which remains tracked.
