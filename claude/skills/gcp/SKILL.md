---
name: gcp
description: Google Cloud Platform patterns and quirks — general GCP infra (IAM roles, Cloud Run deploy mechanics, Secret Manager, Cloud Monitoring) plus Vertex AI specifics for Claude/Anthropic models. Use when working with GCP infrastructure generally (IAM, Cloud Run, Secret Manager, monitoring), not only when Vertex AI or Claude-on-Vertex is involved. For OpenTofu/Terraform resource authoring see the opentofu skill; for GitHub Actions CI/CD auth and deploy workflows see the github-actions skill; for BigQuery query cost discipline see the bigquery skill — this skill covers the GCP service-level behavior those skills build on top of.
---

# GCP Skill

## Anthropic on Vertex AI — Critical Quirks

These are failure modes discovered through direct use. Follow exactly.

### Model IDs

Use **no version suffix** for the latest model on Vertex:

```typescript
// ✅ Correct (gets latest)
model: 'claude-sonnet-4-5'

// ❌ Wrong (version suffix not supported on Vertex)
model: 'claude-sonnet-4-6'
```

### SDK Selection

Use `@anthropic-ai/vertex-sdk`, **NOT** `@google-cloud/vertexai`:

```bash
npm install @anthropic-ai/vertex-sdk
```

The `@google-cloud/vertexai` package uses the wrong publisher path for Claude models and will fail with auth or routing errors.

**Publisher path:** Claude models live at `publishers/anthropic`, not `publishers/google`.

### anthropic_beta Header

Must be passed as an array in the request **body** — NOT as an HTTP header:

```typescript
// ✅ Correct: array in body
client.messages.create({
  model: 'claude-sonnet-4-5',
  max_tokens: 8000,
  anthropic_beta: ['interleaved-thinking-2025-05-14'],  // ← body, not header
  messages: [...]
});

// ❌ Wrong: HTTP header
headers: { 'anthropic-beta': 'interleaved-thinking-2025-05-14' }
```

### thinking Parameter

`{ type: 'adaptive' }` is **NOT** supported on Vertex. Use explicit `enabled` with a budget:

```typescript
// ✅ Correct for Vertex
thinking: { type: 'enabled', budget_tokens: 10000 }

// ❌ Not supported on Vertex
thinking: { type: 'adaptive' }
```

## Authentication

Standard GCP application default credentials work:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

The Vertex SDK picks up ADC automatically. No explicit token management needed for local development.

**`gspace auth` and `gcloud auth application-default login` write the same on-disk ADC file**
(`~/.config/gcloud/application_default_credentials.json`). If ADC is missing a specific scope
(e.g. `sqlservice.login` for Cloud SQL IAM auth), widening `gspace`'s own requested-scope list and
re-running its OAuth flow is a legitimate alternative to a raw `gcloud auth application-default
login --scopes=...` re-auth — but only once the scope has actually been added to gspace's request
list. Don't assume a narrow scope is covered just because the broad `cloud-platform` scope is
already present; check `gspace_check_auth`'s actual scope list for the specific scope needed before
relying on it. (detail: memory "reference_gspace_gcloud_shared_adc_credential")

## Cloud SQL — Schema-Level Grants Don't Cascade to Tables

`GRANT ALL PRIVILEGES ON SCHEMA public TO <role>` only grants `CREATE`/`USAGE` on the schema
itself — it does **not** cascade to privileges on tables that already exist inside it. A role with
this grant can still get `permission denied for table` on every DML statement against
pre-existing tables.

Compounding trap: Cloud SQL's `postgres`/`cloudsqlsuperuser` role is **not** a true Postgres
superuser — it cannot `GRANT` on a table it doesn't own, even though it otherwise behaves like one.
If migration DDL originally ran as a different IAM identity (e.g. a specific `user@domain.com`),
that identity owns the tables, and only it (or a role it grants) can fix table-level access.

**Fix:** connect as the actual table-owning IAM identity and run explicit table-level grants, plus
default privileges so future tables inherit them automatically:

```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "<role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "<role>";
```

(detail: memory "reference_cloudsql_schema_grant_not_cascading_to_tables")

## Secret Manager — Env Var Injection Includes Raw Bytes

When Cloud Run (or any GCP service) injects a Secret Manager secret as an environment variable, the raw bytes are used verbatim — including any trailing newline if the secret was stored with one.

`os.environ.get("MY_SECRET")` returns `"value\n"` not `"value"`. This causes silent bugs: API validators that check token length reject the value; string comparisons fail; authentication breaks.

**Store secrets without trailing newlines:**

