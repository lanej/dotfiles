# Paseo coordinator memory

The Paseo task coordinator keeps its working memory on the filesystem so a new session can
resume and the system can improve itself: standing instructions, curated lessons, a pruned
snapshot of current state, and the scripts it reuses. The live copy is a local git repo at
`~/.local/share/paseo-coordinator`; this directory is the versioned source for its
templates and scripts.

- `init.sh [DIR]` creates or refreshes the live repo. It seeds missing files from
  `templates/`, never overwrites existing state, and always refreshes `bin/`.
- `templates/INSTRUCTIONS.md` standing rules (authority limits, capacity cap, dispatch and merge procedures, preferences).
- `templates/LESSONS.md` curated mistakes and their rules (seed).
- `templates/STATE.md` skeleton of the current-state snapshot.
- `bin/commit-state` commits the live repo; `bin/merge-seq.sh` sequences rebases and merges
  (only when the human has authorized merging) with `resolve-golangci.py` and
  `normalize-golangci.py` handling the lint-scope conflict in epservicesctl.

Update protocol (also in the live repo's README): after any meaningful change, replace
`STATE.md`, update the relevant `initiatives/*.md`, record lessons, and run
`bin/commit-state "<what changed>"`. Prune resolved items; git is the history.
When a procedure improves, update the template here too so a fresh install benefits.
