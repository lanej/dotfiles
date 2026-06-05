# DORA Data Pipeline Reference

## Quick-Start Commands

```bash
just refresh              # Full incremental refresh (EasyPost + Enterprise in parallel)
just refresh 2026-01-01   # Full refresh from a specific date (all resources)
just refresh-enterprise   # Enterprise (ADO) only
just verify-attribution   # Sanity-check identity; exits 1 on hard failures
```

## Pipeline Architecture

`just refresh` runs two scripts in parallel:

**EasyPost pipeline** (`scripts/refresh.sh`):
- Deployments — SSH to `adhoc` host → MySQL on `dblb:36060` (deploy-monitor)
- Flux deployments — GitHub API (kubernetes-*-shared repos)
- GitHub deployments — GitHub Deployments API (wesupplylabs repos)
- Revisions + commits — Phabricator API + GitHub `gh` CLI
- Bugs — Phabricator tasks + Jira JQL
- Alerts — PagerDuty `pd` CLI
- Revision reviews — Phabricator + GitHub review events
- Commit stats + PR size — GitHub API (set-difference incremental; not date-gated)
- Task events (Jira, Phab, ADO)

**Enterprise pipeline** (`scripts/refresh-enterprise.sh`):
- Azure DevOps commits, PRs, bugs — `az` CLI across both orgs
- CLS deployments — Slack #enterprise-releases channel scrape
- ADO task-to-PR links

Both pipelines auto-detect the latest date in BQ for each resource and only fetch new data. Downloads run in parallel, then uploads run in parallel.

**Enterprise cooldown**: refresh-enterprise has a 4-hour cooldown. Override: `ENTERPRISE_FORCE=1 just refresh-enterprise`.

## Upload CLI Taxonomy

Three distinct CLIs are used — choosing the wrong one will fail silently or error:

| CLI | When to use | Notes |
|-----|-------------|-------|
| `bq load --replace` | **Curated reference tables** (full replacement): `unified_identity_history`, `teams`, `team_code_aliases`, `*_team_mapping`, `jira_project_teams`, `pagerduty_users`, `former_employee_teams`, `phab_project_teams`, `team_membership_changelog` | Google CLI (`bq`); requires schema JSON as 3rd arg; `--source_format=NEWLINE_DELIMITED_JSON --replace` |
| `bigquery tables insert --format jsonl --yes` | **Append-only raw table ingestion** (`DORA_raw.*`): revisions, commits, bugs, alerts, deployments, ADO commits/PRs/bugs, task events, PR size, commit stats | EasyPost CLI; `--yes` required for non-interactive; scripts chunk large files before insert |
| `bigquery tables load` | **Large batch loads to raw tables**: alert_acknowledgers | EasyPost CLI; `--yes` is **NOT valid** (non-interactive by default) |

`bq load` example (Justfile pattern):
```bash
bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --replace \
  easypost-platform:DORA.teams \
  data/teams.json \
  infra/schemas/teams_schema.json
```

`bigquery tables insert` example (script pattern):
```bash
bigquery tables insert --format jsonl --yes easypost-platform.DORA_raw.bugs_raw data/bugs.jsonl
```

## Just Command Reference

### Pipeline
```bash
just refresh [SINCE]              # Full refresh; SINCE optional (auto-detects per resource)
just refresh-enterprise [SINCE]   # Enterprise only; 4h cooldown
just verify-attribution           # Run after any identity refresh; exits 1 on hard failures
```

### Identity / Teams (infrequent)
```bash
just download-unified-identity && just upload-unified-identity
  # upload-unified-identity automatically calls just verify-attribution

just download-team-registry && just upload-teams && just upload-team-code-aliases
just download-team-registry && just upload-incident-team-mapping && just upload-pagerduty-team-mapping
just download-team-membership-changelog && just upload-team-membership-changelog
```

### Infrastructure
```bash
just fmt                          # Format HCL
just validate                     # Validate OpenTofu config
just plan                         # Preview changes
just build-schemas                # Regenerate *_schema.json from infra/schemas/*.yml
just check-schema-drift           # Verify JSON matches YAML (CI drift check)
just gen-data-dictionary          # Regenerate schema column tables in docs/
```

### Reporting
```bash
just report-deployment-staleness [RISK_LEVEL]
just generate-charts
just generate-team-report TEAM
just generate-all-team-reports
```

### Per-resource download/upload pairs
```bash
just download-deployments SINCE && just upload_deployments
just download-revisions-with-metadata SINCE && just upload_revisions-with-metadata
just download-bugs SINCE && just upload_bugs
just fetch_alerts SINCE && just upload_alerts
just download-revision-reviews SINCE && just upload-revision-reviews
just download-flux-deployments SINCE && just upload-flux-deployments
just download-github-deployments SINCE && just upload-github-deployments
just download-azure-commits SINCE && just upload-azure-commits
just download-azure-prs SINCE && just upload-azure-prs
just download-cls-deployments SINCE && just upload-cls-deployments
just download-ado-task-pr-links SINCE && just upload-ado-task-pr-links
```

## Troubleshooting

**SSH / Duo MFA exit 255 on `download-deployments`**: Transient Duo rejection from simultaneous connections. Re-run — the script is idempotent. Not a credential issue.

**Enterprise 4h cooldown**: `ENTERPRISE_FORCE=1 just refresh-enterprise` bypasses it.

**BigQuery load failures**: Check schema mismatches. Run `just check-schema-drift` — JSON schema may have drifted from YAML source if `build-schemas` was skipped.

**Upload API errors on large files**: `bigquery tables insert` chunks automatically in scripts. If a manual insert fails with row-count errors, use `bigquery tables load` instead (no row limit).
