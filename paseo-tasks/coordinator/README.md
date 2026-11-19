# Paseo coordinator memory

The Paseo task coordinator keeps standing instructions, lessons, current state, and reusable scripts in a local Git repository, normally at `~/.local/share/paseo-coordinator`. This directory is the source for its templates and scripts.

`init.sh [DIR]` requires an installed `octo-manager` CLI, seeds missing state files, preserves existing state, refreshes the managed PR workflow and `bin/commit-state`, and commits the result. Persistence failures propagate; “ready” means the commit succeeded or there was nothing to commit. CLI availability does not establish service health or PR enrollment. `bin/commit-state MESSAGE` records later state changes. Replace current state rather than appending history, keep initiative details separate, and use Git history for earlier observations.

## PR ownership and follow-up

[The managed PR workflow](templates/PR-WORKFLOW.md) requires OctoManager for PR publication, monitoring, readiness and authorized merging. The worker owns review, CI and conflict follow-ups until remote completion; the coordinator routes events to that worker and maintains the current snapshot. Use the host's native agent tools for Codex workers and Paseo task tools for Pi workers. No repository names, branch names, PR numbers or conflict-resolution recipes are embedded in coordinator scripts.

Initialization refreshes `PR-WORKFLOW.md` and adds a read-first pointer to `INSTRUCTIONS.md` without replacing existing standing instructions. The managed workflow governs PR lifecycle work when older local instructions disagree. Repository-specific requirements still come from that repository's installed guidance.

## Existing memory repositories

Initialization stops before changing a destination that contains a retired `merge-seq.sh`, `merge-seq.py`, `normalize-golangci.py` or `resolve-golangci.py` helper. Inspect and preserve customized or still-needed files outside the coordinator's `bin/`, remove the retired entries, then rerun initialization. It never deletes these files on the operator's behalf or leaves an old merge engine silently active after a successful refresh.

## Verification

The npm test suite exercises initialization against disposable real Git repositories: state preservation, managed workflow refresh, missing OctoManager, retired-helper refusal, and persistence failure. It does not publish or merge live PRs or establish OctoManager service compatibility; verify enrollment and delivery in the worker's actual host session.