```bash
# Wrong — echo appends \n
echo "my-token" | gcloud secrets versions add my-secret --data-file=-

# Wrong — jq -r also appends \n (the most common real-world trigger: extracting
# a client_secret/private_key field from a downloaded OAuth or service-account
# JSON file and piping it straight into gcloud)
jq -r '.web.client_secret' client_secret.json | gcloud secrets create my-secret --data-file=-

# Correct
printf '%s' "my-token" | gcloud secrets versions add my-secret --data-file=-
echo -n "my-token" | gcloud secrets versions add my-secret --data-file=-
jq -rj '.web.client_secret' client_secret.json | gcloud secrets create my-secret --data-file=-
```

**Verify:** `gcloud secrets versions access latest --secret=NAME | wc -c` should equal exactly the token length (no +1).

**In Python**, `.strip()` secrets from env when used in length-sensitive or comparison contexts:

```python
token = os.environ.get("MY_SECRET", "").strip()
```


## Cloud Run Job Creation — Secret Version Required at Deployment Time

When a `google_cloud_run_v2_job` Terraform/OpenTofu resource mounts a Secret Manager secret as an env var (`value_source.secret_key_ref`), GCP validates that the secret version exists at job *creation* time — not at execution time. If the secret resource exists but has no versions yet (just created by TF, not yet populated), the job creation fails with:

```
Permission denied on secret: projects/.../secrets/<name>/versions/latest for Revision service account ...
```

This also fails even if the IAM binding (`secretmanager.secretAccessor`) was just created in the same `tofu apply` run — GCP IAM propagation lag means the binding may not have taken effect before the job creation validation runs.

**The fix:** Omit the secret env var from the TF `google_cloud_run_v2_job` resource entirely. Manage it outside TF with:

```bash
# 1. Populate the secret version first
gcloud secrets versions add <secret-name> --data-file=- <<< "$VALUE"

# 2. Wire the mount onto the job
gcloud run jobs update <job-name> \
  --update-secrets ENV_VAR_NAME=<secret-name>:latest \
  --region <region> --project <project>
```

Use `lifecycle { ignore_changes = [...containers[0].env] }` on the Cloud Run Job resource so TF doesn't clobber the secret mount on subsequent applies.

## Cloud Monitoring — `notification_rate_limit` Only for Log-Based Alerts

`alert_strategy.notification_rate_limit` inside `google_monitoring_alert_policy` (Terraform / OpenTofu) is **only valid for log-based alert policies**. Applying it to metric-based policies returns HTTP 400:

```
Error creating AlertPolicy: googleapi: Error 400: Field alertStrategy.notificationRateLimit
had an invalid value: only log-based alert policies may specify a notification rate limit
```

**Fix:** omit the `alert_strategy` block entirely for metric-based policies (e.g., alerting on Cloud Run `completed_execution_count`):

```hcl
# ❌ Wrong for metric-based
resource "google_monitoring_alert_policy" "my_alert" {
  alert_strategy {
    notification_rate_limit {
      period = "3600s"
    }
  }
}

# ✅ Correct — no alert_strategy for metric-based
resource "google_monitoring_alert_policy" "my_alert" {
  display_name = "My Alert"
  combiner     = "OR"
  conditions { ... }
  notification_channels = [...]
}
```

## BigQuery + Vertex AI

When combining BigQuery data with Vertex AI Claude calls, prefer the `bigquery` CLI skill for queries and pass results as structured context in the Claude API request body.

## Cloud Run IAM Roles for Deploy Automation

