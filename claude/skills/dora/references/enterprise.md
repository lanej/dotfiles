# DORA Enterprise / Azure DevOps Reference

## Two ADO Organizations

All enterprise download scripts query **both orgs**:

| Org URL | ADO Projects |
|---------|-------------|
| `https://dev.azure.com/creativelogistics` | `Vx` |
| `https://dev.azure.com/easypost-enterprise` | `GlobalShip`, `Core`, `Public APIs` |

Any query, `az` CLI invocation, or analysis that covers enterprise engineers must include both orgs. A single-org query will silently miss the other population.

## Primary Tables

| Table | Purpose | Notes |
|-------|---------|-------|
| `DORA_clean.azure_devops_pr_analytics` | Deduplicated PR records | Primary query target for ADO PRs |
| `DORA_clean.azure_devops_git_commits` | Deduplicated commits from both orgs | |
| `DORA_clean.azure_devops_bugs` | Deduplicated ADO bug records | |
| `DORA_clean.azure_devops_change_failures` | Change failure classification | |
| `DORA_clean.azure_devops_pr_reviewers` | Per-reviewer rows for each PR | |
| `DORA_clean.ado_task_pr_links` | ADO work item → PR explicit developer links | Dedup key: source + org + repo + pr_id + task_id |
| `DORA_clean.cls_deployments` | Enterprise deployment events from Slack #enterprise-releases | |

## Analytical Views

| View | Purpose |
|------|---------|
| `DORA.azure_devops_pr_commits_reviewers` | PRs joined with commits and reviewers; includes `lead_time_hours`, `lead_time_days` |
| `DORA.azure_devops_pr_commits_reviewers_normalized` | Normalized IDs with email prefix extraction |
| `DORA.azure_devops_ticket_links` | Jira ticket keys extracted from PR titles |
| `DORA.ado_task_pr_details` | Enriched view: work items linked to PRs with full metadata and unified_identity join |
| `DORA.azure_devops_bug_commit_correlation` | Bugs correlated by explicit reference, PR reference, or time-based proximity (within 7 days) |

## ADO Email Join Pattern (Critical)

```sql
ON LOWER(REGEXP_EXTRACT(author_email, r'^[^@+]+')) = ui.email_prefix
```

The `+` in `[^@+]+` is required. It strips email tags:
- `dwest+cls@easypost.com` → `dwest`
- Using `r'^[^@]+'` silently drops these addresses

This pattern is used in `enterprise_views.tf` for all identity joins:
- `azure_devops_pr_commits_reviewers`: commit `author_email` → `email_prefix`
- `ado_task_pr_details`: PR `createdByEmail` → `email_prefix`

## EPS/EINTK Work Composition

For IC work composition on EPS engineers, PRs must flow through `ado_task_pr_links` (ADO work item → PR explicit developer links). EPS uses ADO, not Phabricator, so the standard `DORA_clean.jira_pr_links` path does not apply.

| Source | What it provides |
|--------|-----------------|
| `DORA_clean.ado_task_pr_links` | Explicit ADO work item → PR links (from ADO API `$expand=relations`) |
| `DORA.ado_task_pr_details` | Enriched: work items + PR metadata + unified_identity |
| `DORA_clean.jira_pr_links` | Jira dev-status PR links (EasyPost Phab/GitHub engineers) |
| `DORA_clean.jira_description_prs` | GitHub PR URLs extracted from Jira issue descriptions (unlinked PR pattern) |

## CLS Deployments

Enterprise deployment events are sourced from Slack #enterprise-releases channel and stored in `DORA_clean.cls_deployments`. Refresh:

```bash
just download-cls-deployments SINCE && just upload-cls-deployments
```

## Enterprise Pipeline Refresh

```bash
just refresh-enterprise [SINCE]
```

Cooldown: 4 hours by default. Override:
```bash
ENTERPRISE_FORCE=1 just refresh-enterprise
```

Enterprise refresh covers: ADO commits, ADO PRs (+ reviewers), CLS deployments, ADO task-to-PR links.

ADO bugs are NOT in the automatic refresh — download separately if needed:
```bash
just download-azure-bugs SINCE && just upload-azure-bugs
```

## az CLI Pattern

```bash
az rest \
  --method GET \
  --uri "https://dev.azure.com/{org}/{project}/_apis/..." \
  --resource 499b84ac-1321-427f-aa17-267ca6975798 \
  --output json
```

The `--resource` GUID is the Azure DevOps resource ID — required for auth. Scripts iterate over both orgs and all projects within each org.
