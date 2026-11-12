# Directory and worktree jumps

Press **Ctrl-B** or run `zz` to search directory history. Press **Alt-W** (**Option-W** on macOS) or run `zw` to search registered Git worktrees. Both pickers change the current shell directory after selection. Cancel with Escape or Ctrl-C; the directory and any unfinished command remain intact.

Inside a repository, `zw` lists that repository’s worktrees. Outside a repository, it finds repositories immediately under the current directory and lists their worktrees, including worktrees stored elsewhere. Rows show the repository and branch, identify detached heads and locked worktrees, and omit missing directories. Discovery is read-only.

The Charmed picker sizes the results from the current matches. Short paths fill additional columns when the list overflows vertically. Filtering to a handful of matches returns to one column. The highlighted path stays selected across a resize or a background update while it still matches. For repository roots, branch, working-tree status and attached agent names appear beside the path and become searchable as they arrive. Type a query such as `Codex dirty` to narrow directly to matching worktrees.

The selected repository preview shows its branch, agent observations, staged/unstaged/untracked changes, committed changes since the merge base, and up to five recent commit subjects with their file and line counts. A rendered README fills any remaining height. Markdown uses the shared Glow theme, with bat and plain text as fallbacks. Outside a repository the preview shows a shallow directory tree. A preview containing only the selected path gives its space back to the list. A narrow, tall pane can show the preview below the matches, and a small pane can open it on demand.

The comparison base uses the local `origin/HEAD` reference when available, otherwise local `main` or `master`; no fetch is performed. The preview names the actual reference and merge-base commit. Uncommitted changes and committed branch changes remain separate; untracked contents are not included in line totals. If a base or statistic cannot be read, it is shown as unavailable.

Agent presence is a snapshot of live tmux/Zellij panes taken when the picker opens, matched to the selected Git worktree. A running agent client establishes attachment; it does not establish an active turn. The current terminal hooks do not expose reliable activity for each agent, so activity remains unknown. Codex desktop chats and agents outside these terminal sessions are outside this observation scope.

| Key | Action |
| --- | --- |
| Up / Down | Move within the results |
| Left / Right | Move between result columns when shown |
| Enter | Jump to the highlighted directory |
| Ctrl-Space | Keep only the current matches and start a fresh search |
| Ctrl-/ | Show or hide the preview |
| Ctrl-J / Ctrl-K | Scroll the preview |
| Escape / Ctrl-C | Cancel |

Run `zz search terms` or `zw search terms` to start with a query. Filtering uses fzf query syntax over the path label and available row details. If `shortpath` is available, labels shorten parent components while keeping the last two components readable; otherwise they use full paths with `~` for the home directory. Abbreviations are display labels only: selection always retains the original path. History is ordered by the score from `_z -l`, with shorter paths first on ties. Worktrees retain Git’s ordering within each repository.

The shell set builds the native UI during `make install`. To build or update just the picker in an existing checkout, run `make directory-picker` with Go available. Both commands use Python 3 and fzf. A checkout without the native binary uses the previous interactive fzf picker.

Run `make test-directory-picker` for shell-jump and Git-discovery checks. After building the UI, run `uv run --script scripts/test-directory-picker-native.py` to exercise the actual Ctrl-B and Alt-W bindings and capture the following terminal views.

![Directory history with 81 matches in two selectable columns](images/directory-picker/history.svg)

![Worktree branch, status and agent names beside each path](images/directory-picker/worktrees.svg)

![Wide worktree picker](images/directory-picker/wide.svg)

![Tall worktree picker](images/directory-picker/tall.svg)

![Compact worktree picker](images/directory-picker/compact.svg)