Distinguish these three roles precisely when granting any automation identity (CI service account, another Cloud Run service's SA, etc.) access to deploy or invoke Cloud Run — they are commonly conflated and each under- or over-provisioning shows up as a different failure:

- **`roles/run.developer`** (scoped to the specific service/job) — required to *deploy*: `gcloud run deploy` / `gcloud run jobs update`, including changing the image, env vars, or resource limits. Does not include invoking a Job with per-run argument overrides.
- **`roles/run.invoker`** (scoped to the specific service/job) — required only to *call* an already-deployed service or trigger an already-deployed job with its existing configuration. Insufficient for deploy.
- **`roles/iam.serviceAccountUser`** on the *runtime* service account (not the automation identity's own SA) — required alongside `run.developer` whenever the deploy command needs to keep an existing runtime identity attached to the resource. Without this, deploy fails trying to re-set the service/job's own SA, even though the automation identity isn't changing anything about the SA itself.

For the Workload Identity Federation (keyless OIDC) setup that a GitHub Actions runner needs to hold `run.developer` in the first place, see the `github-actions` skill — that skill covers the WIF pool/provider Terraform and the workflow-side auth step; this section is the GCP-side role vocabulary those grants use.

## Ephemeral Cloud Run Job for One-off Server-Side GCS Analysis

When a one-off analysis needs to read a GCS bucket too large to download locally (tens of GB/day
across many days), don't download it — run a scoped, disposable Cloud Run Job against it and tear
the job down afterward:

1. If the bucket lives in a different project than your deploy target, that's a cross-project IAM
   grant and needs explicit user approval first — not a same-project additive apply (see the
   infra-apply-approval-scope rule).
2. Create a **new, dedicated** service account for this job only — never the shared default
   compute SA — and grant it read access (`roles/storage.objectViewer`) on the **specific bucket
   only**, not project-wide.
3. Stream directly against GCS (`gsutil cat` piped to your processor) — nothing should land on
   local disk or in a persistent bucket. Parallelize with one task per unit of work.
4. After collecting results, delete the job, the service account, and the IAM binding, and
   **independently verify each deletion** (`gcloud run jobs describe` → not found,
   `gcloud iam service-accounts list` → zero matches, `gsutil iam get` on the bucket → binding
   gone) rather than trusting a sub-agent's cleanup report.

(detail: memory "project_ep67_cloud_run_ephemeral_analysis_job")

## Cloud Run — Multi-Container & Job Gotchas

Discovered self-hosting OSRM + Nominatim on Cloud Run (Jobs + Services, multi-container, Cloud SQL-backed):

- **Cloud Run's native `cloud_sql_instance` volume mount does NOT perform IAM database authentication** — using it alone against a Cloud SQL instance configured for `CLOUD_IAM_SERVICE_ACCOUNT` auth produces an infinite password-prompt retry loop with zero progress. Add an explicit **Cloud SQL Auth Proxy sidecar container** instead (`gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.0`, args `["--auto-iam-authn", "--address=0.0.0.0", "--port=5432", <connection_name>]`); the app container then connects to `127.0.0.1:5432`. The `--address=0.0.0.0` is required — the proxy binds `127.0.0.1` by default, which Cloud Run's own container-level `startup_probe` (a separate process, even within the same task) cannot reach.
- **Multi-container tasks have three interacting resource caps**: total CPU across all containers in a task is capped at 8000 millicpu (a 6+1 vCPU split works, 8+1 doesn't); CPU must be a discrete value from a fixed set (`.08-1`, `1`, `2`, `4`, `6`, `8` — `7` is rejected); and there's a CPU-to-memory ratio ceiling (6 vCPU → max 24Gi, not simply "however much you asked for").
- **`gcloud run jobs update`/`execute` flag ordering for multi-container jobs**: `--container <name>` must precede `--image <image>`; non-container-specific flags (`--async`) must precede `--container`, container-specific flags (`--update-env-vars`/`--args`) must follow it.
- **A Cloud Run Job execution's `timeout` is fixed at launch from the job spec at that moment** — widening the Terraform-managed `timeout` field and re-applying does NOT retroactively extend an already-running execution, only future ones. A killed in-flight execution must be re-launched (ideally via the workload's own resume mechanism, if it has one), not just waited on longer after the config fix lands.
- **`gcloud run jobs execute <job> --args=<value>` REPLACES the job's entire container `args` array** — it does not append to or override just one element. A job whose default `args` embeds a script/entrypoint path (e.g. `["path/to/main.ts", "refresh"]`, common for a `tsx`-run TypeScript job) loses that path entirely if you pass a bare subcommand override (`--args=migrate`) — the container then fails with something like `ERR_MODULE_NOT_FOUND: Cannot find module '/app/migrate'`. gcloud accepts the flag without any warning, so the failure only surfaces after the job's own cold start, in the execution's logs. **Fix:** read the job's actual default `args` (its Terraform/YAML spec, or `gcloud run jobs describe --format='value(spec.template.spec.template.spec.containers[0].args)'`) and pass the full array back, comma-separated: `--args="path/to/main.ts,migrate"`.

(detail: memory "project_usps_route_cloudrun_multicontainer_gotchas", "project_gcloud_run_jobs_args_full_array_gotcha")

**Cloud Run does not redeploy on a bare image push.** Pushing a new `:latest` tag to Artifact Registry does not create a new revision — Cloud Run only redeploys when a `gcloud run deploy`/`jobs update` command actually runs with a resolved image reference. Prefer deploying by content digest (`@sha256:...`) over `:latest` — it makes "what's actually serving" independently verifiable (`gcloud run services describe --format='value(status.latestReadyRevision... image)'` compared against what was just pushed) rather than trusted on faith. If Terraform also manages the same resource with a floating-tag `image` value, expect `tofu plan` to show drift after any out-of-band digest deploy — that's expected divergence between two different deploy mechanisms touching the same field, not a misconfiguration to chase down.
