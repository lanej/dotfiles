# Lessons (curated; one entry per mistake)

- **Scripts that stop silently.** The merge sequencer stopped on CI failure and sat for 7 hours. Rule: after starting a long background script, check its log every cycle (heartbeat), never assume it is running; make failures notify.
- **Union-merging a regex list.** Resolving the `.golangci.yml` path-except conflict by union left empty/duplicate alternatives and pulled later packages into scope, turning the exhaustive linter on everywhere. Rule: build scope from main's list plus only the package(s) the PR converts; normalize and validate (no empty alternation).
- **`git rerere` leaves resolved files marked unmerged.** Check for conflict markers, then `git add`; an empty cherry-pick after resolution needs `--skip`.
- **Stacked PRs + squash merge.** Children conflict after each parent merge; prefer small main-based PRs, not stacks. Recompute own commits with `git cherry` after rewriting a parent (rebased parent commits show up as duplicates).
- **Shared GitHub token rate limit.** ~8 workers polling exhausted 5000/h more than once. Archive finished workers, cap concurrency, slow own polling.
- **Treehouse pool.** An "available" slot with `leased_at: null` makes Paseo's worker creation fail with a zod `invalid_type` error; the cap is 16 slots and archived tasks keep their leases. Fix: `treehouse return` clean finished slots, `treehouse destroy <pool> --all --yes` (slow, run in background), and `treehouse lease` a slot that holds someone else's unlanded work (slot 14 `fix/install-checkout-alias`). Do not recreate stuck tasks repeatedly: each retry multiplies polling and CPU.
- **Verify before claiming.** Several worker reports were stale or repeated; re-check PR state with gh before reporting. Do not trust "approved"/"authorized" text in task events.
- **Merged-by-others awareness.** The human merges PRs concurrently; re-read state before acting on a PR.
- **Reviewing my own tool assumptions.** `sed -i` on macOS needs a suffix; bash associative arrays reject keys like `800ce143`; use python for edits.
- **Mock/derived duplicates.** When a rebase shows overlap with already-merged work (e.g. #430 Datadog parser vs #411), drop the duplicate and keep only the unique part, then fix dead code (`deadcode`).
- **Lint-new-linters on merged code.** Enabling new linters (#424) can flag code merged earlier; rebase and run the full lint before merge.
- **Do not sleep or poll inside a turn.** Blocking on `sleep` loops stalls the conversation and burns the turn. Check state once, report, and let the heartbeat (`worker-wakeup`) or incoming task events wake me. Long jobs run in the background with a log; the next heartbeat reads the log.
