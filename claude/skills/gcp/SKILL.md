---
name: gcp
description: Google Cloud Platform and Vertex AI patterns, quirks, and SDK usage for Claude/Anthropic models on Vertex AI. Use when working with GCP, Vertex AI, the Anthropic Vertex SDK, or deploying Claude models on Google Cloud.
---

# GCP / Vertex AI Skill

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
