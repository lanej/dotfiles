# GCP authentication and resource permissions

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

  # Lock the provider to exactly one repo AND one ref — repo-only is not enough (see below).
  attribute_condition = "assertion.repository == \"org/repo-name\" && assertion.ref == \"refs/heads/main\""

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

**Repo-scoping alone is not sufficient for any workflow that supports `workflow_dispatch`, `workflow_call`, or another manually/remotely-triggerable event.** Matching `assertion.repository` only confirms *which repo* — it does not confine *which code runs*: a workflow triggered via `workflow_dispatch` executes as defined on whatever branch the caller picks, not necessarily the reviewed default branch, and still satisfies a repo-only condition. Anyone with repo write access (not necessarily merge/branch-protection rights) can push an unreviewed branch with a modified workflow or payload and dispatch it to mint credentials under the real condition. Add an explicit ref check — `assertion.ref == "refs/heads/main"` (adjust for the actual protected branch) — to every WIF provider whose workflow has any trigger besides a plain `push`/`pull_request` restricted to that branch. Treat ref-scoping as the default hardening for all new WIF providers, not an opt-in for ones you happen to remember support manual dispatch.

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

**Pool-ID collision in a shared GCP project:** a shared/platform project (multiple repos and teams deploying into the same project) may already have a `google_iam_workload_identity_pool` with the ID you'd naturally pick (e.g. `github-actions-pool`), created by a different repo's own Terraform. Check for this before planning (`gcloud iam workload-identity-pools describe <id> --project=<project> --location=global`) rather than letting `tofu plan`/`apply` surface it as a collision. If it already exists and is owned by someone else's state: don't touch it and don't widen its existing provider's `attribute_condition` to cover your repo too. Instead, reference the pool as a `data` source (read-only, not owned by your state) and add your own distinctly-named `google_iam_workload_identity_pool_provider` underneath it, scoped by its own `attribute_condition` to just your `org/repo` + ref. This leaves the other team's provider and its security boundary completely untouched while still giving your repo keyless auth under the same pool.

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
