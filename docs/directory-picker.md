# Directory and worktree jumps

Press **Ctrl-B** or run `zz` to search directory history. Press **Alt-W** (**Option-W** on macOS) or run `zw` to search registered Git worktrees. Both pickers change the current shell directory after selection. Cancel with Escape or Ctrl-C; the directory and any unfinished command remain intact.

Inside a repository, `zw` lists that repository’s worktrees. Outside a repository, it finds repositories immediately under the current directory and lists their worktrees, including worktrees stored elsewhere. Rows show the repository and branch, identify detached heads and locked worktrees, and omit missing directories. Discovery is read-only.

The list uses the full pane with no outer border or padding. A preview appears on the right at widths of at least 110 columns, below the list in narrower panes with at least 32 rows, and starts hidden in smaller panes. Resizing updates that arrangement. The picker uses the installed shared fzf theme and has no instruction header. Branch and agent pills, semantic change-count chips, and compact glyph headings follow the shared palette, with labeled ASCII fallbacks. In a repository, the preview shows its branch, observed terminal agents, staged/unstaged/untracked status, and committed changes since the merge base, with file counts and added/deleted line totals. Up to five recent commit subjects include only commits after that merge base. A syntax-highlighted README fills the remaining preview height when there is room; it uses the configured `bat` theme, with a plain-text fallback. Outside a repository it retains the shallow file tree; file previews retain the existing `bat` or plain-text fallback.

The comparison base uses the local `origin/HEAD` reference when available, otherwise local `main` or `master`; no fetch is performed. The preview names the actual reference and merge-base commit. Uncommitted changes and committed branch changes remain separate; untracked contents are not included in line totals. If a base or statistic cannot be read, it is shown as unavailable.

Agent presence is a snapshot of live tmux/Zellij panes taken when the picker opens, matched to the selected Git worktree. A running agent client establishes attachment; it does not establish an active turn. The current terminal hooks do not expose reliable activity for each agent, so activity remains unknown. Codex desktop chats and agents outside these terminal sessions are outside this observation scope.

| Key | Action |
| --- | --- |
| Enter | Jump to the highlighted directory |
| Ctrl-Space | Keep only the current matches and start a fresh search |
| Ctrl-/ | Show or hide the preview |
| Ctrl-J / Ctrl-K | Scroll the preview |
| Escape / Ctrl-C | Cancel |

Run `zz search terms` or `zw search terms` to start with a query. Matching uses the displayed path and worktree details. If `shortpath` is available, labels shorten parent components while keeping the last two components readable; otherwise they use full paths with `~` for the home directory. Abbreviations are display labels only: selection always retains the original path. History keeps shortest paths first; worktree rows retain Git’s ordering within each repository.

These commands require Python 3 and fzf; `zz` also uses the existing `_z` history function and `zw` uses Git. Skim is no longer selected implicitly. No installation or relinking is required for the helper because the shell calls it from the dotfiles checkout.

Run `make test-directory-picker` for shell-jump and Git-discovery checks. Run `uv run --script scripts/test-directory-picker-native.py` for real themed fzf filtering, narrowing, resize, preview toggling, and selection checks against a Git fixture with committed and uncommitted changes; this captures terminal SVGs in `docs/images/directory-picker/`.

![Wide worktree picker](images/directory-picker/wide.svg)

![Tall worktree picker](images/directory-picker/tall.svg)

![Compact worktree picker](images/directory-picker/compact.svg)
