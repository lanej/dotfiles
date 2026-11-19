# Git worktree lifecycle hooks

This development patch series adds worktree lifecycle notifications and a veto hook to Git 2.56.0. The interface is local and may change as upstream review progresses. Fresh installation starts from the catalog tag; project updates select the latest stable upstream Git release and compile it locally with the checked-in patches. No custom Git release is required. The runtime reports `<upstream-version>.worktree-hooks.1` and is built separately; building its runtime never replaces the machine's original Git.

`0001-post-worktree.patch` follows [GitGitGadget PR #2442](https://github.com/git/git/pull/2442), pinned to revision `e5855a14919a6ccc7ba0af7e2aa765245f91fccc`. `0002-pre-worktree.patch` adds the local veto interface and its upstream-style regression tests. Git's `worktree` command is built into the main executable, so the package contains the complete runtime, including Git helpers, templates, Perl support and HTTPS transport, rather than a replacement subcommand. Documentation generation, translations, Tcl/Tk tools and Rust components are omitted.

## Install through dotfiles

The shared `base` set selects `git-worktree-hooks` by default. From the normal dotfiles checkout, run:

```sh
make plan
make install
rehash
git --version
```

On a fresh installation, the installer shallow clones `https://github.com/git/git.git` at the catalog's `v2.56.0` tag, applies the checked-in patches, compiles Git and runs the upstream worktree and hook suites. It stages and validates the complete runtime, then atomically activates `~/.local/bin/git` through a launcher that preserves runtime relocation. System Git remains at its original path. An existing user-managed Git executable or symlink is retained with an error.

Locally built runtimes live under `~/.local/opt/git-worktree-hooks/<runtime-version>-<source-fingerprint>`. The fingerprint covers the selected Git version and commit, builder, runtime helpers and patches; unchanged inputs reuse the installed runtime without cloning or compiling again. Changed inputs build into a new directory before activation, retaining the previous runtime. Builds use the local C toolchain and system libraries, including on Enterprise Linux 8; there is no published-platform-package dependency. Dotfiles installation provisions the build dependencies; direct installation and project updates require them already installed.

To keep standard Git on a machine, add this to its existing `[tools]` table:

```toml
[tools]
git-worktree-hooks = false
```

Disabling the tool stops future installation and does not uninstall an active runtime. To return to system Git, remove `~/.local/bin/git` only after confirming it is the installer-owned symlink into `~/.local/opt/git-worktree-hooks/`, then refresh the shell's command cache.

`make base` links configuration without installing or downloading Git. `make install` performs the runtime installation. The independent `worktree-policy` base tool installs a prebuilt native executable without a Python or Go runtime requirement. Shared Git configuration enables [global worktree tracking](git-worktree-policy.md#global-tracking) through named hooks; no repository hook installation is needed. Existing untouched repositories require an explicit `git-worktree-policy refresh` to seed the registry. Limits remain optional and disabled by default.

For an offline or custom package, keep the `.tar.gz` archive and adjacent `.tar.gz.sha256` file together and supply the archive explicitly:

```sh
DOTFILES_GIT_WORKTREE_HOOKS_ARCHIVE=/absolute/path/to/package.tar.gz make install
```

For a focused installation without the rest of the selected tools, run `bash scripts/install-git-worktree-hooks.sh`, optionally with `--archive /absolute/path/to/package.tar.gz`, followed by `make shell`.

## Update and build locally

```sh
project-update pull worktree-manager
project-update build worktree-manager
project-update restart worktree-manager
# Or run all three steps:
project-update update worktree-manager
```

The project entry pulls dotfiles' default branch, discovers the highest numeric `vMAJOR.MINOR.PATCH` tag from the upstream Git repository, and shallow clones it into a shared source cache. Release candidates are excluded. Build compiles that selected source with the checked-in patches, installs Git and the pinned worktree manager, then applies Git configuration. Build requires a preceding source pull and does not query a newer release implicitly. Both commands load their installed runtime on their next invocation; no service restart is required. The manager itself still uses its checksum-verified release executable.

The Git builder requires Python 3.11+, a C toolchain, Make, Git, Perl, tar, development libraries for zlib, libcurl and expat, and `bsdtar` for staged extraction. macOS uses its command line developer tools and SDK libraries. On Ubuntu, install `build-essential libcurl4-openssl-dev libexpat1-dev zlib1g-dev libarchive-tools`; on Rocky Linux, install `gcc make perl libcurl-devel expat-devel zlib-devel bsdtar`.

For a standalone build of the catalog baseline without activation, run:

```sh
scripts/build-git-worktree-hooks.sh /tmp/git-hook-build
```

Pass `--source /path/to/shallow-checkout` to build another stable tag without network access. Project pulls record their selected checkout in `${XDG_CACHE_HOME:-~/.cache}/dotfiles/git-worktree-hooks/selected-source`; later builds and ordinary installs reuse that source. A fresh machine without a selected source uses the catalog tag. Failed release discovery leaves the previous selection unchanged.

The Bash installer and CLI detector run external commands directly. Python remains for TOML parsing. The Bash extractor verifies an isolated archive snapshot, uses libarchive’s `bsdtar` protections, and rejects paths, links and special files that could escape staging. macOS supplies `bsdtar`; the selected Linux dependency installs it through the native package manager. The builder runs the upstream worktree and hook suites, stages a runtime and exercises relocation plus veto and notification behavior. Its archive and checksum are local staging artifacts, also accepted by the installer's `--archive` option; publishing them is unnecessary. Set `JOBS=8` to change the default four parallel build jobs. Temporary source, build and test directories are removed on completion or failure. Existing output archives are retained rather than overwritten.

The [build workflow](../.github/workflows/git-worktree-hooks.yml) checks macOS, Ubuntu and Enterprise Linux 8 builds from the catalog baseline. A project update advances Git independently of that baseline. If the local patches no longer apply to the latest stable release, the update fails before activation; adjust the patches and rerun it. The installed runtime retains its sibling helpers and templates plus the exact upstream tag, commit and patch checksums in `share/doc/git-worktree-hooks/`.

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
