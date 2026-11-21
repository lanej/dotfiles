# Select repository automation guidance

Read the checkout’s `octo-manager.toml` and the current PR’s explicit auto-merge setting from Octo evidence. An explicit per-PR setting takes precedence over the repository default; select only its matching reference. Otherwise resolve `[merging].auto_merge` as follows:

| Installed setting | Read |
| --- | --- |
| `true` | [Enabled automatic merging](auto-merge-enabled.md) |
| `false` | [Disabled automatic merging](auto-merge-disabled.md) |
| `"project_stage"` with installed `.source-code.json` stage `research` or `alpha` | [Enabled automatic merging](auto-merge-enabled.md) |
| `"project_stage"` with installed stage `beta`, `production`, missing, or unknown | [Disabled automatic merging](auto-merge-disabled.md) |

Use the installed stage, not desired `source-code.toml`, a release version, or perceived maturity. Load only the effective reference. When an explicit PR override is unknown, inspect Octo evidence before claiming an effective switch. Do not toggle a PR or edit configuration just to match the task’s preference. `--inherit` restores repository inheritance only when authorized.

Invalid or unavailable repository policy suspends inherited automatic merging and retains last-valid notification instructions. Do not invent defaults or assume an already-submitted operation was cancelled; inspect reconciliation evidence. Source-code setup seeds this file only when Octo is selected and preserves authored settings on later setup and upgrades.

When handling a notification, read [state-specific follow-up](notification-instructions.md).
