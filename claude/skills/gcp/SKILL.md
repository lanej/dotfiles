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

## Secret Manager — Env Var Injection Includes Raw Bytes

When Cloud Run (or any GCP service) injects a Secret Manager secret as an environment variable, the raw bytes are used verbatim — including any trailing newline if the secret was stored with one.

`os.environ.get("MY_SECRET")` returns `"value\n"` not `"value"`. This causes silent bugs: API validators that check token length reject the value; string comparisons fail; authentication breaks.

**Store secrets without trailing newlines:**

```bash
# Wrong — echo appends \n
echo "my-token" | gcloud secrets versions add my-secret --data-file=-

# Correct
printf '%s' "my-token" | gcloud secrets versions add my-secret --data-file=-
echo -n "my-token" | gcloud secrets versions add my-secret --data-file=-
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

**Cloud Run does not redeploy on a bare image push.** Pushing a new `:latest` tag to Artifact Registry does not create a new revision — Cloud Run only redeploys when a `gcloud run deploy`/`jobs update` command actually runs with a resolved image reference. Prefer deploying by content digest (`@sha256:...`) over `:latest` — it makes "what's actually serving" independently verifiable (`gcloud run services describe --format='value(status.latestReadyRevision... image)'` compared against what was just pushed) rather than trusted on faith. If Terraform also manages the same resource with a floating-tag `image` value, expect `tofu plan` to show drift after any out-of-band digest deploy — that's expected divergence between two different deploy mechanisms touching the same field, not a misconfiguration to chase down.
