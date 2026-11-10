# Git worktree lifecycle hooks

This development patch series adds worktree lifecycle notifications and a veto hook to Git 2.56.0. The interface is local and may change as upstream review progresses. No separate fork repository or published binary release is created by this change. The runtime reports `git version 2.56.0.worktree-hooks.1` and is built separately; building and downloading its package never replaces the machine's original Git.

`0001-post-worktree.patch` follows [GitGitGadget PR #2442](https://github.com/git/git/pull/2442), pinned to revision `e5855a14919a6ccc7ba0af7e2aa765245f91fccc`. `0002-pre-worktree.patch` adds the local veto interface and its upstream-style regression tests. Git's `worktree` command is built into the main executable, so the package contains the complete runtime, including Git helpers, templates, Perl support and HTTPS transport, rather than a replacement subcommand. Documentation generation, translations, Tcl/Tk tools and Rust components are omitted.

## Install through dotfiles

The optional `git-worktree-hooks` tool installs a prebuilt package and links its complete runtime into `~/.local/bin/git`. Add the key to the existing `[tools]` table in this machine's `~/.config/dotfiles/config.toml`:

```toml
[tools]
git-worktree-hooks = true
```

Open the [Git worktree hooks workflow](https://github.com/lanej/dotfiles/actions/workflows/git-worktree-hooks.yml), choose a successful run for the version you want, and download its platform artifact. Choose `git-worktree-hooks-macOS-ARM64` for Apple Silicon or `git-worktree-hooks-Linux-X64` for Linux x86_64. Extract the downloaded artifact ZIP to obtain the `.tar.gz` archive and its adjacent `.tar.gz.sha256` file; keep both together. Other platforms require a compatible package built with the script below.

Then run from the normal dotfiles checkout, substituting your extracted archive path:

```sh
make plan
DOTFILES_GIT_WORKTREE_HOOKS_ARCHIVE=/absolute/path/to/git-2.56.0-worktree-hooks-darwin-arm64.tar.gz make install
rehash
git --version
```

The archive path is supplied for the first installation rather than saved in machine configuration. Later `make install` runs reuse and validate that same installed runtime without requiring the archive again. Installation verifies the checksum, safely extracts the complete runtime into `~/.local/opt/git-worktree-hooks/2.56.0.worktree-hooks.1`, checks its version, and atomically activates the `~/.local/bin/git` symlink. An existing user-managed Git executable or symlink is retained with an error. The system Git remains available at its original path. Missing packages on a fresh machine fail clearly; installation never falls back to compiling Git on each machine. The current workflow produces downloadable build artifacts; these changes have not published a binary release.

For a focused installation without installing the rest of this machine's selected tools, use the same installer directly:

```sh
python3 scripts/install-git-worktree-hooks.py --archive /absolute/path/to/package.tar.gz
make shell
```

Default `make` still applies configuration without installing software. No existing tool set enables this patched runtime automatically. Disable the machine's tool selection to stop future installation; that does not uninstall an already active runtime. To return to system Git, remove `~/.local/bin/git` only after confirming it is the installer-owned symlink into `~/.local/opt/git-worktree-hooks/`, then refresh the shell's command cache.

Register each repository explicitly with `git-worktree-policy install`; see [policy configuration](git-worktree-policy.md) for optional repository and global budgets. Installing the runtime does not install repository hooks or choose limits.

## Build packages

The build script requires Python 3.11+, a C toolchain, Make, Git, Perl, curl, tar with xz support, and development libraries for zlib, libcurl and expat. macOS uses its command line developer tools and SDK libraries. On Ubuntu, install `build-essential libcurl4-openssl-dev libexpat1-dev zlib1g-dev`. The script downloads the canonical kernel.org Git 2.56.0 archive and checks its pinned SHA256 before applying the checked-in patches.

```sh
scripts/build-git-worktree-hooks.sh /tmp/git-hook-packages
```

The script runs the upstream worktree and hook suites, stages a runtime, exercises the installed runtime from its temporary location, then writes a platform archive and checksum. Set `JOBS=8` to change the default four parallel build jobs. Source, build and test directories are removed on completion or failure. An existing output archive is retained rather than overwritten.

The [build workflow](../.github/workflows/git-worktree-hooks.yml) creates macOS ARM64 and Ubuntu x86_64 artifacts without publishing a release. Build once per supported OS and architecture; installing the artifact does not require compiling Git on each machine. Linux packages still depend on compatible system libraries and glibc; they are not universal static binaries. macOS packages target the runner's OS and later compatible systems. Runtime library dependencies are recorded in `share/doc/git-worktree-hooks/libraries.txt`; macOS builds reject dependencies on Homebrew or MacPorts library paths.

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
