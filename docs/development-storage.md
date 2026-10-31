# Development storage

`make dev-cache-schedule` installs an hourly user job and the editable `~/.config/dev-cache-budgets.json`. Defaults are 4 GiB for uv, 2 GiB each for Go build, npm download, and Cargo download caches, 4 GiB for Go modules, and 8 GiB across Rust `target` directories in `~/src`, `~/Documents/Codex`, and Paseo worktrees. Run `dev-cache-prune --dry-run` to inspect usage. Setup records the installed Python executable, Node/npm and Go directories, and Go workspace path. Rerun the setup target after replacing Python, Node, or Go or changing the Go workspace. Developer temporary folders are scanned for borrowed cache files; macOS Apple app-private temporary folders are excluded.

Preview worktree cleanup across all projects with `git-worktree-cleanup ~/src`,
or run it from `~/src` without an argument. Inside a repository, the command
checks only that repository unless you pass a directory to sweep. Discovery
includes grouped projects, stops descending at the first repository in each
directory branch, deduplicates linked checkouts, and checks
each repository's registered worktrees even when they live outside `~/src`.
One table lists repositories, base refs, worktree disk usage, and retention
reasons, sorted by disk usage from smallest to largest, with unknown sizes last.
A combined estimate follows for eligible checkouts. Terminal
progress covers discovery and scanning, including when stdout is redirected.
Disk sizes are cached for 15 minutes in
`${XDG_CACHE_HOME:-~/.cache}/git-worktree-cleanup`; the `SIZE AGE` column marks
cached estimates. Use `--refresh` to remeasure sizes. Missing or replaced
directories invalidate their entries. Git state and activity checks run fresh,
including immediately before removal. If the cache is unavailable, sizes are
measured directly.

Prune only large checkouts with `git-worktree-cleanup --min-size 1GiB ~/src`; add `-y` to apply. `--min-size` also works with `--worktree`, `--json`, the acceptance flags, and `--wip-push`. It compares allocated disk usage, retaining checkouts below the threshold and reporting the reason in the table. Filtering always measures eligible checkouts fresh and remeasures before removal, so a cached estimate cannot qualify a checkout that has shrunk. Unknown sizes remain registered. K/M/G/T and KiB/MiB/GiB/TiB use binary units; KB/MB/GB/TB use decimal units. Bare values and B mean bytes, and fractions such as `0.5GiB` are accepted.

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
Tracked files marked assume-unchanged or skip-worktree retain their checkout,
because Git status can hide edits to those files.

Use explicit exceptions to relax individual eligibility checks. `--accept-dirty` permits discarding tracked edits, untracked files, and edits hidden by assume-unchanged or skip-worktree flags. `--accept-ignored` permits discarding ignored artifacts beyond the usual disposable build caches. `--accept-unmerged` permits removing a checkout whose named local branch retains its unmerged HEAD. `--accept-recent` bypasses the age threshold. Each flag leaves the other checks in place. Preview one dirty checkout with `git-worktree-cleanup --accept-dirty --worktree /path/to/checkout`, then apply with `git-worktree-cleanup --accept-dirty -y --worktree /path/to/checkout`. Combine flags as needed for one checkout or a project sweep, such as `git-worktree-cleanup --accept-unmerged --accept-recent ~/src`.

`--force` is shorthand for all four exceptions. Preview with `git-worktree-cleanup --force ~/src` and apply with `git-worktree-cleanup --force -y ~/src`. Flags apply to all eligible worktrees in the requested scan; local-file exceptions explicitly report that accepted files will be discarded. The table starts with one preview/apply line. Its `STATUS` column shows the action followed by accepted conditions observed for that checkout, such as `force-remove (dirty,unmerged,recent)`; unused exceptions are omitted. JSON exposes the same `status` and per-row `accepted_conditions` while preserving the machine-readable `action`. `--json` previews and `--integrated` are supported. `--accept-recent` also works with `--wip-push`; the other exceptions and `--force` exclude that preservation mode.

Branches and their commits remain accessible after removal. Detached HEAD still requires the usual merge eligibility. Primary checkouts, Treehouse pool slots, locked or active worktrees, unresolved index conflicts, and unfinished Git operations remain protected. A valid base ref and successful safety checks are still required, and eligibility is rechecked immediately before removal. Unaccepted ignored artifacts and hidden index flags are checked again after the activity check, followed by Git-operation and commit-retention checks.

Preview preservation of dirty or unmerged work with
`git-worktree-cleanup --wip-push ~/src`. This mode accepts only effective GitHub
push URLs owned by `easypost-sandbox`, preferring `origin` or another approved
remote. The table shows each proposed recovery branch. Add `-y` to create a
unique `wip/cleanup/...` branch, commit tracked changes and untracked source,
push that snapshot, verify its remote ref, and remove the checkout. Original
branches are retained; detached work gets a named recovery branch too.
The age threshold applies before the snapshot commit. A base ref is unnecessary
in this mode, and the usual activity, lock, and ignored-artifact checks still
apply. Unfinished Git operations are retained. Commit or push failures, remote
verification failures, and changes made during publication leave the checkout
in place, with any completed WIP commit retained on its local recovery branch.

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
