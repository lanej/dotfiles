# Paseo coordinator state

The filesystem here is the coordinator's memory. A new session reads, in order:

1. `INSTRUCTIONS.md` — standing rules, authority limits, conventions, procedures.
2. `STATE.md` — the current snapshot (what is running, queued, open, pending). Pruned to the present; history lives in git.
3. `LESSONS.md` — curated mistakes and fixes; read before dispatching or merging.
4. `initiatives/*.md` — one short file per multi-step effort (goal, status, next step, links).
5. `bin/` — reusable scripts (merge sequencer and its conflict helpers).

## Update protocol
- After any meaningful change (worker dispatched/finished, PR opened/merged/failed, human decision or new instruction), edit `STATE.md` (replace, do not append history) and the relevant initiative file.
- New standing instruction from the human -> `INSTRUCTIONS.md`. A mistake or discovery -> `LESSONS.md` (one entry: what happened, cause, rule).
- Prune: delete resolved items; keep each file short enough to read in one pass.
- Commit every update: `bin/commit-state "<what changed>"`. The git log is the history and the self-improvement trail (review it, and LESSONS.md, when a procedure keeps failing).
