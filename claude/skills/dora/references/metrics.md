# DORA Metrics — BigQuery Reference

## Query Workflow

Always dry-run before executing:
```bash
# MCP
mcp__bigquery__dry_run(query="SELECT ...")

# CLI
bigquery dry-run "SELECT ..."
```

## Primary Views — Four DORA Pillars

### Deployment Frequency

| View | Purpose | When to use |
|------|---------|-------------|
| `DORA.deployment_frequency_weekly` | Weekly deploy counts + service diversity | Weekly DORA reporting |
| `DORA.deployment_frequency` | Daily deployment counts (deploy-monitor + Flux + GitHub) | Daily trend analysis |
| `DORA.user_deployments` | User-initiated deploys with outlier filtering | Team-level attribution |
| `DORA.first_user_deployments` | First deployment per commit SHA | De-duplicated commit→deploy mapping |
| `DORA.latest_deployments_by_service` | Latest deploy per service + staleness risk | Deployment health monitoring |
| `DORA.stale_production_services` | Active services with stale deployments | Risk assessment |

EasyPost pipeline: deploy-monitor (SSH→MySQL), Flux GitOps (kubernetes-*-shared repos), GitHub Deployments API (wesupplylabs repos).

### Lead Time for Changes

| View | Purpose | When to use |
|------|---------|-------------|
| `DORA.changes` | Complete change records with lead time | Detailed change analysis, primary join target |
| `DORA.changes_lead_time_with_moving_avg_overall` | Org-wide lead time trends (30/60/90/180/365d rolling) | Overall performance tracking |
| `DORA.changes_lead_time_with_moving_avg_per_author` | Author-level rolling averages | Individual developer performance |
| `DORA.changes_lead_time_with_moving_avg_per_service` | Service-level rolling averages | Service health monitoring |
| `DORA.revisions_with_lead_time` | Revisions enriched with lead time | Source-level lead time analysis |

`changes` joins: `DORA_clean.revisions` → `DORA_clean.revision_commits` → `DORA_clean.deployments`. Lead time = first deploy timestamp − first commit timestamp.

### Change Failure Rate

| View | Purpose | When to use |
|------|---------|-------------|
| `DORA.change_failure_rate_by_team` | Monthly CFR per team = (incidents + bugs) / deployments | Team CFR reporting |
| `DORA.change_failure_rates` | Org-wide monthly CFR aggregate | Overall CFR trend |
| `DORA.bugs_by_team` | Bugs with team attribution via Phab projects + Jira project keys | Bug attribution |
| `DORA.incidents_by_team` | Post-mortems with team attribution | Incident attribution |
| `DORA_clean.bugs` | Deduplicated bug records (Phab + Jira) | Direct bug queries |

`change_failure_rate_by_team` joins `deployments_by_team`, `incidents_by_team`, and `bugs_by_team` on column names — a column rename in any of these breaks CFR silently.

### Alerts (Stability)

| View | Purpose | When to use |
|------|---------|-------------|
| `DORA.technical_alerts` | Alerts filtered to technical only (excludes customer_escalation, partner_support, it_workflow) | Actionability analysis |
| `DORA.alerts_flat` | Single-row format with segmentation fields + ack latency | Dashboard queries |
| `DORA.alert_health_by_team` | Monthly metrics per PagerDuty team with DORA team mapping | Team on-call health |
| `DORA.alerts_by_responder` | Alert acknowledgments per engineer | Individual on-call load |
| `DORA.responder_load_by_month` | Monthly on-call load per person | Burn rate monitoring |
| `DORA.alerts_with_service_attribution` | Raw alerts with service extraction (15 strategies, priority chain) | Service-level alert routing |

## Secondary Views (Navigation Table)

These views exist but have no non-obvious gotchas beyond the standard rules:

| Area | Primary views |
|------|--------------|
| Review time | `DORA.first_human_review`, `DORA.last_approval`, `DORA.time_to_first_review_by_team`, `DORA.time_to_approval_by_team`, `DORA.revision_review_outcomes` |
| Risk assessment | `DORA.risk_assessment_daily` |
| Task events | `DORA.task_event_durations`, `DORA_clean.task_events` |
| Repository ownership | `DORA.repository_owners`, `DORA.repositories` |
| PR size | `DORA_clean.revision_pr_size_raw` (use `file_stats_fetched_at IS NOT NULL` for rows with full breakdown) |
| AI attribution | `DORA.ai_attribution_*` (see data dictionary for current view list) |
| Enterprise metrics | See `references/enterprise.md` |

## Common Query Patterns

### Team filter (EasyPost pipeline)

```sql
JOIN `easypost-platform.DORA.unified_identity` ui
  ON ui.email_prefix = LOWER(REGEXP_EXTRACT(author_email, r'^[^@+]+'))
WHERE ui.team = 'Platform'
```

Or filter on `dora_team_name` column directly in pre-attributed views:
```sql
WHERE dora_team_name = 'Platform'
```

### Date filter

```sql
WHERE DATE(started_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  AND DATE(started_at) < CURRENT_DATE()
```

### Deployment frequency — 30-day window

```sql
SELECT
  DATE_TRUNC(deploy_date, WEEK) AS week,
  SUM(total_deployments) AS deploys,
  AVG(unique_services) AS avg_services
FROM `easypost-platform.DORA.deployment_frequency_weekly`
WHERE deploy_week >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 WEEK)
GROUP BY week
ORDER BY week
```

### Lead time — org-wide 90d rolling

```sql
SELECT date, moving_avg_90d_days
FROM `easypost-platform.DORA.changes_lead_time_with_moving_avg_overall`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
ORDER BY date
```

### CFR by team — last 6 months

```sql
SELECT team_name, month, change_failure_rate
FROM `easypost-platform.DORA.change_failure_rate_by_team`
WHERE month >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH), MONTH)
ORDER BY team_name, month
```

## Pipeline Split

EasyPost (Phab + GitHub) and Enterprise (Azure DevOps) are separate pipelines with separate views. Most top-level `DORA.*` views cover the EasyPost pipeline only. For ADO metrics, see `references/enterprise.md` and query `DORA.azure_devops_*` or `DORA_clean.azure_devops_*` views.
