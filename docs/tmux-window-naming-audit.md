# Tmux Window Naming Audit

**Date:** 2026-06-01  
**Scope:** Investigation of intermittent window naming bug where window 2 steals window 1's name

## Executive Summary

Tmux windows are intermittently being named incorrectly with a specific directional pattern: **window 2 receives window 1's name instead of its own**. The bug is not program-specific, not timing-sensitive to rapid window creation, and occurs unpredictably.

**Root cause hypothesis:** The bug is caused by **incorrect window targeting in worktree hooks** (`bin/claude-worktree-create-hook:29` and `bin/claude-worktree-remove-hook:13`) which call `tmux rename-window` without the `-t` argument. This causes the command to rename the **current** window instead of the window associated with `TMUX_PANE`, leading to window 1 being renamed when the hook fires for window 2.

**Secondary factor:** Race condition between vim-prosession plugin and Claude hooks, both attempting to name windows simultaneously on session startup.

**Affected code:**
- `bin/claude-worktree-create-hook` (line 29)
- `bin/claude-worktree-remove-hook` (line 13)
- `nvim/init.lua` (lines 1819-1832, vim-prosession configuration)

## Mechanism Inventory

Ten distinct code paths control tmux window names across three systems: Claude hooks (7), tmux configuration (2), and neovim (1).

| Mechanism | File:Line | Trigger | Targeting Method | Commands | Reads/Writes |
|-----------|-----------|---------|------------------|----------|--------------|
| **SessionStart Hook** | `bin/claude-session-start-hook:24-27,81-82` | Claude SessionStart event (startup/clear/compact/resume) | `-t $pane` from `TMUX_PANE` env var | `rename-window`, `set-option -w @claude_named`, `set-option -w allow-rename off`, `set-option -p @claude-session-id` | Writes name, reads from cache |
| **Stop Hook** | `bin/claude-autoname-hook:35-39` | Claude Stop event | `-t $pane` from `TMUX_PANE` env var (or implicit fallback) | `rename-window`, `set-option -w @claude_named` | Writes name from CWD |
| **Notification Hook** | `bin/claude-notification-hook:41,47` | Claude Notification event (waiting for input) | `-t "$TMUX_PANE"` | `rename-window` (adds `!` prefix), `set-option -w @claude-state "waiting"` | Reads current name, writes prefixed version |
| **Clear Waiting** | `bin/claude-clear-waiting:6-7` | tmux `after-select-window` hook (when window name matches `^!`) | `-t "$window_id"` from arg 1 | `set-option -w @claude-state ""`, `rename-window` (removes `!` prefix) | Reads name from arg, writes stripped version |
| **Worktree Create** ⚠️ | `bin/claude-worktree-create-hook:29` | Claude WorktreeCreate event | **Implicit current window** (NO `-t`) | `rename-window "$name"` | Writes branch name |
| **Worktree Remove** ⚠️ | `bin/claude-worktree-remove-hook:13,17` | Claude WorktreeRemove event | **Implicit current window** (NO `-t`) | `rename-window "$name"`, `set-window-option automatic-rename on` | Writes repo name |
| **Tool Start Hook** | `bin/claude-tool-start-hook:21` | Claude PreToolUse event | `-t $pane` from `TMUX_PANE` env var | `set-option -w @claude-state "tool"` | Writes state only (NO rename) |
| **after-select-window Hook** | `rc/tmux.conf:227` | tmux native hook (when selecting window) | Conditional on window name regex `^!` | Calls `bin/claude-clear-waiting` script | Indirect via script |
| **automatic-rename Disable** | `rc/tmux.conf:76` | Global tmux config | Global setting | `setw -g automatic-rename off` | N/A (blocks tmux shell renaming) |
| **vim-prosession Plugin** | `nvim/init.lua:1819-1832` | Neovim VimEnter or session load/switch | **Plugin-internal** (unknown targeting) | Plugin calls `tmux rename-window` internally | Writes session-based name |

### Hook Execution Order

When a Claude session starts in a new window:
1. **SessionStart Hook** fires first → sets name to `{repo}_{branch}` or `{directory}`
2. **vim-prosession** (if neovim loads) → may rename based on vim session (race condition)
3. **Worktree hooks** (if worktree operations occur) → may rename wrong window ⚠️
4. **Notification Hook** (when Claude waits) → adds `!` prefix
5. **Clear Waiting** (when user switches to window) → removes `!` prefix
6. **Stop Hook** (when Claude stops) → updates name to current CWD

## Current Naming Resolution Logic

