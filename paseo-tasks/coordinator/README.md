# Paseo coordinator guidance

Run `init.sh [DIR]` to install [the session startup and PR workflow](templates/PR-WORKFLOW.md), standing instructions and a starter set of lessons. The default notes repository is `~/.local/share/paseo-coordinator`. Setup requires Git and the `octo-manager` CLI. Each worker verifies its PR enrollment and event delivery in its own session.

On a new session, read the installed `PR-WORKFLOW.md`. It explains how to find the accepted task and assignee in Beads, confirm the worker on its execution host, and resume actionable PR feedback through Octo Manager.

## Existing installations

Setup refreshes the managed workflow and replaces unchanged starter notes from earlier installations. It preserves customized notes, handwritten status files, initiative directories, and unrelated staged changes. An existing `bin/commit-state` stays with its owner. Setup commits its installed guidance directly through Git. Use ordinary Git commits to record future edits to standing instructions and lessons.

Setup stops before writing if it finds a legacy `merge-seq.sh`, `merge-seq.py`, `normalize-golangci.py` or `resolve-golangci.py` in the destination’s `bin/`. Inspect and move these helpers out of that directory before retrying.
