# Git worktree lifecycle hooks

This development patch series adds worktree lifecycle notifications and a veto hook to Git 2.56.0. The interface is local and may change as upstream review progresses. Platform packages are published in a versioned dotfiles release; no separate Git fork repository is required. The runtime reports `git version 2.56.0.worktree-hooks.1` and is built separately; building and downloading its package never replaces the machine's original Git.

`0001-post-worktree.patch` follows [GitGitGadget PR #2442](https://github.com/git/git/pull/2442), pinned to revision `e5855a14919a6ccc7ba0af7e2aa765245f91fccc`. `0002-pre-worktree.patch` adds the local veto interface and its upstream-style regression tests. Git's `worktree` command is built into the main executable, so the package contains the complete runtime, including Git helpers, templates, Perl support and HTTPS transport, rather than a replacement subcommand. Documentation generation, translations, Tcl/Tk tools and Rust components are omitted.

## Install through dotfiles

The shared `base` set selects `git-worktree-hooks` by default. From the normal dotfiles checkout, run:

```sh
make plan
make install
rehash
git --version
```

On a fresh installation, the installer downloads the pinned platform archive and checksum from the [versioned package release](https://github.com/lanej/dotfiles/releases/tag/git-worktree-hooks-2.56.0.1). It verifies the checksum, safely extracts the complete runtime into `~/.local/opt/git-worktree-hooks/2.56.0.worktree-hooks.1`, checks its version, relocation, and HTTPS helper compatibility, and atomically activates `~/.local/bin/git` through a launcher that preserves runtime relocation. Later installations validate and reuse that runtime without downloading or compiling Git again. An existing user-managed Git executable or symlink is retained with an error. System Git remains available at its original path.

Packages cover Apple Silicon and Intel macOS, and ARM64 and x86_64 Linux. Rocky Linux, RHEL, AlmaLinux, CentOS and Oracle Linux version 8 machines select separate `linux-el8` packages built on Rocky Linux 8 with its glibc and transport libraries. Other Linux machines select the existing Ubuntu 22.04 packages. These packages require compatible system libraries; they are not universal static binaries. macOS packages target macOS 15 and later compatible systems. Runtime library dependencies are recorded in `share/doc/git-worktree-hooks/libraries.txt`; macOS builds reject dependencies on Homebrew or MacPorts library paths. An unavailable or incompatible package fails clearly rather than silently selecting another Git.

To keep standard Git on a machine, add this to its existing `[tools]` table:

```toml
[tools]
git-worktree-hooks = false
```

Disabling the tool stops future installation and does not uninstall an active runtime. To return to system Git, remove `~/.local/bin/git` only after confirming it is the installer-owned symlink into `~/.local/opt/git-worktree-hooks/`, then refresh the shell's command cache.

`make base` links configuration without installing or downloading Git. `make install` performs the runtime installation. Shared Git configuration enables [global worktree tracking](git-worktree-policy.md#global-tracking) through named hooks; no repository hook installation is needed. Existing untouched repositories require an explicit `git-worktree-policy refresh` to seed the registry. Limits remain optional and disabled by default.

For an offline or custom package, keep the `.tar.gz` archive and adjacent `.tar.gz.sha256` file together and supply the archive explicitly:

```sh
DOTFILES_GIT_WORKTREE_HOOKS_ARCHIVE=/absolute/path/to/package.tar.gz make install
```

For a focused installation without the rest of the selected tools, run `python3 scripts/install-git-worktree-hooks.py`, optionally with `--archive /absolute/path/to/package.tar.gz`, followed by `make shell`.

## Build and publish packages

The build script requires Python 3.11+, a C toolchain, Make, Git, Perl, curl, tar with xz support, and development libraries for zlib, libcurl and expat. macOS uses its command line developer tools and SDK libraries. On Ubuntu, install `build-essential libcurl4-openssl-dev libexpat1-dev zlib1g-dev`. The script downloads the canonical kernel.org Git 2.56.0 archive and checks its pinned SHA256 before applying the checked-in patches.

```sh
scripts/build-git-worktree-hooks.sh /tmp/git-hook-packages
```

The script runs the upstream worktree and hook suites, stages a runtime, exercises the installed runtime from its temporary location, then writes a platform archive and checksum. Set `JOBS=8` to change the default four parallel build jobs. Source, build and test directories are removed on completion or failure. An existing output archive is retained rather than overwritten.

The build script and installer share the package naming rule: Enterprise Linux 8 builds produce `git-2.56.0-worktree-hooks-linux-el8-<architecture>.tar.gz`, and other platforms keep their existing names. On Rocky Linux, the library build prerequisites are `libcurl-devel expat-devel zlib-devel`. You can still supply a custom native archive through `DOTFILES_GIT_WORKTREE_HOOKS_ARCHIVE`; existing archives with the generic Linux name remain accepted on Enterprise Linux 8. Later ordinary `make install` runs reuse an installed compatible runtime without downloading another package.

The [build workflow](../.github/workflows/git-worktree-hooks.yml) builds and tests macOS and Ubuntu packages plus both Enterprise Linux 8 architectures in Rocky Linux 8 containers. Publish the additional `linux-el8` archives and checksums alongside the existing assets in the pinned release before deploying the installer change. Existing installed runtimes remain reusable. To upgrade Git itself, build the new catalog and patches, publish the tested archives and checksums in a versioned GitHub release, and pin that release's URL and runtime version in `bootstrap/tools.toml` before enabling the upgrade for fresh installations. Published package assets should be retained unchanged; use a new runtime version and release for changed builds. The workflow does not publish releases automatically.

The installer keeps sibling `libexec`, `share`, and library directories together: runtime relocation depends on that layout. The package records the exact source URL, checksum, build options and applied patch checksums alongside copies of the patches in `share/doc/git-worktree-hooks/`.

## Hook contract

Both hooks receive exactly four arguments:

```text
<event> <worktree-id> <old-absolute-path> <new-absolute-path>
```

Events are `add`, `move`, and `remove`. Inapplicable paths are empty arguments. Pruning emits `remove` for each removed administrative entry; its old path can be empty if the registration cannot supply one. Dry-run pruning invokes neither hook. Hooks run in the invoking repository, not in the affected checkout. Clear Git's local repository environment variables before using Git inside another checkout.

`pre-worktree` runs before mutation. A nonzero result rejects the operation even with `--force`. Its `add` identifier is empty because Git has not allocated the administrative entry. Rejected creation does not create or reset a branch, including with `add -B`. Rejected move or removal retains the existing checkout and registration; rejected prune entries are retained while pruning continues for other entries. Acceptance does not guarantee eventual success and does not reserve capacity.

`post-worktree` runs after successful mutation, including creation with `--no-checkout` or `--orphan`. It runs after `post-checkout` even if that hook fails. A nonzero result reports failure but leaves the completed operation in place; callers must reconcile actual state rather than assume rollback. A failing `post-checkout` takes precedence over the post-worktree status.

Hooks do not serialize concurrent commands. Two requests can both pass a capacity check before either creates a checkout. A sequential request sees updated usage, but a small simultaneous overshoot remains possible and is accepted for this policy. Hook configuration can also disable these checks.

See [worktree policy](git-worktree-policy.md) for global inventory, optional per-repository and global count/disk budgets, Treehouse integration, and the stock Git `post-checkout` fallback. That fallback misses `--no-checkout` creation and removal/move/prune events and cannot veto creation; explicit reconciliation keeps those worktrees discoverable.
