# Standalone worktree management

The optional [worktree-manager](https://github.com/lanej/worktree-manager) tool installs the native `worktree` command for fresh task checkouts, global inventory, optional budgets and explicit safe pruning. It has no reusable checkout pool and does not require Python or Go on installed machines. Cleanup uses Bash, Git, `lsof` and standard Unix tools; optional `sqlite3` adds Codex session information.

## Opt in

Add `worktrees` to this machine's existing set list, then run `make plan` and `make install`:

```toml
sets = ["macos", "worktrees"]
```

The set selects `worktree-manager` and its `lsof` dependency, and disables future installation of the older standalone `worktree-policy` binary. Existing machine sets and explicit overrides still compose normally. You can instead set `worktree-manager = true` in the machine's `[tools]` table.

The installer downloads the pinned [v0.1.0 release](https://github.com/lanej/worktree-manager/releases/tag/v0.1.0), verifies the platform executable and checksum, and installs `~/.local/bin/worktree`. Receipt checks preserve modified or unmanaged binaries. `WORKTREE_INSTALL_BINARY` selects an offline native executable with an adjacent `.sha256` file.

Configuration selects the new manager as the existing named hooks' provider, without adding a second observer or replacing repository hook files. `git-worktree-policy` forwards its existing command interface to `worktree policy` when that provider is selected. If both tools are selected, the manager takes precedence. Disabling it and running `make configure` restores the older provider when selected; disabling both disables the named hooks. A selected but missing executable still blocks admission and only warns on ordinary checkout.

A missing `$XDG_CONFIG_HOME/worktree-manager/config.json` (default `~/.config/worktree-manager/config.json`) is initially seeded with the existing `easypost-sandbox` recovery-push owner restriction. Existing configuration, including symlinks, is preserved. Edit that machine-local file to change approved owners. The standalone tool otherwise approves no recovery destinations by default.

## Use

```sh
worktree backfill ~/src ~/.files    # Explicitly discover existing worktrees.
worktree create --branch task/example --json
worktree status
worktree finish TASK_ID             # Finish protection; keep the checkout.
worktree prune --all                # Preview and explain retention reasons.
worktree prune --all --apply        # Recheck and remove eligible preview candidates.
```

New tasks remain protected until explicitly finished. Pruning still requires all other safety checks. Limits remain optional and disabled by default; exceeding one never deletes anything. The existing registry, local Git settings and global budgets remain compatible.

This opt-in does not retire Treehouse, change agent worktree instructions, claim existing leases, or alter Octo Manager repair repositories. Existing Treehouse pool directories remain protected. See the [tool documentation](https://github.com/lanej/worktree-manager/blob/v0.1.0/README.md) for the complete lifecycle, cleanup, JSON and recovery contracts.

## Verify

`make test-worktree-manager WORKTREE_MANAGER_BINARY=/path/to/worktree-PLATFORM-ARCH GIT_WORKTREE_HOOKS_GIT=/path/to/patched/git` exercises actual installation, provider selection, global vetoes, missing-binary behavior, opt-out and configuration preservation in disposable homes and repositories. Keep the native executable's adjacent checksum file available. The feature workflow downloads the pinned public packages; it does not compile Git or Go.
