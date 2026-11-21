# Select application tool policy

Before choosing application libraries, API protocols, or migration scope, read the installed `.source-code.json`. Authored `source-code.toml` expresses desired policy; `source-code explain` shows differences. Apply the installed choices at every lifecycle stage. Never infer authority from hosting, repository names, or public visibility.

Read exactly one authority reference and one adoption reference matching the installed values, relative to this directory:

| Configuration | Read |
| --- | --- |
| `authority = owned` | [Owned authority](authority-owned.md) |
| `authority = shared` | [Shared authority](authority-shared.md) |
| `authority = upstream` | [Upstream authority](authority-upstream.md) |
| `adoption = hold` | [Hold adoption](adoption-hold.md) |
| `adoption = new` | [New-surface adoption](adoption-new.md) |
| `adoption = backfill` | [Backfill adoption](adoption-backfill.md) |

Do not load the other configuration variants. Read [the application tool catalog](tool-catalog.md) only when both selected policies permit applying it to the affected capability. A local or shadow installation does not establish project agreement. Missing or unknown settings do not grant stack selection or migration permission: preserve established conventions and resolve the policy before applying the catalog. Use the source-code management skill for setup or configuration changes.
