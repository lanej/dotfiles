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

## Disabled Keybinds

The default resurrect keybinds (`prefix+Ctrl-s` to save, `prefix+Ctrl-r` to restore) are explicitly unbound:

```tmux
set -g @resurrect-save 'none'
set -g @resurrect-restore 'none'
```

Use `tmux-sessions save` and `tmux-sessions restore` instead. The keybinds were too easy to fat-finger and are superseded by the event-driven save hooks anyway.
