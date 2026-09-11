# tmux Session Management

## Session Persistence

tmux-resurrect saves session state (windows, panes, layout, running commands) to `~/.tmux/resurrect/tmux_resurrect_*.txt`. Two mechanisms trigger saves:

- **tmux-continuum**: auto-saves every 15 minutes as a backstop
- **Event hooks** in `rc/tmux.conf`: saves fire immediately on structural changes — window/pane create or destroy, new session

Snapshots below 100 bytes captured no real state and are ignored by `tmux-sessions`.

The `last` symlink in `~/.tmux/resurrect/` points to the snapshot that will be used on the next restore.

## Claude Code Pane Restoration

Before each save, `@resurrect-hook-pre-save` runs `bin/tmux-resurrect-save-hook`, which reads the `@claude-session-id` pane user option from every pane and writes `~/.tmux/resurrect/claude-sessions.txt` — a tab-delimited map of working directory → session ID.

On restore, `bin/tmux-resurrect-claude` is the resurrect process strategy for Claude panes. It receives the pane's restored working directory, looks it up in `claude-sessions.txt`, and runs:

- `claude --resume <session_id>` — if a matching session ID exists
- `claude --continue` — otherwise

The `@resurrect-processes` config is `'"nvim ~claude"'` — resurrect restores nvim and any command matching `~claude` (the strategy script).

## `tmux-sessions`

```
tmux-sessions <subcommand> [arg]
```

| Subcommand | Behavior |
|---|---|
| `list` | Tabular listing of all non-degenerate snapshots, newest first. Current marked with `*`. Columns: `#`, `TIMESTAMP`, `SIZE`, `WINDOWS`, `PANES`. |
| `show [n\|file]` | Colorized window/pane tree of a snapshot. Default: current (`last` symlink). Pane types color-coded: green=claude, blue=nvim, yellow=claude-sub, gray=shell. |
| `save` | Trigger a save now (calls resurrect's `save.sh quiet`). |
| `restore [n\|file]` | Restore a snapshot. No arg: fzf picker with preview. Arg: 1-based index or filename. Always prompts before executing. Updates `last` symlink before restoring. |

Index numbers from `list` are valid arguments to `show` and `restore`.

## Idle Claude windows → `later` → closed

`bin/claude-tmux-later` moves idle Claude windows into the existing `later`
session after **one hour** and closes parked windows after **24 hours total
idle** (not another 24 hours after parking). It complements the manual
`prefix+H` binding. No requests are sent to Claude to maintain the timer.

`make claude` links `claude/tmux-later.json` to
`~/.config/claude-tmux-later/config.json`; `.claude/settings.json` wires the
lifecycle hooks alongside the existing naming and notification hooks. Start
new Claude processes, or exit and resume existing conversations, to enroll
them. Hooks start one detached monitor per tmux server, polling once a minute.
There is no separate installer, cron entry, or tmux configuration change.

| Setting | Default |
| --- | --- |
| `archive_seconds` | `3600` |
| `close_seconds` | `86400` |
| `poll_seconds` | `60` |
| `later_session` | `later` |
| `enabled` | `true` |
| `dry_run` | `false` |

The monitor reloads configuration each poll. Set `dry_run` to `true` to log
proposed operations without changing tmux; set `enabled` to `false` to stop
cleanup. Re-enabling takes effect when a new hook restarts the monitor.

Idle means the main agent has finished responding and has no known active
subagents, background work, or scheduled prompts. New prompts/tool activity
reset the clock and mark the session busy; a successful Stop begins a new idle
interval. Terminal repainting does not count as activity. Using a parked
conversation resets its timer but does not automatically move it back.

Safety rules:

- Every pane in the window must be an enrolled, idle Claude process. Shell,
  editor, and untracked panes prevent both moving and closing that window.
- Viewed, pinned, linked, dead, and copy-mode windows are left alone.
- Process ID, process start time, foreground process group, and terminal must
  match. Inherited `TMUX_PANE` alone cannot enroll claude-mem observers.
- Busy or uncertain states never expire into idle. An interrupted turn, API
  failure, or missing background-task fields protects the session until a
  subsequent successful turn or restart. Lost Stop events therefore retain
  windows instead of terminating potentially active work.
- Resume identifiers are recorded before `tmux kill-window`. This terminates
  the window, not a graceful `/exit`; it does not delete project files,
  transcripts, or worktrees. Normal persisted conversations remain resumable.

Inspect or pin the current window:

```sh
~/.files/bin/claude-tmux-later status
tmux set-option -w @claude_later_pin 1
tmux set-option -wu @claude_later_pin  # unpin
```

Resume via `claude --resume` from the project directory, or use the exact
session ID recorded in
`${XDG_STATE_HOME:-~/.local/state}/claude-tmux-later/*/history.jsonl`.
The log contains IDs, working directories, transcript paths, and action
outcomes, not prompt text. Existing `@claude-session-id` restore metadata is
left unchanged. The monitor exits when its tmux server exits; later hooks
restart it when needed.

Requires Python 3.9+, tmux, and a foreground native Claude process (including
`claude-wrapper`, which pins its argument-zero name). Node/npm installations,
SSH/container processes, and wrappers that retain the foreground process
group are not enrolled. A current Claude release must report both
`background_tasks` and `session_crons` in Stop hooks; absent fields are treated
as unknown rather than as empty. This is an idle policy, not a measurement of
the provider's prompt-cache lifetime, and does not change cache settings.

Tests: `make test` includes unit and isolated live-tmux tests. The latter use
an empty tmux config, a private socket, and disposable native test processes;
they never use the default server or call the Claude API. They skip if tmux
is unavailable locally; CI requires them on Linux and macOS.

## Disabled Keybinds

The default resurrect keybinds (`prefix+Ctrl-s` to save, `prefix+Ctrl-r` to restore) are explicitly unbound:

```tmux
set -g @resurrect-save 'none'
set -g @resurrect-restore 'none'
```

Use `tmux-sessions save` and `tmux-sessions restore` instead. The keybinds were too easy to fat-finger and are superseded by the event-driven save hooks anyway.
