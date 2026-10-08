# Development storage

`make dev-cache-schedule` installs an hourly user job and the editable
`~/.config/dev-cache-budgets.json`. Defaults are 4 GiB for uv, 2 GiB each for
Go build, npm download, and Cargo download caches, 4 GiB for Go modules,
and 8 GiB across Rust
`target` directories in `~/src`, `~/Documents/Codex`, and Paseo worktrees.
Run `dev-cache-prune --dry-run` to inspect usage.
Setup records the installed Node/npm directories, including nvm installations.
Rerun the setup target after replacing a Node installation.

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
