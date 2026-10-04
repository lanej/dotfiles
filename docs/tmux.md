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

<a id="claude-window-status"></a>

## Claude and Codex window status

Each window tab reports what the Claude or Codex session in it is doing. The
point is triage across a wall of windows: a window that **needs you** should be
impossible to miss, one that is working should be visible without pulling your
eye, and one that has been sitting untouched should say so rather than looking
the same as a window an agent just finished in.

`bin/tmux-claude-state` owns the shared palette, so `rc/tmux.conf` branches on
"is there a state" and reads the colours back out of window options. Adding a
state costs one row in `STATES`, not three more nested ternaries per segment.
The existing `@claude-*` option names are shared by both clients, keeping
running tmux servers and Claude hooks compatible.

Run `make tmux-status-legend` for coloured sample window titles: focused,
zoomed, plain inactive, bell/activity fallbacks, and every agent state. It
renders the current `rc/tmux.conf` formats on a temporary tmux server and uses
the shared palette, so the legend follows configuration changes.

| State | Class | Glyph | Colour | Means |
| --- | --- | --- | --- | --- |
| `approval` | need | ▲ | Nord11 red, bold | Blocked on a permission prompt |
| `question` | need | `?` | Nord11 red, bold | Blocked on something it asked you |
| `plan` | need | ▣ | Nord12 orange, bold | A plan is up for approval |
| `tool` | activity | ● | Nord13 yellow | A tool is running |
| `thinking` | activity | ◐ | Nord8 cyan | The agent has the turn, nothing running yet |
| `idle` | quiet | ○ | Nord3 grey | Finished, still warm |
| `dormant` | quiet | · | Nord1, dimmed | Finished and untouched for an hour |
| _(unset)_ | — | — | default | No agent session in this window |

The glyph means the state survives a colourless terminal or a screenshot, and
the three need-states stay apart from each other even though they share a
colour.

The agent's state outranks tmux's own bell and activity flags, because it says
*why* the window wants you, which a flag cannot. Windows with no agent session
fall back to those flags exactly as before.

### Claude hooks

| Event | Hook | Writes |
| --- | --- | --- |
| `UserPromptSubmit` | `claude-tmux-state-hook` | `thinking` |
| `PreToolUse` | `claude-tmux-state-hook` | `tool`, or `plan` for `ExitPlanMode` |
| `Notification` | `claude-notification-hook` | `approval` or `question`, by message |
| `Stop` | `claude-stop-hook` | `idle` |
| `SessionEnd` | `claude-tmux-state-hook` | _(cleared)_ |
| _select a `!`-prefixed window_ | `claude-clear-waiting` | `idle` |

`PostToolUse` is deliberately unwired: re-asserting a state between every tool
call would strobe the tab on a busy turn without saying anything new.

### Codex hooks

Run `make codex-tmux` to install just the tmux integration, or `make codex` as
part of the full Codex setup. `bin/sync-codex-tmux-hooks` merges
`codex/tmux-hooks.json` into `$CODEX_HOME/hooks.json` (normally
`~/.codex/hooks.json`). Existing handlers, including Paseo's, keep their
positions and definitions. Repeated installs do not add duplicate handlers or
rewrite an unchanged file.

Restart Codex and use `/hooks` to review and trust the new tmux handlers.
Codex skips new or changed non-managed hooks until their exact definitions are
trusted. Hooks must be enabled (`features.hooks`, enabled by default).
See the [Codex hooks documentation](https://developers.openai.com/codex/hooks/).

All handlers call `bin/codex-tmux-state-hook`, which reads JSON on stdin and
targets the originating `TMUX_PANE`. Outside tmux it does nothing.
The `codex` function in `sh/alias` adds `--no-daemon` inside tmux so the hooks
inherit that terminal's environment. Reload the shell after updating the
aliases; direct binary invocations inside tmux should also use `--no-daemon`.

| Event | Writes |
| --- | --- |
| `SessionStart` | `idle`; compaction preserves the current state |
| `UserPromptSubmit` | `thinking` |
| `PreToolUse` | `tool`, or `question` for `request_user_input` / `request_user_input_async` |
| `PermissionRequest` | `approval` |
| `PostToolUse` | `thinking` after the waiting tool returns; ordinary completions leave the tab steady |
| `Stop` | `idle`, or `plan` when `permission_mode` is `plan` |
| `Interrupt` | `idle` |
| `SessionEnd` | _(cleared)_ |

Questions, approval requests, and turn completion ring the originating pane's
bell. `SessionStart` records `@codex-session-id` on the pane so events from a
previous session cannot clear its replacement's status.

### Dormancy and the status-bar roll-up

tmux has no timer, so `bin/tmux-claude-sweep` rides the status refresh
(`status-interval`, 10s) from a `#()` in `status-right`. One process per
refresh regardless of window count, doing two jobs:

- `idle` → `dormant` once a window has sat untouched for `CLAUDE_DORMANT_AFTER`
  (default 3600s, originally chosen for Claude's prompt-cache window; Codex uses
  the same display threshold independently of its cache policy). The focused
  window is never dormant — you are the activity.
  Stale windows are marked, never moved or closed; `prefix+H` parks one in
  `later` by hand.
- `tool`/`thinking` → `dormant` after `CLAUDE_STALL_AFTER` (default 3600s). A
  window still claiming to work an hour on lost its `Stop` hook to a killed
  client or a crashed session; claiming it is busy is the one genuinely
  misleading state.

It also prints a cross-session roll-up into `status-right` — `▲2 ●1` — counting
needs and activity everywhere, because the need you most want surfaced is in a
window you are not looking at. Quiet states alone print nothing.

### Navigation

`prefix+C-a` (`bin/tmux-quickswitch-alert`) escalates: if any window needs you
it cycles only among those, otherwise among the busy ones. A window Claude
merely finished in is never a jump target — the quiet states are display, not
navigation. `prefix+C-f`'s fzf picker sorts needs to the top and labels each
window with its state.

### Known limitations

When Claude ends a turn by asking you something, `Stop` fires first and the tab
goes `idle`; Claude Code only emits the `Notification` that promotes it to
`question` after its own idle delay (~60s). The bell from
`claude-stop-bell-hook` covers that gap audibly. Permission prompts and plans
have no such delay — they fire mid-turn and light the tab immediately.

Codex's `PermissionRequest` runs before the approval decision. There is no
separate hook for acceptance, so the tab returns to activity when that tool
produces `PostToolUse` or another tool starts. A question written in a final
answer has no dedicated hook; only structured user-input tools mark
`question` immediately. Each window has one state, so use separate windows
for independently running agent sessions.

## Disabled Keybinds

The default resurrect keybinds (`prefix+Ctrl-s` to save, `prefix+Ctrl-r` to restore) are explicitly unbound:

```tmux
set -g @resurrect-save 'none'
set -g @resurrect-restore 'none'
```

Use `tmux-sessions save` and `tmux-sessions restore` instead. The keybinds were too easy to fat-finger and are superseded by the event-driven save hooks anyway.
