<claude-mem-context>
# Memory Context

# [.files] recent context, 2026-05-30 2:43pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (17,277t read) | 270,488t work | 94% savings

### May 28, 2026
10444 8:35a 🟣 tmux-quickswitch-alert adds "waiting" priority tier based on ! window name prefix
10445 8:36a ✅ tmux-quickswitch-alert: debug logging added to /tmp/tmux-quickswitch-alert.log
10446 " ⚖️ CLAUDE.md content considered for claude-mem storage
10447 " ✅ Removed "Edit tool strips embedded UTF-8 glyphs" rule from global CLAUDE.md
10449 8:37a 🔵 tmux select-window does not support -c flag — confirmed bug in quickswitch script
10448 " ✅ Edit tool UTF-8 glyph gotcha migrated from CLAUDE.md to auto-memory
10450 8:40a ⚖️ tmux-quickswitch-alert reverted to single-session mode — cross-session approach abandoned
10452 8:43a 🟣 tmux-quickswitch-alert handles popup session by transparently searching session 0
10453 " 🔴 tmux-quickswitch-alert: popup session now switches client to session 0 before selecting window
10795 2:15p 🔵 claude-mem observer sessions appear as tmux window titles
10796 " 🔵 claude-mem observer-sessions directory is a named path constant in the plugin source
10797 " 🔵 Custom Claude tmux hooks control window rename behavior around sessions
10798 2:16p 🔵 claude-autoname-hook unconditionally re-enables allow-rename immediately after renaming window
10799 2:19p 🔵 claude-autoname-hook edits not reflected in git diff — working tree clean after edits
10800 2:20p 🔵 bin/claude-autoname-hook is untracked in the dotfiles repo — never committed
10801 " 🔵 dotfiles .gitignore has bin/* glob — bin/ scripts require git add -f to track
10802 " 🔴 claude-autoname-hook staged for first commit — allow-rename fix confirmed in staged content
10803 " 🟣 bin/claude-autoname-hook committed to dotfiles repo
10814 2:25p 🔵 Five claude bin/ scripts exist on disk but are not tracked in git
10815 " ✅ Five previously untracked claude bin/ scripts staged alongside two modified tracked scripts
10816 " 🟣 Claude Code hook suite expanded: worktree/subagent hooks, statusline overhaul committed
S4423 Fix "observer-sessions" spurious tmux window title — caused by claude-mem observer sessions inheriting TMUX_PANE (May 28 at 2:26 PM)
10817 2:26p ✅ Desktop notification removed from claude-notification-hook — now tmux-only
10819 " 🔄 claude-notification-hook desktop notification removed and committed
10820 " 🔵 claude-worktree-remove-hook re-enables automatic-rename — potential title injection vector
10821 2:27p 🔵 claude-session-start-hook reads automatic-rename to detect user-named windows — worktree-remove-hook breaks this
10822 " 🔵 tmux after-select-window hook triggers claude-clear-waiting when window name starts with !
S4472 Add code comments to claude-mem observer session filter scripts to document the rationale (May 28 at 2:28 PM)
### May 29, 2026
11026 7:54a ✅ Expanded code comment in claude-session-start-hook for observer session skip logic
11027 7:55a ✅ Expanded code comment in claude-autoname-hook for observer session skip logic
S4477 Replace "- Nvim" text in tmux pane title with neovim Nerd Font glyph () (May 29 at 7:55 AM)
11046 8:06a 🔵 tmux auto-title system architecture in dotfiles
11047 8:08a ✅ Neovim init.lua already uses neovim glyph in titlestring
11048 " 🟣 tmux-auto-title.zsh gains @nvim_named title preservation
S4549 Fix neovim exit resetting the tmux window title (May 29 at 8:09 AM)
11333 1:07p 🔵 Neovim exit still resets terminal window
11336 1:09p 🔵 tmux-auto-title.zsh has debounced async window title updates and nvim title lock clearing
11337 " 🔴 Removed debounced async tmux title updates in favor of synchronous hooks
11338 " 🔴 Set vim.opt.titleold = "" in neovim config to prevent terminal title restore on exit
S4551 Replace "- Nvim" text in tmux pane title with neovim glyph to improve visual appearance when neovim sets the title (May 29 at 1:10 PM)
11363 1:23p ✅ Refactor tmux window title tracking from option-based to command-tracking
S4649 Restore /socrates skill to earlier interrogation-first behavior — user felt recent versions had degraded (May 29 at 1:24 PM)
### May 30, 2026
11764 12:38p 🔵 User Prefers Earlier /socrates Skill Versions With Stronger Interrogative Focus
11765 " 🔵 /socrates eaa3c6f Version Had Three-Phase Structure With Plan Mode Entry
11770 12:41p ✅ /socrates Skill Restored to Three-Phase Interrogation-First Design
11771 " ✅ Added Explicit Assumption and Source Citation Requirements to /socrates
11772 " ✅ /socrates Skill Restoration Committed to Dotfiles (ed6741c)
S4650 Restore /socrates skill to earlier interrogation-first behavior — full restoration and polish complete (May 30 at 12:42 PM)
11776 12:42p ✅ Source Citations Section Tightened to Require Inline Markdown Links
11777 " ✅ Source Citations Markdown Link Requirement Committed (4f91c7d)
S4651 Restore /socrates interrogation-first behavior — expanded to align /compose citation model with new /socrates conventions (May 30 at 12:42 PM)
11780 12:43p 🔵 /compose Skill Has Its Own Embedded 6-Question Interrogation Stage
11781 " ✅ /compose Updated to Use Inline Markdown Links Instead of Footnote Annotations
11782 " ✅ /compose Claim Classification Updated: Inline Links Replace Footnote Annotations
11783 " ✅ /compose Stage 4 Draft Rules Updated to Inline Link Citation
11784 12:44p ✅ /compose Stage 5 and Stage 7 Updated to Complete Inline Link Citation Consistency Pass
11785 " ✅ /compose Inline Link Citation Refactor Committed (681e9bf)
S4689 Verifying claude-code.nvim keymaps work after lazy=false fix — troubleshooting toggle and send-selection behavior (May 30 at 12:44 PM)
11864 2:10p 🔴 claude-code.nvim keymaps not registering due to lazy loading
S4695 Neovim keymap for Claude Code — user asked about sending a file reference (@path) instead of literal text selection (May 30 at 2:42 PM)
**Learned**: Claude Code terminal session resolves `@` references (file paths and line ranges) natively, meaning keymaps can send compact references rather than copying full text content into the prompt.

**Completed**: Nothing committed yet — discussion phase. Existing keymap sends literal text. No files have been modified.

**Next Steps**: User is evaluating whether to implement both: a normal-mode keymap (`&lt;leader&gt;af`) sending `@%` (full file reference) and an upgraded visual-mode keymap sending `@file:startline-endline` range references instead of literal yanked text.


Access 270k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>