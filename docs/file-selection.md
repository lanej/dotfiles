# File selection

Shell and Neovim searches use smart case: lowercase queries ignore case, while queries containing uppercase letters respect case.

File selection uses fzf in the shell and FzfLua in Neovim. A standalone Python helper stores usage in `$XDG_STATE_HOME/dotfiles/file-history.sqlite3`, defaulting to `~/.local/state/dotfiles/file-history.sqlite3`. It uses Python's standard SQLite library and needs no editor plugin, headless editor, or background service. Concurrent shell and editor processes share transactional updates. Each selection or file visit adds one point; scores decay with a 30-day half-life.

Candidates are ordered by frequency/recency, then fewer directory levels, then shorter paths. fzf still ranks by fuzzy match quality first and uses that candidate order when match scores tie. An empty query shows usage-ranked files. Depth is measured relative to the search directory. Generic piped fzf input retains its shorter-match tie-break rather than assuming every input line is a file path.

## Shell

Ctrl-T and the Ctrl-O file picker search the current directory's files. Pressing Enter records the selected files and inserts their paths into the command line. Ctrl-O retains its hidden/ignored-file toggle. Cancellation records nothing.

`frec` searches previously used files across projects and prints the selected absolute paths. It records accepted selections. For example, `nvim "$(frec)"` opens a single selected file; if you cancel, no file visit is recorded. Global search includes only existing previously used files, so it does not scan the entire filesystem. It finds files outside the current working directory and excludes deleted files from its results.

Shell ranking and recording require Python 3, supplied by bootstrap. Without Python, shell Ctrl-T and Ctrl-O fall back to ordinary `fd` candidates.

## Neovim

`<leader>ff` searches current-directory files, `<leader>fr` searches from the current file's directory, and `<leader>gf` searches tracked files from the repository root. `<leader>fc` opens the global frequently/recently used file picker. File visits are also recorded when entering ordinary file buffers, so opening files outside the picker teaches the same shared history. Updates are batched and flushed before opening a picker or exiting Neovim.

In `<leader>ff`, Ctrl-G includes or excludes ignored and hidden files while retaining the query; `.git` stays excluded. Existing FzfLua previews, file-opening actions, Ctrl-H preview toggle, and Ctrl-F fullscreen toggle remain available. Long paths keep their filename end visible in narrow pickers. Other Neovim searches and specialized review/status pickers continue to use their existing FzfLua providers.

## Verification

Run `python3 scripts/test-nvim-file-picker.py --check history` for standalone history, concurrency, decay, global lookup, real shell acceptance, cancellation and safe filename forwarding. It uses Python, fd, fzf and Zsh. Run `python3 scripts/test-nvim-file-picker.py --check editor` for the mapped Neovim picker, file visits, shared shell ranking, Git-root scope and narrow global lookup. The editor check adds installed Neovim, FzfLua and devicons. Both checks use disposable configuration and history directories. Omit `--check` to run both.

CI setup helpers live under `.github/scripts/`. `make shellcheck` includes the shared tool installer. Run `uvx --from ruff==0.17.5 ruff check --isolated .github/scripts/prepare-file-selection-plugins.py` to lint the editor fixture setup independently of GitHub Actions.
