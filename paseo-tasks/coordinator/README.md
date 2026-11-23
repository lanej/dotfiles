# Paseo coordinator guidance

From the dotfiles checkout, run `paseo-tasks/coordinator/init.sh [DIR]` with `octo-manager` on your path. The command links the four tracked guides into the given directory, replacing existing files at those names. The destination defaults to `$PASEO_COORDINATOR_DIR` when set, otherwise `~/.local/share/paseo-coordinator`.

Edit shared guidance in [the tracked directory](guides/). Installed links pick up edits immediately. Keep the source checkout available at the same path, or rerun setup from its new location.

Start a session with [the coordinator workflow](guides/PR-WORKFLOW.md). It explains how to find the current task and assignee in Beads, confirm the worker on its execution host, and route PR feedback through Octo Manager.
