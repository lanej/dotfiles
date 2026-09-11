---
name: looker-development
description: Develop LookML against a live, GitHub-CI-integrated Looker instance (the official "Looker Continuous Integration" GitHub App plus git-connected deploy). Use when debugging `looker/ci - Github CI - *` GitHub check failures or silence, setting up Looker CI (GitHub App install, CI Suite creation, deploy webhook) for a repo that doesn't have it yet, onboarding a new LookML model, diagnosing a connection/SQL Validator failure, or trying to shift feedback left before the multi-minute CI round-trip. Not for querying/searching an existing Looker catalog for data (see the `looker` skill) or for BigQuery cost/query mechanics (see the `bigquery` skill).
---

# Looker Development Against Live GitHub CI

Distilled from debugging one real instance end-to-end. The principles generalize across
Looker instances/repos; none of the concrete names below (project IDs, connection names,
model names) do — treat every specific identifier here as an example, not a default to copy.

## Two-layer architecture — know which layer you're debugging

1. **Instance-level admin page** (Admin → Platform → Continuous Integration, naming may vary
   by version): turns the CI feature on instance-wide and lets you install/authorize the
   "Looker Continuous Integration" GitHub App per repo. Necessary but **not sufficient** for
   anything to run on a PR.
2. **CI Suite**: a project-level object, created and edited only inside the Looker IDE
   (Develop → open the project → Continuous Integration icon in the left nav rail → Suites
   tab). Requires the `manage_ci` permission (included in the Admin permission set, but
   distinct from it — a role can have `develop` without `manage_ci` or vice versa). This is
   where "Trigger on pull requests from Looker" and the enabled validator list (LookML /
   Content / SQL / Assert) actually live. **There is no REST API to create or edit a suite** —
   the only documented API surface, `Project.create_continuous_integration_run`, triggers an
   *existing* suite, it doesn't create one. Suite CRUD is IDE-only even though it's
   conceptually server-side config, not code.

If a repo shows the GitHub App "Installed" and nothing fires on a PR, check layer 2 before
assuming anything is broken. Installing the app only grants Looker permission to receive
webhooks for that repo — it does not create a suite or turn on PR-triggering.

## GitHub status checks lie by omission more often than they lie outright

- **No checks at all** on an open PR is *expected*, not broken, if no CI suite exists yet with
  PR-triggering on, or if the suite/toggle was created *after* the PR was already opened —
  GitHub webhooks fire on `opened`/`synchronize`/`reopened`, never retroactively. To force a
  fresh trigger on an already-open PR: push a new commit (fires `synchronize`), or close and
  reopen it. Once a suite exists, a plain `git push` is the normal day-to-day loop — no need to
  close/reopen every time.