The canonical window name format is `<directory/repository> (<branch>)`, but the current implementation uses `{repo}_{branch}` or `{directory}`.

### Source Code: `bin/claude-session-start-hook` (lines 41-52)

```bash
git_window_name() {
    local repo_name branch_name
    
    # Get repository name from git toplevel
    repo_name=$(git rev-parse --show-toplevel 2>/dev/null | xargs basename)
    
    if [[ -n "$repo_name" ]]; then
        # Get current branch name
        branch_name=$(git symbolic-ref --short HEAD 2>/dev/null || git branch --show-current 2>/dev/null)
        
        # Format: {repo}_{branch} or just {repo} if branch unavailable
        echo "${repo_name}${branch_name:+_$branch_name}"
    else
        # Fallback: directory basename if not in git repo
        basename "$PWD"
    fi
}
```

### Resolution Logic

1. **In git repository:**
   - Run `git rev-parse --show-toplevel | xargs basename` → repo name
   - Run `git symbolic-ref --short HEAD` or `git branch --show-current` → branch name
   - Format: `{repo_name}_{branch_name}` (e.g., `api_main`, `easypost_feature/auth`)
   - If branch unavailable: `{repo_name}` only

2. **Not in git repository:**
   - Run `basename "$PWD"` → directory name
   - Format: `{directory_name}` (e.g., `Documents`, `.files`)

### Example Outputs

| Working Directory | Git Status | Window Name |
|-------------------|------------|-------------|
| `/Users/josh/.files` | Git repo on `master` | `.files_master` |
| `/Users/josh/src/api` | Git repo on `feature/auth` | `api_feature/auth` |
| `/Users/josh/src/easypost` | Git repo, detached HEAD | `easypost` |
| `/Users/josh/Documents` | Not a git repo | `Documents` |
| `/tmp` | Not a git repo | `tmp` |

### Discrepancy with Intended Format

**Intended:** `<directory/repository> (<branch>)` (e.g., `.files (master)`)  
**Actual:** `{repo}_{branch}` (e.g., `.files_master`)

The current implementation uses underscore separator instead of parentheses and omits the parentheses entirely for non-git directories.

## Race Condition Analysis

### Primary Culprit: Worktree Hooks Missing `-t` Argument

**Affected Files:**
- `bin/claude-worktree-create-hook:29`
- `bin/claude-worktree-remove-hook:13`

**Buggy Code:**
```bash
# claude-worktree-create-hook (line 29)
tmux rename-window "$name"  # NO -t argument

# claude-worktree-remove-hook (line 13)
tmux rename-window "$name"  # NO -t argument
```

**Correct Pattern (from other hooks):**
```bash
# claude-session-start-hook (line 24)
tmux rename-window -t $pane $name  # WITH -t argument targeting specific window

# claude-autoname-hook (line 35)
tmux rename-window -t $pane $name  # WITH -t argument
```

### Why Window 2 Steals Window 1's Name

**Failure Sequence:**

1. **Time 0:** Window 1 opens, Claude SessionStart hook fires
   - `TMUX_PANE` points to window 1
   - SessionStart hook runs: `tmux rename-window -t $pane "{window1_name}"`
   - Window 1 correctly named

2. **Time 1:** Window 2 opens (e.g., neovim loads, Claude starts)
   - User's focus is still on window 1 (current window = window 1)
   - `TMUX_PANE` in window 2's process points to window 2

3. **Time 2:** Worktree hook fires for window 2
   - Hook runs in window 2's context: `TMUX_PANE` = window 2's pane ID
   - But hook calls: `tmux rename-window "{window2_name}"` (NO `-t`)
   - **tmux renames the CURRENT window**, not the window from `TMUX_PANE`
   - Current window = window 1
   - **Window 1 is renamed to `{window2_name}`**

4. **Time 3:** Later, window 2 gets named correctly by another hook
   - Window 2 now has correct name
   - But window 1 still has window 2's name

**Result:** Window 2 "stole" window 1's name (window 1 has window 2's name, window 2 has correct name)

### Timing Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User focused on Window 1                                        │
│ (tmux "current window" = window 1)                             │
└─────────────────────────────────────────────────────────────────┘

Window 1                          Window 2
(Claude session)                  (neovim or new Claude session)
─────────────────────────────────────────────────────────────────

[SessionStart fires]
TMUX_PANE → window 1
tmux rename-window -t $pane "proj_main"
✅ Window 1 named "proj_main"

                                  [Window 2 created]
                                  TMUX_PANE → window 2
                                  
                                  [Worktree hook fires]
                                  TMUX_PANE → window 2
                                  tmux rename-window "docs"  ❌ NO -t
                                  
