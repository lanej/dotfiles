# Native worktree policy

This standalone Go command implements [global worktree tracking and optional admission budgets](../../docs/git-worktree-policy.md). Target machines need Git and the prebuilt executable; neither Go nor Python is required to run it. The policy does not depend on Treehouse or a patched Git binary. Patched Git provides automatic veto delivery; stock Git provides checkout observation and explicit preflight.

## Contracts

The CLI, canonical common-Git-directory identity, SHA256 registry filenames, and JSON layout remain compatible with the earlier Python command. Paths preserve raw filesystem bytes through Python-compatible JSON surrogate escapes; budgets preserve arbitrary-size integers. Inventory comes from Git rather than event counters. Repository subprocesses clear inherited local Git environment variables before targeting another repository.

The common Git directory owns local inventory and compatibility dispatchers. The machine-local state directory owns the repository registry and optional global budgets. Named Git hooks call `observe`, which never chains existing hooks; compatibility dispatchers call `hook`, which preserves saved originals. Notifications warn without rejecting checkout, while an unevaluable admission budget fails closed. Concurrent additions can overshoot because a preflight does not reserve capacity.

## Build and verify

Use the Go version in `go.mod` and Python 3.11+ for the existing build/test tooling:

```sh
scripts/build-worktree-policy.sh /tmp/policy-packages
bash tools/worktree-policy/scripts/check-go.sh
python3 scripts/test-install-worktree-policy.py --binary /tmp/policy-packages/git-worktree-policy
make test-git-worktree-policy
```

`CGO_ENABLED=0` produces a native executable with no C library dependency on Linux. The build writes `git-worktree-policy-<darwin|linux>-<arm64|amd64>` and an adjacent SHA256 file. The generic symlink is a development convenience, not a release asset. Quality checks use the committed portable Go profile, including race tests and vulnerability scanning.

## Release

The [native workflow](../../.github/workflows/worktree-policy.yml) builds and tests all four platform packages and uploads binaries and checksums as artifacts. Publish those verified artifacts in `git-worktree-policy-vVERSION` before merging a new default catalog version. The version comes from `bootstrap/tools.toml` and is embedded in the executable. Retain published assets unchanged; use a new version for changed builds. The workflow does not publish automatically.

The installer verifies checksums, platform execution and version before activation, refuses unmanaged or modified destinations, and records the installed digest for reuse and future upgrades. It can consume an explicit local executable plus adjacent checksum through `DOTFILES_WORKTREE_POLICY_BINARY`.
