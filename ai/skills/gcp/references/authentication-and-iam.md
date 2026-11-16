# Authentication and IAM

## Authentication

Standard GCP application default credentials work:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

The Vertex SDK picks up ADC automatically. No explicit token management needed for local development.

**`gspace auth` and `gcloud auth application-default login` write the same on-disk ADC file** (`~/.config/gcloud/application_default_credentials.json`). If ADC is missing a specific scope (e.g. `sqlservice.login` for Cloud SQL IAM auth), widening `gspace`'s own requested-scope list and re-running its OAuth flow is a legitimate alternative to a raw `gcloud auth application-default login --scopes=...` re-auth — but only once that scope is in gspace's request list. Don't assume a narrow scope is covered by the broad `cloud-platform` scope; check `gspace_check_auth`'s actual scope list first. (detail: memory "reference_gspace_gcloud_shared_adc_credential")

## Cloud Run IAM Roles for Deploy Automation

Distinguish these three roles when granting an automation identity (CI service account, another Cloud Run service's SA) access to deploy or invoke Cloud Run — they're commonly conflated, and under- or over-provisioning each fails differently:

- **`roles/run.developer`** (scoped to the specific service/job) — required to *deploy*: `gcloud run deploy` / `gcloud run jobs update`, including changing the image, env vars, or resource limits. Does not include invoking a Job with per-run argument overrides.
- **`roles/run.invoker`** (scoped to the specific service/job) — required only to *call* an already-deployed service or trigger an already-deployed job with its existing configuration. Insufficient for deploy.
- **`roles/iam.serviceAccountUser`** on the *runtime* service account (not the automation identity's own SA) — required alongside `run.developer` whenever the deploy command needs to keep an existing runtime identity attached to the resource. Without this, deploy fails trying to re-set the service/job's own SA, even though the automation identity isn't changing anything about the SA itself.

For the Workload Identity Federation (keyless OIDC) setup a GitHub Actions runner needs to hold `run.developer` — the WIF pool/provider Terraform and workflow-side auth step — see the `github-actions` skill; this section is the GCP-side role vocabulary those grants use.

**`bigquery.jobUser` is scoped to the project the query bills against — which is not necessarily the dataset's project.** `bigquery.dataViewer` is dataset-scoped and goes on whichever project owns the dataset being read. `bigquery.jobUser` is project-scoped and must additionally be granted on whatever project the calling client actually bills the job against — by default the SA's/client's own project, not the dataset's, unless the client code explicitly overrides it. Copying an IAM pattern from a precedent repo that grants `jobUser` on the dataset's project is not sufficient if your own client bills elsewhere — check which of the precedent's grants its own client code actually relies on, not just which one exists. A `403 bigquery.jobs.create` on the SA's own project (not the dataset's) is the signature of this miscopy. (detail: memory "reference_bigquery_jobuser_billing_project_not_dataset_project")
