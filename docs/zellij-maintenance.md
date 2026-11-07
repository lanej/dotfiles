# Zellij maintenance reference

This repository-only guide covers installation, implementation boundaries, and verification. Daily usage lives in the [Zellij overview](zellij.md), [keybinding map](zellij-keybinds.mdx), and feature guides under `docs/zellij/`. This document is not published by the documentation website.

## Runtime and configuration

The selected runtime recipe is defined in [the tool catalog](../bootstrap/tools.toml); its patched revision and native build settings live in [the runtime installer](../scripts/install-zellij). The patched runtime carries the CLI completion, shutdown flush, initial-client registration, and concurrent permission-cache fixes needed by the supported workflows. Upstream release and main selections do not imply those fixes are present.

Native builds use Rust 1.95.0 and revision-isolated artifacts under `${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/zellij/target/<revision>`. The installation stamp sits beside the managed executable rather than in the restorable cache. The first build from a revision's isolated cache replaces stale binaries; subsequent verified installs can reuse Cargo's ownership checks.

```sh
make config
make zellij-runtime zellij
make zellij-status zellij
```

Runtime installation and configuration are separate operations. Configuration alone does not compile or provision software. Without a compatible runtime and built status artifact, `make zellij` selects the legacy configuration. A prebuilt bar can be supplied with `ZELLIJ_STATUS_WASM=/absolute/path/lane-status.wasm`.

Restart existing session servers after changing the runtime or loaded plugins. Replacing an executable or WASM file does not update a running instance. Keep `$HOME/.local/bin` ahead of package-manager binaries. Preserve malformed permission caches for diagnosis rather than replacing them silently.

## Feature ownership

The [status plugin](../zellij/status/src/main.rs) renders the top bar, observes native attention, and coordinates client-specific helpers. Its background receiver routes paste and attention bindings to the invoking client. The [navigation plugin](../zellij/navigation/README.md) owns bare pane-navigation keys. The [command-prompt plugin](../zellij/command-prompt/README.md) owns private prompt, command-history, and new-session routing.

Native Zellij owns current attention, including detached sessions. The [notification helper](../bin/zellij-notify) owns bounded history and reads source viewports only after validating their server and pane-process identities; it checks again before displaying a captured viewport. Its history is not an event-time screen recording and cannot reconstruct all intermediate transitions while every source client is detached.

The [clipboard helper](../bin/zellij-clipboard) keeps the Neovim session buffer separate from terminal clipboard writes. OSC 52 copying has no terminal acceptance acknowledgement. Local buffer checks do not establish acceptance by a particular terminal or SSH transport.

The [picker](../bin/zellij-picker) preserves live panes when moving or swapping. These operations are sequential, not atomic. Their stale-client checks do not make concurrent moves transactional; partial changes require inspection rather than automatic rollback. The [balance helper](../bin/zellij-balance) uses native resize steps rather than loading replacement layouts that could create new shells.

## Forwarded-agent and session safety

The attach workflow maintains owner-only session-specific SSH-agent links keyed by persistent native session identity. Renaming or reusing a display name does not retarget an existing session. The shared popup follows its selected outer session's managed link; arbitrary symlinks, follower chains, self-reference, and loops are rejected. Raw agent sockets remain the ordinary session-refresh input.

Recovery identifies the target session's server through a short unfocused native command. It needs no Python or SQLite client at runtime. Failure falls back to ordinary attachment with the incoming socket rather than blocking attachment. No private key material is copied.

Shutdown validates the owning Unix socket again before ending a session. The client-detach chooser uses fresh attachment identities and receiver ownership, rejecting observed stale selections rather than falling back to detaching every other viewer.

## Verification

Choose checks for the affected feature, following [the verification guide](verification.md). The existing entrypoints include:

```sh
zellij setup --check
make test-zellij
make test-zellij-notifications
make test-zellij-notifications-ui
make test-zellij-status
make test-zellij-codex-titles
make test-zellij-claude-titles
make test-zellij-navigation
make test-zellij-layout
make test-zellij-sessions
make test-zellij-auto-title
make test-zellij-tab-labels
make test-zellij-command-prompt
make test-zellij-session-keys
```

The real-terminal detectors install into private temporary homes and sessions. They exercise configured prefix keys, preserve process and scrollback identity, and clean up only their own sessions. Some checks require Neovim, fzf, Rust, or installed navigation artifacts. Runtime installation has its own cache and upstream-download boundary; orchestration tests do not establish live release availability.

Run `make test-ssh-agent` for local-agent, tmux, and attachment-failure checks and `python3 scripts/test-zellij-agent-update.py` for pinned-runtime reconnects, popup survival, and unsafe-source rejection. These use real temporary agents but do not open a real SSH connection or authenticate against 1Password.

The notification detector validates fixed-width wide and narrow layouts and colored source previews. A previous live-resize check disrupted input; whether that came from the runtime or the test harness remains unresolved. Do not treat fixed-width checks as proof of live-resize behavior.

Agent lifecycle fixtures verify configured title updates, ownership, and restoration without running a live Claude or Codex model task. Likewise, mock/native buffer checks do not establish system-clipboard acceptance in a user's terminal.
