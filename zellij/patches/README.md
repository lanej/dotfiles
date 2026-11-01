# Native Zellij fixes

These patches apply to upstream Zellij `main` at [`bf517077`](https://github.com/zellij-org/zellij/commit/bf517077c848d91f75091f66d1996cfeb84f4732), which includes OSC 7501 support. [`scripts/install-zellij`](../../scripts/install-zellij) verifies the source archive's SHA-256, applies the patches without changing the dependency lockfile, and installs the compiled executable atomically. The build retains that revision's bundled plugins, vendored curl, and web-server support. It uses optimized, stripped code without link-time optimization to bound build memory.

The former startup patch, `0001-preserve-starting-session.patch`, is already included upstream through [`81f56e1`](https://github.com/zellij-org/zellij/commit/81f56e1aed4e17b822af5cb382a8f524e35f3eae). Its existing session workflow detector remains. The two patches below still supply repairs absent from the pinned upstream revision.

| Patch | Behavior | Tracking |
| --- | --- | --- |
| `0002-scope-command-completion.patch` | Broadcast input-unblock events reach initialized terminal clients. Temporary CLI clients receive completion from their own request, so an unrelated pane closure cannot finish a query before its JSON arrives. | [dotfiles #121](https://github.com/lanej/dotfiles/issues/121) |
| `0003-flush-session-shutdown.patch` | Queue normal exits for all clients, then wait for their queued messages to reach the IPC streams before terminating the server. One shared 500 ms deadline bounds stalled clients; failed writes and flushes are reported. | [dotfiles #120](https://github.com/lanej/dotfiles/issues/120) |

The CLI correction removes the confirmed empty-reply failure that could abort Firstmate's required ownership check. It does not prove the initiating cause of the earlier untraced CI failure. Firstmate's source remains unchanged, and its existing workflow detector exercises worker launch and ownership.

Run `python3 scripts/install-zellij --test` for the focused native regressions and installation. The existing session workflow also forces a connection to close before the first client initializes, then exercises the configured popup and session controls. CI runs these checks and the other Zellij workflows on Linux and macOS.

The executable reports upstream's `0.46.0` and includes that revision's bundled plugins. `python3 scripts/install-zellij --check` verifies the recorded patch set and executable hash. Restart a running session server to load the fixes. Remove a patch when a pinned upstream release contains an equivalent repair and passes these same regressions; a newer version number alone does not establish that.