- **A green validator does not mean the model resolved.** If nothing in the LookML is
  resolvable at all (e.g. a new model isn't Admin-configured yet, or a dashboard references a
  model that doesn't exist), some validators can trivially pass because there's nothing for
  them to check — indistinguishable from "no problems found" by pass/fail alone. Don't treat a
  clean SQL/Content Validator as proof a model actually loaded if you have independent reason
  to suspect it didn't (e.g. a live Explore-UI error) — check via the Looker UI/API or a known
  ground-truth credential (see "API/CLI permission-ceiling trap" below), not by re-reading the
  green check.
- **A validator's rollup state can mislead.** One validator's real failure can bleed into a
  sibling's pass/fail *label* even when the sibling's own count is zero — e.g. `LookML
  Validator: fail` shown with `0 LookML validation failures` in its own description, because
  Assert Validator was the one actually erroring. Always read the check's description text,
  not just the red/green rollup.
- **Assert Validator errors instead of skipping cleanly on a project with zero data tests.** If
  `grep -rn "^test:"` across the project returns nothing, this validator is structurally
  inapplicable — don't chase it as a regression from your latest change. Root-cause fix:
  disable Assert Validator in the suite config if there's genuinely nothing to assert.
  Workaround (only if there's something real worth asserting): add an actual `test:` block —
  never add one purely to satisfy the check.

## Deploy webhook: GitHub's delivery status is not the source of truth

Looker's native auto-deploy-on-merge is a plain webhook
(`<instance>/webhooks/projects/<project>/deploy`, though see setup note below on not
hand-constructing this URL) — a mechanism entirely separate from CI validation and from any
custom deploy scripting. Two gotchas, both general to any webhook receiver whose own work is
slower than the caller's timeout, not Looker-specific:

1. **One-time bootstrap required.** The project must be deployed to production manually once
   (Looker IDE → Git Actions panel → Deploy to Production) before the webhook does anything —
   stated directly on Looker's webhook-secret config screen. Skipping this can make the
   endpoint hang/error even on a trivial `ping`.
2. **GitHub's webhook delivery timeout (~10s) is shorter than a real deploy can take**
   (git pull + LookML compile + deploy). GitHub will report `500`/`504`/"context deadline
   exceeded" on *every* delivery — including a `ping` — purely because the response is slow,
   while Looker completes the deploy successfully in the background. **The authoritative
   source is Looker's own Deployment Manager / deploy history page, not GitHub's delivery
   log.** Cross-check delivery timestamps against Looker's deploy-history timestamps before
   concluding an integration is broken: a delivery logged as failed a few seconds before a
   "success" entry in Looker's history is this pattern, not a real failure.

Don't jump to network-layer causes (IP allowlist, firewall, VPN gating) from a bare timeout —
check the receiving system's own success log first, and check whether a *different* webhook to
the same host is succeeding (if the CI webhook to the same instance works, the network path is
fine and the deploy webhook's failure is this timing pattern, not connectivity).

## Onboarding a brand-new model is multi-step and partly manual — CI-green is not "close to done"

Sequence, each step gating the next:

1. Author LookML on a branch.
2. CI green (LookML/Content/SQL validators pass).
3. **Merge/deploy to the production branch.** A model that exists only on an unmerged branch
   cannot even be *discovered* by Admin's "Add model" flow — deploy is a prerequisite for
   visibility, not just for going live.
4. An admin manually adds the model in Admin → LookML Models: enable it, set its allowed
   connection(s), set visible groups.
5. Only now is it usable — including in dev-mode preview.

A "Model 'x' has not been configured" error after CI-passing, even after merge, means step 4
hasn't happened. It's an admin action outside version control, not a LookML defect — don't try
to fix it with more LookML changes.

**Cheaper alternative:** if the new explores' data connection is compatible with an existing,
already-configured model, add the explores to that model instead of standing up a new one —
skips steps 3–4's admin/deploy sequencing entirely. Constraint: a LookML model has exactly one
`connection:` for all its explores, so this only works if the existing model's connection can
actually read the new views' source tables. Verify with an actual SQL Validator run, not by
inspecting LookML — connection-level read grants aren't visible in LookML source, and a
mismatch surfaces there, not at the LookML-validation stage (see next section).

## Connection names vs. GCP project IDs

A Looker `connection:` value is an instance-wide named resource configured in Looker Admin —
never a GCP project ID, even when a connection happens to point at a similarly-named project.
Using a GCP project ID directly as `connection:` fails CI with `Unknown database connection
"<id>"`. Get the real connection name from Admin, or from a working example elsewhere in the
same project — don't guess from the GCP project ID.

## API/CLI permission-ceiling trap

A narrowly-scoped Looker API service-account credential can 404 on admin-gated endpoints
(`connections`, `lookml_models`, ad hoc `query run-inline-query`) for resources that definitely
exist. Looker returns 404, not 403, when a credential lacks visibility scope — indistinguishable
from "doesn't exist" without a second, better-scoped credential or direct Admin UI access.
Isolate this by testing the identical call against a known-good, long-established resource: if
that also 404s, it's the credential's scope, not the target resource's absence. Also check
`user me`/whoami-equivalent for `is_service_account: true` with `can.view_in_ui: false` — a
concrete tell. Fix is a differently-scoped credential/role, never a client code change.

## Shift-left checklist — catch these before opening a PR, not after a multi-minute CI round-trip

- `grep -rn "^test:" .` across the project — if empty, expect Assert Validator to error rather
  than skip; don't burn a debug cycle chasing it as a regression.
- Check every model's `connection:` against the real configured connection list (via a
  properly-scoped API/CLI credential if available) rather than inspecting LookML source or
  guessing from naming — see the permission-ceiling trap above for why LookML source alone
  isn't ground truth.
- Before merging/adding explores into an existing model, confirm that model's connection can
  actually read the new tables — a mismatch produces a SQL Validator failure (cross-connection
  permission error), not a LookML-level one, so it won't surface until the SQL Validator step
  of a full CI run.
- Before standing up a brand-new model, decide up front whether the full onboarding sequence
  above is worth it versus folding into an existing, already-configured model — the admin/
  deploy overhead is identical regardless of how small the new content is.
- Don't test "does official CI actually fire" by opening a fresh PR and waiting on it alone —
  check the CI suite's PR-trigger toggle and the GitHub App's per-repo install status first. A
  fresh PR only tells you the outcome, not the cause, and costs a full CI round-trip either way.
- **Verify the source table actually exists and is populated before authoring a view against
  it** — a LookML `sql_table_name` referencing a nonexistent table is not caught by the LookML
  Validator (it's syntactically valid LookML), only by the SQL Validator, which means the
  earliest you'd find out is a full CI round-trip after opening a PR. If a view is meant to read
  an upstream pipeline's output (a dbt/EPQ gold table, a scheduled export, etc.), confirm that
  table exists via a warehouse client directly (e.g. `bq`/BigQuery MCP `list_datasets` +
  `describe_table`) before writing the LookML at all — a dataset existing is not the same as a
  table inside it existing. This is the single highest-leverage shift-left check for a new
  view: it catches the failure in seconds instead of minutes, and rules out an entire category
  of false "connection is broken" debugging (see "Debug loop" step 4).

## Forward-looking: when Looker depends on an upstream analysis pipeline's output

A recurring shape: some other project (an EPQ analysis, a dbt model, an ad hoc script) computes
a result and someone wants it in a Looker dashboard. The failure mode seen in practice: LookML
gets written first, against a table path that *sounds* right, before anyone confirms the
upstream pipeline actually publishes to that path — the pipeline may only ever have written to
a local file/DuckDB for its own report, with no warehouse export step at all. This surfaces as a
SQL Validator failure, but the real problem is a missing design decision made too late.

Before authoring LookML against any upstream pipeline's output:

1. Confirm the pipeline actually writes to the warehouse (grep its source for the write/export
   call — don't infer this from what dataset/table names "should" exist, or from a dataset
   existing with no tables in it, which looks encouraging but proves nothing).
2. If it doesn't yet, resolve *how it should* before writing any LookML: what provisions the
   destination dataset/table/schema (ad hoc, or infrastructure-as-code — e.g. OpenTofu, if
   that's how the org manages BQ schema elsewhere), what refresh cadence, who owns the export
   job. This is a design decision with real alternatives, not a one-line fix — treat it with
   the same up-front sequencing as the CI/deploy bootstrap steps above, not as a footnote
   discovered via a failing check.
3. Only then write the LookML view against a table that's confirmed to exist.

## Debug loop once a PR is open

1. Push a commit (fires `synchronize`) — no need to close/reopen once a suite with
   PR-triggering already exists.
2. Poll check status periodically (`gh pr checks <n>` or equivalent). A full validator run can
   take several minutes with no incremental status change in between — confirm the instance's
   own typical timing before concluding it's stuck; idling in `pending`/`queued` the whole way
   through is normal for this pipeline shape, not a hang.
3. On failure, read the check's `description` field, not just pass/fail, and follow its
   `target_url` into the Looker run page — the GitHub status text is often too terse (e.g. a
   validator-count rollup) to show which statement or connection actually failed.
4. A SQL Validator failure after merging/adding explores across previously-separate
   models/connections is *often* the connection-compatibility issue described above, but not
   always — don't stop at that hypothesis. Check whether *other* explores newly added in the
   same commit, on the same connection, passed. If they did, the connection itself is fine and
   the failure is explore-specific — read the actual error message (via the CI run detail, not
   the GitHub status text) for the real cause. A real one seen in practice: every error was
   `Table <project>:<dataset>.<table> was not found` — a table that had simply never been
   materialized upstream, confirmed independently via a BigQuery client (dataset existed,
   contained zero tables). That's a data-pipeline gap, not a Looker or connection bug at all —
   no LookML or CI change fixes it.

## See also

`references/ci-and-deploy-setup.md` — step-by-step first-time setup checklist (GitHub App
install, CI suite creation, deploy webhook + merge-strategy config) for an instance/repo that
doesn't have any of this wired up yet.
