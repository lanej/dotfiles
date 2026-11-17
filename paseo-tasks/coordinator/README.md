# Paseo coordinator memory

The Paseo task coordinator keeps standing instructions, lessons, current state, and reusable scripts in a local Git repository, normally at `~/.local/share/paseo-coordinator`. This directory is the source for its templates and scripts.

`init.sh [DIR]` seeds missing state files, preserves existing state, refreshes the scripts, and commits the result. Persistence failures propagate; “ready” means the commit succeeded or there was nothing to commit. `bin/commit-state MESSAGE` records later state changes. Replace current state rather than appending history, keep initiative details separate, and use Git history for earlier observations.

## Authorized merge sequencing

`bin/merge-seq.sh PR [PR...]` retains the existing Bash entrypoint and uses a private Python implementation. It requires Python 3, Git, and authenticated `gh`. Run it only after the human explicitly authorizes rebasing, publishing, and merging those PRs. Passing checks do not replace required reviews or grant authority.

Use a clean, dedicated clone with one `origin` fetch URL and one push URL, both identifying `EPSCTL_REPO` (default `easypost-sandbox/epservicesctl`). `EPSCTL_MERGE_DIR` selects the clone and `EPSCTL_MERGE_META` selects the metadata directory. Defaults are `/tmp/epsctl-merge` and `/tmp/epsctl-merge-meta`.

Each `PR.tsv` must contain five tab-separated fields: head branch, base branch, state, comma-separated replay commits, and captured full head SHA. Legacy four-field metadata is rejected. Capture an `OPEN`, non-draft, same-repository PR already targeting `main`; retarget stacked PRs manually after checking their parents. The replay list must exactly match `git rev-list --reverse BASE_SHA..HEAD_SHA` for fetched current main and captured head, without merge commits. Reconcile other histories manually rather than guessing which commits may be omitted.

The sequencer creates a new scratch branch without replacing an existing branch. It retains the epservicesctl lint-scope adapters, stops on adapter or Git failures, and publishes with a lease against the captured SHA. Metadata is never silently refreshed to authorize someone else’s newer work.

Publication must be confirmed before checks are used. Checks belong to the exact published head; missing, pending, failed, cancelled, malformed, or unavailable results cannot authorize a merge. The default poll budget is 90 observations, 45 seconds apart; `EPSCTL_MERGE_ATTEMPTS` and `EPSCTL_MERGE_INTERVAL` configure it. Each external command also has a 60-second deadline. Main or head changes invalidate the assessment.

The merge uses `--match-head-commit` and completes only after GitHub reports the expected head merged and its resulting commit is found on fetched `main`. A queued or uncertain outcome stops the sequence until inspected; do not blindly repeat publication or merge requests. Failed runs retain their scratch branch and Git conflict state for inspection.

## Verification

The npm test suite includes the coordinator entrypoint detector. It uses disposable real Git repositories and controlled `gh` responses to exercise publication failure, stale metadata, concurrent updates, check failures and timeouts, head-pinned merging, merge confirmation, and initialization persistence. These checks establish orchestration and Git behavior, not live GitHub service compatibility.
