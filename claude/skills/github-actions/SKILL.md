---
name: github-actions
description: GitHub Actions workflow design for deploying to GCP — Workload Identity Federation (keyless OIDC), per-resource least-privilege IAM, path-filtered multi-workflow layouts, and digest-based Cloud Run deploys. Use when creating or editing .github/workflows/*.yml that build/push images or deploy to GCP, when setting up CI auth to a cloud provider, or when a workflow needs to trigger on specific file paths for one of several deployable components in the same repo.
---

# GitHub Actions Skill

Patterns for GitHub Actions workflows that build and deploy to GCP, learned from standing up deploy-on-push for a multi-service repo (Cloud Run Service + Cloud Run Job, one Terraform-managed GCP project).

## Workload Identity Federation — keyless GCP auth from CI

Never mint a long-lived GCP service account key for a GitHub Actions runner. Use OIDC federation instead — GitHub issues a short-lived token per run, GCP trusts it directly, no secret ever exists.

**Terraform-side setup** (`google_iam_workload_identity_pool` + `..._provider`):

```hcl
resource "google_iam_workload_identity_pool" "github_actions" {
  workload_identity_pool_id = "github-actions-pool"
}

resource "google_iam_workload_identity_pool_provider" "github_actions" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Lock the provider to exactly one repo — do not leave this open.
  attribute_condition = "assertion.repository == \"org/repo-name\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "github_actions_deployer" {
  account_id = "github-actions-deployer"
}

resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_actions_deployer.name
  role                = "roles/iam.workloadIdentityUser"
  member              = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_actions.name}/attribute.repository/org/repo-name"
}
```

The `attribute_condition` is the actual security boundary — without it, *any* repo in your GitHub org (or on GitHub entirely, depending on pool config) could mint tokens against this SA. Always scope it to the exact `org/repo` string.

**Workflow-side auth** (`google-github-actions/auth`):

```yaml
permissions:
  contents: read
  id-token: write   # required — this is what lets the runner request an OIDC token at all

steps:
  - uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider
      service_account: github-actions-deployer@PROJECT_ID.iam.gserviceaccount.com
```

`workload_identity_provider` uses the numeric project number, not the project ID — you only get the real value after `tofu apply` creates the pool/provider (Terraform outputs it). This means: provision the WIF Terraform once manually, read the output, then hardcode that resource name into the workflow YAML. It does not need to be a secret — the attribute condition is what protects it, not obscurity.

## Per-resource least-privilege IAM, not project-wide roles

Grant the deploy SA access scoped to the specific resources it deploys, not `roles/run.admin` or `roles/editor` project-wide:

```hcl
resource "google_artifact_registry_repository_iam_member" "deployer_push" {
  location   = "us-central1"
  repository = "my-repo"
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.github_actions_deployer.email}"
}

resource "google_cloud_run_v2_service_iam_member" "deployer_service" {
  name     = "my-service"
  location = "us-central1"
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.github_actions_deployer.email}"
}

resource "google_cloud_run_v2_job_iam_member" "deployer_job" {
  name     = "my-job"
  location = "us-central1"
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.github_actions_deployer.email}"
}

# gcloud run deploy / jobs update need this to keep the existing runtime SA attached —
# without it, deploy fails trying to re-set the job/service's own identity.
resource "google_service_account_iam_member" "deployer_act_as_runtime_sa" {
  service_account_id = google_service_account.runtime_sa.name
  role                = "roles/iam.serviceAccountUser"
  member              = "serviceAccount:${google_service_account.github_actions_deployer.email}"
}
```

One `roles/artifactregistry.writer` grant covers push access for every image pushed to that repo — don't create per-image grants. But `run.developer` must be granted per Cloud Run resource (service or job), since there's no repo-level Cloud Run equivalent.

## Path-filtered multi-workflow layout

GitHub Actions has **no per-job path filter** — `on.push.paths` applies to the whole workflow file. If a repo deploys N independent components (e.g. a frontend+backend service and a separate worker job), don't try to cram them into one workflow with conditional job logic — write **one workflow file per deployable component**, each with its own `paths:` filter:

```yaml
# .github/workflows/deploy-service-a.yml
on:
  push:
    branches: [main]
    paths:
      - 'src/service_a/**'
      - 'Dockerfile.service_a'

# .github/workflows/deploy-service-b.yml
on:
  push:
    branches: [main]
    paths:
      - 'src/service_b/**'
      - 'Dockerfile.service_b'
```

A push touching both path sets triggers both workflows concurrently — that's correct and expected, not a race condition to guard against (each targets a different GCP resource).

**Verify path filtering actually works**, don't just trust the YAML: push a change to an explicitly out-of-scope path (e.g. a DAG file neither workflow should care about) and confirm neither workflow run appears in `gh run list`. Path filter bugs are easy to write (a too-broad glob, a missing leading `/`) and silent — they either over-trigger (wasted deploys) or under-trigger (a real change ships without a deploy) with no error either way.

## Digest-based Cloud Run deploy, not `:latest`

Build and push both a floating tag and a content-addressed digest, but **deploy by digest**:

```yaml
- name: Build and push
  run: |
    docker build -t "${IMAGE}:latest" -t "${IMAGE}:${{ github.sha }}" .
    docker push "${IMAGE}:latest"
    docker push "${IMAGE}:${{ github.sha }}"
    DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${IMAGE}:${{ github.sha }}" | cut -d'@' -f2)
    echo "digest=${DIGEST}" >> "$GITHUB_OUTPUT"

- name: Deploy
  run: |
    gcloud run deploy my-service --image="${IMAGE}@${{ steps.build.outputs.digest }}" --region=us-central1
```

Pushing a new `:latest` image alone does **not** trigger a new Cloud Run revision — Cloud Run only redeploys when the deploy command runs with a resolved reference. Deploying by digest (rather than `:latest`) also makes the deployed artifact byte-verifiable: after a workflow run, `gcloud run services describe`/`gcloud run jobs describe` and compare the serving image's digest against what the workflow pushed — an exact match is real end-to-end proof, "the workflow reported success" is not.

**Known, accepted drift**: if Terraform's `google_cloud_run_v2_service`/`_job` resource pins `image` to a floating tag (`:latest`) for its own initial-create/plan purposes, a CI deploy-by-digest will cause `tofu plan` to show drift on that field afterward. This is expected, not a bug — reconcile it the next time Terraform runs against that resource, don't try to make CI itself keep Terraform state in sync (that would require giving the CI SA far broader Terraform-apply permissions for no real benefit).

## Static/AI review cannot substitute for actually running the workflow

A workflow YAML can pass multiple layers of review — task-level review, a final whole-diff review, even a dedicated high-capability review pass — and still ship with an execution-order bug that only a live run exposes. Reviewers read the YAML sequentially and reason about intent; they do not simulate the runner's actual working directory state at each step.

Confirmed failure mode: a `test` job ran the backend test suite before a separate `build-frontend` step had run, and the backend tests happened to serve static files from the frontend's build output directory. Every reviewer (two task-scoped reviews plus one whole-branch review) read the YAML as internally consistent and approved it — none caught that step B depends on step A's filesystem side effect, because none of them executed the steps in order against a real checkout.

**Rule:** treat a CI/CD workflow change as unverified until it has been triggered at least once against real infra and observed to either fully succeed or fail for an already-understood reason. Push a trivial, reversible change that matches the workflow's path filter, watch the run (`gh run watch` / `gh run view --log`), and only then consider the change done. This is a specific case of a workflow that inherently cannot be validated by reading — the failure mode is order-of-operations across steps that touch a shared filesystem, which no amount of re-reading the YAML will surface.

## CI runners have zero ambient credentials — this is a feature, not friction

A GitHub Actions runner has no `gcloud auth application-default login` session, no cached ADC file, nothing. Any code path that constructs a cloud client (`bigquery.Client()`, etc.) outside a try/except that's supposed to degrade gracefully will crash for the first time here — even if that code has run correctly for months on developer laptops and in production (where ADC/the runtime SA is always present).

This makes a from-scratch CI run a genuine, high-value correctness check distinct from "does the code work" — it answers "does the code work with **no** implicit credential fallback," which laptop-based testing structurally cannot answer. Treat a credential-related failure surfaced only in CI as a real, pre-existing gap worth fixing (not a CI environment quirk to work around), especially if the failing function has a documented "never raises" / graceful-degradation contract.

## A run stuck at "pending" with zero jobs is not a hang — diagnose, don't just wait longer

GitHub Actions does not fail fast when a run can't start; it queues indefinitely at `pending`/`queued` with no job list and no error. Waiting longer does not help — the run is stuck for one of a small number of diagnosable reasons, and re-checking status alone (`gh run list`/`gh run view`) won't reveal which one, because a "pending, zero jobs" run looks identical in all of them:

1. **Org included Actions minutes are exhausted.** GitHub queues rather than erroring — other workflows (e.g. `validate.yml` on GitHub-hosted runners) can keep succeeding normally while a specific workflow's runs silently pile up. Check org billing/Actions usage, not just this repo's run list.
2. **An older run is holding the `concurrency` group lock.** If the workflow sets `concurrency: { group: ..., cancel-in-progress: false }`, one ancient stuck or awaiting-approval run (hours or days old) blocks every subsequent run in the same group forever — including ones that would otherwise run fine. Find and cancel/resolve the old one before assuming the new push is broken.
3. **A real environment-approval gate is genuinely waiting on a human reviewer.** Distinguish this from #2 by checking `pending_deployments`, not top-level status:
   ```bash
   gh api repos/OWNER/REPO/actions/runs/RUN_ID/pending_deployments
   gh api repos/OWNER/REPO/actions/runs/RUN_ID/jobs   # zero jobs = not yet started, not "running slowly"
   ```
4. **Self-hosted runners have no matching label/are all busy/offline.** If the workflow targets `runs-on: [self-hosted, ...]`, a run queues forever if no runner with that exact label is currently online — check `gh api repos/OWNER/REPO/actions/runners` for online/busy status before assuming the workflow file itself is wrong.

A workflow-file-only change (e.g. editing `.github/workflows/*.yml`) does **not** retrigger a run on its own unless the workflow's `on.push.paths` filter also matches — merging a fix to the workflow YAML with no matching path change produces zero new runs, which looks identical to "the fix didn't work" if you only watch for a new run to appear.

**Self-hosted runner note:** a fresh runner VM has no shared plugin/dependency cache, so the first several jobs on it are slow for that reason alone (not stuck) — don't conflate "slow because cold cache" with "stuck because blocked." Check actual job elapsed time (`gh run view --json jobs` timestamps) before concluding either way.
