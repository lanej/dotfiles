# Git worktree policy

`git-worktree-policy` tracks known repositories globally and optionally limits new linked worktrees by count or disk usage, per repository and globally. It includes worktrees created outside Treehouse, excludes each main worktree from limits, and never edits Treehouse pool state, claims external worktrees as leases, or deletes files. Every decision reads Git's actual `worktree list --porcelain -z`; inventory is reconciled rather than incremented from events.

`make shell` links the executable into `~/.local/bin` alongside the other shell tools. Keep its source checkout available and have Python 3 available, then opt in from each repository:

```sh
git-worktree-policy install
git config --local worktree.limit 4
git config --local worktree.maxBytes 8GiB
git-worktree-policy refresh
git-worktree-policy status --all
```

With [patched Git](git-worktree-hooks.md#install-through-dotfiles) active, these hooks refuse the next worktree creation once a configured budget is full. With stock Git, installation enables inventory refresh and budget warnings; use the explicit preflight command below for cooperating allocation tools. Existing Treehouse slots can still be reused at capacity.

All limits are optional and disabled by default. Local `worktree.limit` sets a nonnegative linked-worktree count, and local `worktree.maxBytes` sets a disk budget. Global Git configuration does not set these repository limits. Zero permits no additions; unset either local key to disable that limit. Byte budgets accept integers or integer sizes such as `500MB` and `8GiB`, with decimal KB/MB/GB/TB and binary KiB/MiB/GiB/TiB units. Global budgets cover all registered repositories:

```sh
git-worktree-policy configure --global --max-bytes 40GiB --max-worktrees 12
git-worktree-policy configure --global --max-worktrees off
```

`install`, `refresh`, hooks, and `preflight` register the current repository by its canonical common Git directory under `$XDG_STATE_HOME/git-worktree-policy/repositories` (default `~/.local/state/git-worktree-policy/repositories`). Global configuration lives alongside that directory in `config.json`. Registration discovers repositories you use with this tool; it does not scan the machine. `status --all` reconciles each known repository, reports local and global limits, counts and allocated disk bytes, and marks unavailable repositories explicitly without deleting their records. An incomplete report exits nonzero, includes only available repositories in its partial count, and omits a global byte total. Each repository also retains `worktree-policy/inventory.json` inside its common Git directory.

Disk accounting includes ignored dependencies and build outputs inside linked worktree directories, skips symbolic links, and deduplicates filesystem inode identities to avoid counting hardlinks or overlapping paths twice within a budget measurement. It uses allocated file blocks rather than logical file sizes. Shared APFS extents and other copy-on-write sharing cannot be identified by this measurement, so totals can conservatively overstate physical usage. Shared Git objects in the main repository are outside the linked-directory budget. Measuring large dependency trees takes time; disk measurements run when a disk budget needs enforcement or global status is requested.

For a retired or moved repository, copy its exact absolute `common_gitdir` from `status --all`, then run `git-worktree-policy forget /absolute/old/repository/.git` to remove only that central registration. Forget uses the historical path without following replacement symlinks, so a new repository reached through the old path keeps its own registration. The command prints the exact removed registry record and errors if none exists; it never removes repository files, local inventory, hooks, configuration, or leases. Before forgetting a moved repository, register its new location with `refresh` and verify the expected worktrees and files are present. Forgetting the unavailable old location allows global budgets to reconcile again. An active repository's next installed hook or explicit reconciliation registers it again.

The installer adds `post-checkout`, `pre-worktree`, and `post-worktree` dispatchers to the common Git directory's default `hooks` directory. Existing hooks move alongside their dispatchers with the suffix `.worktree-policy-original`; executable originals receive the same arguments, environment, and working directory, and their failure status is preserved. Installation is idempotent and preserves Git configuration. Enabled `extensions.worktreeConfig` is supported when every worktree uses the default hooks directory. Before changing any hooks, the installer rejects an effective `core.hooksPath` in the current context, the main worktree, or any linked worktree, including inactive worktrees and relative overrides. Integrate the `hook` command through your existing manager in those contexts. Dispatchers refer to the executable's absolute path, so keep that installation available.

Stock Git invokes `post-checkout` after worktree creation with checkout and after ordinary checkouts. The dispatcher refreshes inventory and warns when any budget reaches or exceeds its cap; policy never rejects checkout. Creation with `--no-checkout`, removals, moves, and pruning have no stock lifecycle notification and become visible on the next reconciliation. Cooperating allocation entrypoints can check current inventory before creation:

```sh
git-worktree-policy preflight && git worktree add ../next-task -b next-task
```

Patched Git invokes `pre-worktree EVENT ID OLD_PATH NEW_PATH` before operations and `post-worktree EVENT ID OLD_PATH NEW_PATH` afterward, with absolute nonempty paths and an empty ID before add allocation. The pre hook refuses `add` when the actual local or global count or allocated bytes already reaches its configured cap; other operations remain available. The post hook refreshes after add, move, remove, and prune. Hook integrations can invoke `git-worktree-policy hook pre-worktree "$@"`, `git-worktree-policy hook post-worktree "$@"`, or `git-worktree-policy hook post-checkout "$@"` as appropriate. Reusing an existing Treehouse slot creates no worktree and remains available at capacity.

Checks and additions are separate operations, so simultaneous creators can overshoot. Stock Git callers that omit preflight can also overshoot. Byte budgets gate on current usage and do not predict the size of a new checkout or restrict subsequent build growth. The next preflight or patched pre-add sees actual usage and refuses further allocation. A configured budget that cannot be evaluated visibly rejects admission; an unavailable registered repository blocks a configured global budget. Notification hooks report evaluation failures and preserve ordinary Git operations. Original hooks retain their own failure behavior.

Verify the stock fallback with `make test-git-worktree-policy`. It uses disposable real stock-Git repositories, real allocated files, and direct calls to the native hook interface. Run `make test-treehouse-worktree-policy GIT_WORKTREE_HOOKS_GIT=/path/to/patched/bin/git` with native Treehouse installed to exercise actual veto delivery, repository and global disk gates, and reuse of an idle pool slot at capacity. These checks create and return only their disposable leases; native return requires process-inspection permission.
