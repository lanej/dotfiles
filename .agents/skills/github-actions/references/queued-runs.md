# Diagnosing queued workflow runs

## A run stuck at "pending" with zero jobs is not a hang — diagnose, don't just wait longer

GitHub Actions does not fail fast when a run can't start; it queues indefinitely at `pending`/`queued` with no job list and no error. Waiting longer does not help — the run is stuck for one of a small number of diagnosable reasons, and re-checking status alone (`gh run list`/`gh run view`) won't reveal which one, because a "pending, zero jobs" run looks identical in all of them:

1. **Org included Actions minutes are exhausted.** GitHub queues rather than erroring — other workflows (e.g. `validate.yml` on GitHub-hosted runners) can keep succeeding normally while a specific workflow's runs silently pile up. Check org billing/Actions usage, not just this repo's run list.
2. **An older run is holding the `concurrency` group lock.** If the workflow sets a concurrency group with `cancel-in-progress` set to `false`, one ancient stuck or awaiting-approval run (hours or days old) blocks every subsequent run in the same group forever — including ones that would otherwise run fine. Find and cancel/resolve the old one before assuming the new push is broken.
3. **A real environment-approval gate is genuinely waiting on a human reviewer.** Distinguish this from #2 by checking `pending_deployments`, not top-level status:
   ```bash
   gh api repos/OWNER/REPO/actions/runs/RUN_ID/pending_deployments
   gh api repos/OWNER/REPO/actions/runs/RUN_ID/jobs   # zero jobs = not yet started, not "running slowly"
   ```
4. **Self-hosted runners have no matching label/are all busy/offline.** If the workflow’s `runs-on` list includes `self-hosted` and other labels, a run queues forever if no runner with that exact label is currently online — check `gh api repos/OWNER/REPO/actions/runners` for online/busy status before assuming the workflow file itself is wrong.

A workflow-file-only change (e.g. editing `.github/workflows/*.yml`) does **not** retrigger a run on its own unless the workflow's `on.push.paths` filter also matches — merging a fix to the workflow YAML with no matching path change produces zero new runs, which looks identical to "the fix didn't work" if you only watch for a new run to appear.

**Self-hosted runner note:** a fresh runner VM has no shared plugin/dependency cache, so the first several jobs on it are slow for that reason alone (not stuck) — don't conflate "slow because cold cache" with "stuck because blocked." Check actual job elapsed time (`gh run view --json jobs` timestamps) before concluding either way.
