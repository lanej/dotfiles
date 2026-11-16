# Monitoring and billing

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

## Cost-Attribution Labels — Per-Resource-Type Gotchas

`labels` don't reach Cloud Billing uniformly:

- **`google_dataplex_asset` on a BQ dataset strips that dataset's own Terraform labels** (provider issue #13198) — label the asset, not the dataset.
- **Cloud Run billing reads only `template.labels`** (`google_cloud_run_v2_service`/`_job`); a top-level `labels` shows in the Console, never in billing export.
- **`google_bigquery_data_transfer_config`/`TransferRun` and `google_cloud_scheduler_job` have no `labels` field.** Billing export carries BQ *job* labels, not dataset labels — lead a scheduled query's script with `SET @@query_label = "component:<name>";`.
- **A Terraform/OPA cost policy sees only `tofu plan` JSON** — a runtime client-library job (`createQueryJob({ query })`) is invisible however declared resources are labeled; the fix is app-code `job.labels`, not a stronger policy.

(detail: memory "project_dataplex_billing_label_cost_attribution_gotchas")