⚠️ Window 1 renamed to "docs"    
(because window 1 is current!)

                                  [Later: SessionStart for window 2]
                                  tmux rename-window -t $pane "docs"
                                  ✅ Window 2 named "docs"

FINAL STATE:
Window 1: "docs" (WRONG)
Window 2: "docs" (CORRECT)
```

### Evidence Supporting Hypothesis

| Observation | Explanation |
|-------------|-------------|
| ✅ Directional pattern (window 2 → window 1, not random swap) | Worktree hook fires for window 2 but renames current window (window 1) |
| ✅ Intermittent (not always reproducible) | Depends on which window is current when hook fires; if user has switched to window 2, it works correctly |
| ✅ Not program-specific (any window can be involved) | Hook fires regardless of window contents; bug is in window targeting, not program detection |
| ✅ Not rapid-creation-related (not timing-sensitive to user actions) | Bug is triggered by hook execution, not by how fast windows are created |
| ✅ Window 1's fate varies (no consistent pattern) | Depends on which hook fires last; could be worktree hook, SessionStart, or Stop |

### Secondary Race: vim-prosession vs Claude Hooks

**Conflict:**
- **vim-prosession** plugin calls `tmux rename-window` when neovim loads or sessions switch
- **Claude SessionStart hook** calls `tmux rename-window -t $pane` when Claude starts
- Both may fire simultaneously when neovim window opens with Claude

**Race Outcome:** Last hook to execute wins (overwrites previous name)

**Observed Behavior:**
- If vim-prosession fires last → window named with vim session name (format `@@@` from config)
- If Claude hook fires last → window named with `{repo}_{branch}` format
- If vim-prosession has stale window ID mapping → could rename wrong window

**Evidence:**
- `nvim/init.lua:1831` sets `prosession_tmux_title_format = "@@@"` (custom format, not matching Claude's format)
- No explicit window targeting visible in lua config (plugin internals handle tmux commands)

### Reproduction Pattern

**Not deterministically reproducible**, but occurs when:
- Multiple windows exist
- Worktree hook fires (WorktreeCreate or WorktreeRemove event)
- User's current window ≠ window associated with `TMUX_PANE` in hook process
- Window 1 is current when hook fires for window 2

**Mitigation (not implemented):**
- Add `-t` argument to worktree hook `rename-window` calls
- Use `TMUX_PANE` env var or derive window ID from pane ID
- Guard against renaming windows outside the current Claude session

## Canonical Naming Contract

### Format Specification

**Intended Format:** `<directory/repository> (<branch>)`

**Current Implementation Format:** `{repo}_{branch}` or `{directory}`

**Examples:**
| Context | Intended | Current Implementation |
|---------|----------|------------------------|
| Git repo on `master` | `.files (master)` | `.files_master` |
| Git repo on `feature/auth` | `api (feature/auth)` | `api_feature/auth` |
| Non-git directory | `Documents` | `Documents` |

**Recommendation:** Update format to match intended spec or document current format as canonical.

### Resolution Logic

1. **Directory/Repository Name:**
   - If in git repo: `git rev-parse --show-toplevel | xargs basename`
   - If not in git repo: `basename "$PWD"`

2. **Branch Name:**
   - `git symbolic-ref --short HEAD` (current branch)
   - Fallback: `git branch --show-current`
   - If fails: omit branch portion

3. **Formatting:**
   - Current: `{repo}_{branch}` or `{repo}` or `{directory}`
   - Intended: `{repo} ({branch})` or `{directory}`

### Authority Hierarchy

When multiple mechanisms attempt to name the same window, authority is:

1. **Notification Hook** (highest priority) — `!` prefix for visual "waiting" indicator
   - Temporary state, always takes precedence
   - Removed by Clear Waiting when user switches to window

2. **SessionStart Hook** — Initial naming on Claude startup/resume
   - Sets base name on session creation
   - Stores name in `~/.claude/session-names/{session_id}` for persistence
   - Respects user manual renames (checks `automatic-rename` option)

3. **Stop Hook** — Updates name when Claude stops
   - May change name if CWD changed during session
   - Re-applies stored name if available

4. **Worktree Hooks** (buggy) — Override on worktree create/remove
   - Should have high priority for worktree events
   - Currently buggy (renames wrong window)

5. **vim-prosession** (lowest priority, conflicts) — Names on vim session load
   - Conflicts with Claude hooks
   - No explicit integration with Claude naming system
   - Uses custom format (`@@@` from config)

### Invariants

The following must always hold:

1. **CWD Reflection:** Window name must reflect current working directory or git context
   - If CWD is `/Users/josh/.files`, name should be `.files` or `.files_{branch}`

2. **Notification Prefix:** `!` prefix indicates Claude waiting for input (temporary state)
   - Prefix added by Notification Hook
   - Prefix removed by Clear Waiting
   - Base name preserved during toggle

3. **@claude_named Marker:** Window option `@claude_named` must be set whenever Claude renames a window
   - Used to detect manual user renames
   - Prevents Claude from overwriting user's custom name
   - Cleared on tmux-resurrect restore to allow re-naming

4. **automatic-rename Off:** Global setting prevents tmux shell integration from overwriting names
   - Set in `rc/tmux.conf:76`
   - Ensures Claude hooks have control over window names
   - Individual windows can re-enable via Worktree Remove hook

5. **Session ID Tagging:** Pane option `@claude-session-id` links pane to Claude session
   - Set by SessionStart hook (line 81)
   - Used for session-name cache lookup
   - Persists window name across tmux-resurrect restores

### Conflicts

**1. vim-prosession vs Claude Hooks**
- Both try to name windows on startup
- No coordination between systems
- vim-prosession format (`@@@`) conflicts with Claude format (`{repo}_{branch}`)
- Race condition: last to execute wins

**2. Worktree Hooks vs Current Window**
- Worktree hooks don't target specific windows (missing `-t`)
- Rename whichever window is current, not the intended window
- Causes window 2 → window 1 name stealing

**3. Manual User Renames vs Claude Hooks**
- Partially mitigated: SessionStart hook checks `automatic-rename` and `@claude_named`
- But other hooks (Stop, Worktree) don't check before renaming
- User's manual name may be overwritten

## Regression Test Cases

### Working Scenarios (Must Preserve)

#### 1. Fresh Claude Session Startup
**Setup:**
- Start Claude in a git repository
- No existing windows

**Expected Behavior:**
- Window named `{repo}_{branch}` (e.g., `.files_master`)
- `@claude_named` option set to `{repo}_{branch}`
- `automatic-rename` set to `off`
- `@claude-session-id` set to session UUID

**Verification:**
```bash
tmux display-message -p '#{window_name}'  # Should show {repo}_{branch}
tmux show-window-options -v @claude_named  # Should show {repo}_{branch}
tmux show-window-options -v automatic-rename  # Should show "off"
```

#### 2. Notification State Toggle
**Setup:**
- Claude session running
- Window named `project_main`

**Expected Behavior:**
- Claude waits for input → window renamed to `!project_main`
- `@claude-state` set to `"waiting"`
- User provides input or switches to window → window renamed back to `project_main`
- `@claude-state` cleared

**Verification:**
```bash
# While waiting
tmux display-message -p '#{window_name}'  # Should show !project_main
tmux show-window-options -v @claude-state  # Should show "waiting"

