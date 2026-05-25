<claude-mem-context>
# Memory Context

# [.files] recent context, 2026-05-25 1:45pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (16,990t read) | 315,944t work | 95% savings

### May 18, 2026
5199 10:42a 🚨 git-crypt symmetric key potentially exposed in public dotfiles repo
5202 10:46a 🔐 git-crypt key file in dotfiles repo — safe to commit
5203 10:47a 🔐 git-crypt key exposure audit in public dotfiles repo
5204 " 🔵 ~/workspace repo has no git-crypt encrypted files
5205 10:48a 🔵 ~/.files is the only git-crypt-enabled repo across 70+ local repositories
5206 " 🔵 Sensitive-named files tracked unencrypted in public dotfiles repo
5207 10:49a 🔵 git-crypt key file confirmed as PGP RSA encrypted — not a raw key leak
5208 " 🔐 superwhisper/settings/settings.json was committed in plaintext before encryption — history still public
5209 " 🔵 superwhisper/settings.json encryption boundary confirmed: one plaintext commit before encryption took effect
5210 10:51a 🔵 ~/workspace repo contains sensitive organizational content with zero encryption
5211 " 🔵 git-crypt key scope confirmed: ~/.files only, not ~/workspace — user's belief was incorrect
5212 10:53a ⚖️ Git-crypt remediation plan written: Option A (remove git-crypt from dotfiles) recommended
5283 1:25p 🚨 git-crypt private key potentially exposed in public dotfiles repo
5284 1:26p 🔵 ~/workspace uses git-crypt but has no .git-crypt/ directory
5290 1:28p 🔵 ~/workspace uses git-remote-gcrypt (GPG-based), not git-crypt
5294 1:29p 🔵 ~/workspace has no git-crypt encrypted files — confirmed
5295 1:30p ⚖️ Git-crypt remediation plan: remove git-crypt from dotfiles, no key rotation needed
5296 1:32p ⚖️ Dotfiles git-crypt plan revised: keep encryption, just delete stale claude/* branches
5378 3:11p 🔵 qmd skill exists in dotfiles; lancer/pkm skills removed
S3005 Update qmd skill file to make CLI the primary interface after qmd MCP was removed (May 18 at 3:12 PM)
5380 3:13p ✅ qmd skill file updated: CLI promoted to primary interface, MCP demoted
S3030 Migrate qmd interface from MCP to CLI-first, update CLAUDE.md and skill file, commit changes to dotfiles repo (May 18 at 3:14 PM)
5536 7:01p 🔵 Global settings.json has invalid WorktreeCreate/WorktreeRemove hook keys
S3272 Improve the xlsx skill file — fix broken examples, add gotchas, trim bloat (May 18 at 7:02 PM)
### May 20, 2026
6445 10:52a 🔵 xlsx binary stats subcommand requires COLUMN argument
6446 " 🔵 xlsx filter supports --offset pagination and 0-based sheet index
6447 " 🔵 xlsx slice uses --start/--end flags, not positional arguments
6448 10:53a 🔵 xlsx advanced subcommands are full sub-command groups with rich functionality
6451 " ✅ xlsx SKILL.md rewritten — 383 lines collapsed to 117 with correctness fixes
S3351 Upgrade /reflection skill to dispatch sub-agents that fix issues in local tool repos rather than documenting workarounds (May 20 at 10:54 AM)
6752 4:14p ⚖️ Reflection skill should dispatch sub-agents to fix issues, not add caveats
6754 4:15p 🔵 reflection.md skill current structure: 4-step analyze-scope-apply workflow
6755 " 🟣 reflection.md upgraded: tool-repo scope added, sub-agent dispatch for local fixes
S3411 Update /compose and distill skill: make distill a mandatory whole-document pass; fix YAML quoting bug in distill SKILL.md (May 20 at 4:16 PM)
### May 21, 2026
6981 8:50a ✅ /compose skill: distill made mandatory whole-document pass in Stage 6
6982 8:51a 🔴 distill skill: fixed YAML parse error from unescaped apostrophe in description field
S3417 Should reflection skill treat claude-mem as a valid output target for capturing session findings? (May 21 at 8:52 AM)
7003 9:24a ⚖️ Reflection skill should consult claude-mem for session context
S3418 Integrate claude-mem (auto-memory) as a first-class output target for the reflection skill (May 21 at 9:25 AM)
7004 9:25a 🟣 Reflection skill updated to include claude-mem cross-reference step
7006 " ✅ Reflection skill granted Write tool permission for direct memory file writes
7007 9:26a ✅ Auto-memory elevated to first-class reflection target alongside CLAUDE.md and skill files
7008 " 🟣 Auto-memory scope fully documented in reflection skill with type taxonomy and decision order
7010 " 🟣 Reflection skill Step 4 gains memory dispatch handler with concrete write instructions
S3506 Fix tmux bell misattribution in Claude hooks so bell always rings in the Claude window, not the active window at hook-fire time (May 21 at 9:26 AM)
### May 22, 2026
7474 10:34a ⚖️ tmux bell attribution fix plan for Claude hooks
7475 " 🔴 claude-notification-hook tmux attribution fixed with -t $TMUX_PANE
7476 " 🟣 claude-stop-bell-hook: new Stop hook rings bell only when task is complete
7477 10:35a 🟣 claude-stop-bell-hook registered in Stop hooks and verified working
7478 " 🔵 claude-stop-bell-hook todo-suppression logic verified via unit tests
7479 " 🔵 claude-stop-bell-hook is untracked in .files git repo
7480 " 🔵 claude-stop-bell-hook missing from git status despite Write tool reporting success
7481 " ✅ tmux bell attribution changes committed to .files dotfiles repo
S3516 Commit distill skill YAML fix and packaged .skill file to dotfiles repo (May 22 at 10:36 AM)
7502 11:15a ✅ Dotfiles repo has multiple staged modifications across CLAUDE.md and skills
### May 24, 2026
S3712 Fix claude-session-start-hook to preserve manually-set session names (via /name) across session restarts instead of overwriting with cwd basename (May 24 at 9:59 AM)
### May 25, 2026
8820 1:43p ⚖️ Persistent tmux session management investigation initiated
8821 1:44p 🔵 No existing tmux plugin manager or persistence config in dotfiles
8822 " 🔵 Josh's tmux dotfiles structure and config baseline
8823 " 🔵 tmux.conf uses @prefix_highlight variables indicating partial plugin awareness

Access 316k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>