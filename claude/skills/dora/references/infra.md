# DORA Infrastructure Reference

## Schema Authoring

**Canonical source: `infra/schemas/*.yml`** (YAML). The root-level `schemas/` directory does not exist — do not look there.

Generated files: `infra/schemas/*_schema.json` — never edit directly. `just build-schemas` regenerates them from YAML and will silently overwrite any manual edits.

### Field change workflow

1. Edit `infra/schemas/<table>_schema.yml`
2. `just build-schemas` — regenerate `*_schema.json`
3. `just check-schema-drift` — verify JSON matches YAML
4. `just gen-data-dictionary` — regenerate schema column tables in `docs/bigquery-data-dictionary.md`
5. Proceed with view/table workflow below

## View / Table Change Workflow

```bash
# 1. Edit the .tf file
# 2.
just fmt          # Format HCL
just validate     # Validate config
just plan         # Preview changes — review carefully
# 4.
tofu -chdir=infra apply -auto-approve   # Non-interactive apply
# (just apply also works but requires stdin confirmation)
```

After applying:
```bash
just ls                   # Verify resource appears in state
just verify-attribution   # Run if identity or team views changed
```

## Documentation Rule

**Always update `docs/bigquery-data-dictionary.md` in the same commit when you add, modify, or remove any table or view.** Two locations must be updated together:

1. **Table Categories** section (`## Table Categories`) — one-line entry in the appropriate subsection
2. **Detailed Table Reference** section — full entry with: type, purpose, source/depends-on, output columns (with types), sample query, known limitations

Run `just gen-data-dictionary` after schema changes — it regenerates the `**Schema:**` column tables from YAML automatically. Review and manually update any prose sections that refer to the changed columns.

## Column Rename Rule

Before renaming any output column in a DORA view:

```bash
grep -r 'old_column_name' infra/
```

`change_failure_rate_by_team` joins `deployments_by_team`, `incidents_by_team`, and `bugs_by_team` on column names — a silent rename in any of those breaks CFR completely. After deploying any rename, run `just verify-attribution`.

## File Organization

```
infra/
  main.tf                 # Datasets, repositories table, risk assessment views
  raw.tf                  # All DORA_raw append-only tables (dora_raw_* prefix)
  clean.tf                # All DORA_clean dedup views (clean_* prefix)
  deployments.tf          # Deployment frequency metrics
  lead_time.tf            # Lead time for changes metrics
  change_failure_rate.tf  # Bug and incident tracking
  alerts.tf               # PagerDuty alerts
  identity.tf             # unified_identity, teams, team_code_aliases, team_membership_changelog
  enterprise_tables.tf    # (empty — ADO tables moved to raw.tf)
  enterprise_views.tf     # Azure DevOps analytical views
  review_time.tf          # Time to first review / time to approval
  repository_ownership.tf # CODEOWNERS-based team attribution
  service_classifications.tf  # Service type classification
  schemas/                # YAML sources + generated JSON schemas
```

## Code Style

- SQL in views: heredoc syntax `<<-SQL ... SQL`
- Always reference by resource attribute: `${var.project_id}.${google_bigquery_dataset.dataset.dataset_id}.${google_bigquery_table.foo.table_id}` — never hardcode dataset/table names
- Raw input tables: `DORA_raw` dataset, `deletion_protection = true`, resource prefix `dora_raw_*`
- Clean dedup views: `DORA_clean` dataset, `deletion_protection = false`, resource prefix `clean_*`
- Analytical views + curated tables: `DORA` dataset; views have `deletion_protection = false`; critical curated tables have `deletion_protection = true`

## Adding a New Raw Table

1. Add resource to `infra/raw.tf` with `deletion_protection = true` and `dora_raw_` prefix
2. Add schema YAML to `infra/schemas/<table>_schema.yml`
3. `just build-schemas`
4. Add clean dedup view to `infra/clean.tf` with `clean_` prefix
5. Create upload script in `scripts/upload-<resource>.sh` using `bigquery tables insert --format jsonl --yes`
6. Add download script if needed
7. Add Justfile recipes for download + upload
8. Wire into `scripts/refresh.sh` if part of the incremental pipeline
9. Update `docs/bigquery-data-dictionary.md`

## State Operations

```bash
just ls           # List all resources in state
tofu -chdir=infra state list | grep <pattern>   # Filter resources
```

State is stored in GCS at `gs://ep-platform/metrics-opentofu-state`.