# After input
tmux display-message -p '#{window_name}'  # Should show project_main
tmux show-window-options -v @claude-state  # Should show empty
```

#### 3. tmux-resurrect Restore
**Setup:**
- Claude session running in window with name `api_feature`
- Save tmux session: `<prefix>Ctrl+s`
- Kill tmux server: `tmux kill-server`

**Expected Behavior:**
- Restore session: `tmux`
- Window name restored from `~/.claude/session-names/{session_id}`
- Window shows `api_feature`

**Verification:**
```bash
cat ~/.claude/session-names/{session_id}  # Should contain api_feature
tmux display-message -p '#{window_name}'  # Should show api_feature
```

#### 4. Manual User Rename Respected
**Setup:**
- Claude session running, window named `project_main`
- User manually renames: `<prefix>,` → type `my-custom-name`

**Expected Behavior:**
- Claude SessionStart/Resume fires
- Hook detects `automatic-rename` is `off` and `@claude_named ≠ current name`
- Window name NOT overwritten, remains `my-custom-name`

**Verification:**
```bash
tmux rename-window my-custom-name
tmux show-window-options -v automatic-rename  # Shows "off"
# Trigger SessionStart (e.g., Claude resume)
tmux display-message -p '#{window_name}'  # Should still show my-custom-name
```

#### 5. Single Window Operation
**Setup:**
- Only one tmux window exists
- Claude session starts

**Expected Behavior:**
- All hooks fire correctly
- Window name always matches current CWD/git context
- No race conditions (no other windows to conflict)

**Verification:**
```bash
tmux list-windows | wc -l  # Should show 1
tmux display-message -p '#{window_name}'  # Should match git_window_name
```

### Known Failure Scenario

#### Window 2 Steals Window 1's Name

**Setup:**
- Window 1 exists, Claude session running, named `project_main`
- Window 1 is current (user focused on window 1)
- Window 2 created (e.g., neovim opens, new Claude session)

**Trigger:**
- Worktree hook fires for window 2 (WorktreeCreate or WorktreeRemove)
- Hook calls `tmux rename-window "docs"` without `-t` argument

**Actual Behavior:**
- Window 1 renamed to `docs` (wrong window)
- Window 2 later named `docs` by SessionStart hook (correct)
- Both windows now named `docs`

**Expected Behavior:**
- Window 1 should remain `project_main`
- Window 2 should be named `docs`

**Verification:**
```bash
tmux list-windows -F '#{window_index}:#{window_name}'
# Actual:   0:docs  1:docs  (BOTH have "docs")
# Expected: 0:project_main  1:docs
```

**Reproduction Notes:**
- Not deterministically reproducible
- Depends on timing: which window is current when worktree hook fires
- More likely when user creates window 2 in background without switching to it

## Appendix: Custom Window Options

Claude hooks use custom tmux window and pane options for state tracking:

### Window Options

#### `@claude_named`
- **Type:** Window option (per-window)
- **Value:** String (window name that Claude last set)
- **Set By:** SessionStart hook (line 25), Stop hook (line 36/39)
- **Purpose:** Track whether Claude has named this window
- **Usage:** SessionStart hook checks if `@claude_named` differs from current window name to detect manual user renames
- **Cleared:** Not explicitly cleared; tmux-resurrect may clear on restore

#### `@claude-state`
- **Type:** Window option (per-window)
- **Value:** `"waiting"`, `"tool"`, or `""` (empty)
- **Set By:** Notification hook (`"waiting"`), Tool Start hook (`"tool"`), Clear Waiting (`""`)
- **Purpose:** Track Claude's execution state for visual indicators (tmux status line coloring)
- **Visual Effect:**
  - `"waiting"` → status line shows amber/yellow (defined in tmux.conf:197-199)
  - `"tool"` → status line shows amber (defined in tmux.conf:188)
  - `""` → default color

#### `automatic-rename`
- **Type:** Built-in tmux window option
- **Value:** `on` or `off`
- **Set By:** tmux.conf global (`off`, line 76), SessionStart hook (`off`, line 27), Worktree Remove hook (`on`, line 17)
- **Purpose:** Control whether tmux shell integration can rename window
- **Usage:** SessionStart hook checks this to respect manual user renames

### Pane Options

#### `@claude-session-id`
- **Type:** Pane option (per-pane)
- **Value:** String (Claude session UUID)
- **Set By:** SessionStart hook (line 81)
- **Purpose:** Link pane to Claude session for name persistence
- **Usage:** Stored name loaded from `~/.claude/session-names/{session_id}`

### State Values Reference

| State | Option | Value | Visual Effect | Set By Hook |
|-------|--------|-------|---------------|-------------|
| Running | `@claude-state` | `""` (empty) | Default window color | Stop, Clear Waiting |
| Waiting for input | `@claude-state` | `"waiting"` | Amber status line | Notification |
| Executing tool | `@claude-state` | `"tool"` | Amber status line | PreToolUse |
| Named by Claude | `@claude_named` | `{window_name}` | N/A (not visual) | SessionStart, Stop |
| Session tracking | `@claude-session-id` | `{session_uuid}` | N/A (not visual) | SessionStart |

---

## Conclusion

This audit identified **10 distinct window-naming mechanisms** across tmux hooks, Claude hooks, and neovim configuration. The primary bug is caused by **worktree hooks lacking `-t` argument**, causing them to rename the current window instead of the intended window. A secondary race condition exists between vim-prosession and Claude hooks.

**Implemented:**
- ✅ **Hook execution logging** — All window-naming hooks now log operations to `~/.claude/logs/window-naming.log`
  - Includes: timestamp, TMUX_PANE value, current window ID/name, action performed
  - Helps diagnose race conditions and track which hook renamed which window
  - View logs: `tail -f ~/.claude/logs/window-naming.log`

**Recommended Next Steps (Not Implemented):**
1. Fix worktree hooks to include `-t` argument targeting `TMUX_PANE`
2. Add internal session guards to worktree hooks (matching SessionStart/Stop pattern)
3. Consider disabling vim-prosession tmux integration or coordinating formats
4. Document or update canonical naming format (current `{repo}_{branch}` vs intended `{repo} ({branch})`)
