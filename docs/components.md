# Components

Worktree cleanup and agent launchers own their source, installation mappings, and focused tests under `components/`. Component dependencies describe both the repository inputs available during tests and the consumers selected when those inputs change. Other features retain their existing workflows during this pilot.

## Install and test

`make shell` still links the commands selected by the existing shell configuration. It reads the generated `config/components-install.tsv` through Bash, so basic setup does not require Python. Command names and the development symlink model remain unchanged; the original `bin/` paths are compatibility symlinks. Component installation mappings are relative to the installation home, without shell expansion.

```sh
python3 scripts/components.py validate
python3 scripts/components.py generate # after editing installation mappings
python3 scripts/components.py test worktree-cleanup
python3 scripts/components.py test agent-launchers --suite exit-hook
make test-components
```

The existing `make test-git-worktree-cleanup`, `make test-agent-treehouse`, `make test-codex-worktree-exit`, and `make test-codex-cleanup` entrypoints call the component runner. `make test-components-all` runs both components. The runner requires Python 3.11+, uv, and the native tools declared in each manifest. CI uses `scripts/install-treehouse` to build the pinned fork with self-updates disabled; runtime acquisition remains the responsibility of bootstrap and the tool catalog.

Each test run copies its declared repository inputs into a temporary source tree, installs them into a temporary home using the real Bash installer, and invokes installed commands. The runner prepares the pinned launcher Python environment from its checked-in uv lockfile before entering isolation. Native Git, lsof, processes, Unix sockets, and Treehouse remain real; agent executables and provider responses remain controlled fixtures.

## Declare ownership

Every file below `components/<name>/` belongs to that component. Its version 1 `component.toml` declares `dependencies`, `legacy_inputs`, `platforms`, `tools`, `install`, and named `suites`. Platforms are `linux` and `darwin`; suites are argument arrays run from the component directory. Python suites use a component-local `pyproject.toml` and `uv.lock`. POSIX system utilities are part of the host runtime; manifests name additional tools required by the feature.

Installation destinations must be unique, including parent/child conflicts. Paths must remain relative and cannot contain traversal or control characters. Relative source symlinks may reach another component only through a declared dependency. In particular, the launcher's sibling cleanup link is validated against its dependency on worktree cleanup. Directory symlinks and legacy inputs reached through symlinks are rejected.

New component files inherit selection automatically. A declared legacy input is an exact regular-file path; `sh/alias` remains a temporary launcher input while shell ownership is unmigrated. Validate and regenerate the installation table after changing mappings; CI rejects drift.

## Select affected tests

```sh
base=$(git merge-base origin/master HEAD)
python3 scripts/components.py plan --base "$base" --head HEAD
python3 scripts/components.py plan --base "$base" --head HEAD --json
```

Selection compares committed revisions. It includes owners of changed paths and their transitive dependents, consulting both revisions to preserve deleted files, renames, and removed dependency edges. Changes to compatibility command paths map to their component. Unclassified legacy paths select both pilot components. Runner, sandbox, installation, and workflow changes also select both. Working-tree validation and explicit component tests include new files before they are committed.

The component workflow runs on every pull request, selects from its merge-base comparison, and explains selection in the job summary. Master pushes and manual runs execute both components. The stable `Components` result requires successful validation and all selected platform jobs; branch protection is configured separately. Remaining workflows retain their own feature selection, including updated consumers of migrated code.

## Enforcement and limits

Linux requires Bubblewrap with working user and mount namespaces. macOS requires `sandbox-exec`; nested agent sandboxes may require running the detector through an approved native shell. The runner fails when isolation is unavailable. Every run verifies allowed staged reads in parent and child processes, rejected direct and symlinked reads of original checkout inputs, and rejected writes to staged inputs and the sandbox policy.

System runtime paths are readable, while source checkouts and their Git metadata are excluded. Network access is disabled; Unix sockets remain available. Writes are limited to the temporary execution tree, the normal uv cache, and device interfaces. On macOS, directory traversal and mounted-filesystem metadata are available for the loader and native lsof inspection. A disposable copy of set-id system tools has its privilege bits removed and is ad-hoc signed so native process inspection can run without privilege escalation.

This establishes repository-input selection relative to the enforced boundary. It does not establish fully hermetic toolchains, compatibility with every host, or the sensitivity of every behavioral detector. The controlled selection and installation cases protect the mapping; existing behavioral detectors protect their own outcomes. A sandbox probe cannot substitute for the actual Linux and macOS suites.

Successful runs remove their temporary tree and newly created script environments, retaining shared package downloads. Failed runs report the retained diagnostic directory, including the staged source, sanitized environment, and sandbox profile. CI also uploads those diagnostics. Remove retained task directories and their recorded script environments after investigation; do not prune other runs' caches.
