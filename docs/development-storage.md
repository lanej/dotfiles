# Development storage

`make dev-cache-schedule` installs an hourly user job and the editable
`~/.config/dev-cache-budgets.json`. Defaults are 4 GiB for uv, 2 GiB each for
Go build, npm download, and Cargo download caches, 4 GiB for Go modules,
and 8 GiB across Rust
`target` directories in `~/src`, `~/Documents/Codex`, and Paseo worktrees.
Run `dev-cache-prune --dry-run` to inspect usage.
Setup records the installed Node/npm directories and Go workspace path.
Rerun the setup target after replacing Node or changing the Go workspace.
Developer temporary folders are scanned for borrowed cache files; macOS Apple
app-private temporary folders are excluded.

Preview worktree cleanup across all projects with `git-worktree-cleanup ~/src`,
or run it from `~/src` without an argument. Inside a repository, the command
checks only that repository unless you pass a directory to sweep. Discovery
includes grouped and nested projects, deduplicates linked checkouts, and checks
each repository's registered worktrees even when they live outside `~/src`.
The report shows disk usage per worktree and a combined estimate for eligible
checkouts.

Add `-y` to remove eligible worktrees. The tool retains primary, locked, active,
dirty, and unmerged checkouts, plus those with recent HEAD commits, and checks
eligibility again before each removal. Checkout creation time does not set its
age: a new checkout of an old commit can be eligible. Ignored files are retained
except for recognized dependency and build
caches such as `node_modules`, `.venv`, and `target`. It requires `lsof` to
inspect processes belonging to your user; if that check fails, worktrees stay
in place. Each project uses its own `origin/HEAD` ref, falling back to local
`main` or `master`; use `-b` for a different base ref. Refs are read locally,
so refresh them before relying on the report. Project errors are reported
without stopping the remaining sweep, and branches are retained.

These are periodic size budgets. Busy caches and targets are deferred and
checked again on the next run. Native managers clean over-budget caches;
Cargo trims old entries. npm's installed `_npx` tools, installed Rust toolchains,
virtual environments, source, datasets, and browser installations are retained.
Go cleanup waits until Go processes and language servers stop. Downloaded
Go modules and cached Go toolchain downloads may be fetched again afterward.
Environment or tool symlinks into a cache prevent its eviction.

Worktrees already share their Git object database. Reuse each package manager's
normal download cache rather than allocating one per task. Keep Python caches
on the same filesystem as virtual environments so uv can use hard links or
copy-on-write clones. Keep distinct dependency versions isolated: symlinking
mutable `node_modules`, virtual environments, or build outputs across different
branches can mix their dependencies or artifacts. Use a package manager's
content store to share immutable package files instead.

Link read-only datasets, verified package artifacts, and browser installations
to their canonical locations when another worktree needs them. Do not copy
these into every checkout. Keep build outputs local and disposable; the Rust
target budget removes inactive outputs when their combined size exceeds its
limit. Test runs needing a temporary cache must remove it at completion.
