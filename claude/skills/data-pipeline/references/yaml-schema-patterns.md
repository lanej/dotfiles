# YAML Schema Management for Data Pipelines

## Why YAML for Schemas

Prefer YAML files over inline SQL DDL or JSON for table schema definitions:

**Benefits:**
- **Version control friendly:** Line-by-line diffs, not one-line JSON blobs
- **Human readable:** Comments, clear structure, no escape sequences
- **Separation of concerns:** Schema definition (YAML) separate from infrastructure code (Terraform)
- **Tooling integration:** Linters, validators, documentation generators
- **Consistency:** One source of truth for schema across upload scripts, documentation, and infrastructure

**Use cases:**
- BigQuery table schemas in Terraform/OpenTofu
- dbt models (though dbt has its own YAML format)
- Data validation rules
- Pipeline configuration

## YAML Schema Structure (BigQuery Example)

```yaml
- name: key
  type: STRING
  mode: REQUIRED
  description: Unique identifier for the record

- name: created
  type: TIMESTAMP
  mode: NULLABLE
  description: Record creation timestamp

- name: tags
  type: STRING
  mode: REPEATED
  description: Array of tag values

- name: metadata
  type: RECORD
  mode: NULLABLE
  description: Nested metadata object
  fields:
    - name: source
      type: STRING
      mode: NULLABLE
      description: Source system identifier
```

## Terraform Integration Pattern

```hcl
resource "google_bigquery_table" "my_table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "my_table"
  
  # YAML → JSON conversion via Terraform functions
  schema = jsonencode(yamldecode(file("${path.module}/schemas/my_table.yml")))
  
  deletion_protection = true
}
```

**Gotcha:** Field order in YAML must match BigQuery's actual field order for drift detection (see opentofu skill for details).

## Workflow for Schema Changes

1. **Edit the YAML file** - Add/modify/remove field definitions
2. **Run schema generator** (if using one) - e.g., `just build-schemas` to generate JSON
3. **Plan infrastructure** - `terraform plan` or `tofu plan` to preview changes
4. **Apply changes** - `terraform apply` to update table schema
5. **Update upload scripts** - If adding fields, update jq filters or column mappings in upload logic
6. **Backfill or re-extract** - Populate new columns if needed

## Schema Validation

Include validation in CI/CD:

```bash
# Check YAML syntax
yamllint schemas/*.yml

# Verify generated JSON matches YAML (prevent drift)
./scripts/check-schema-drift.py

# Dry-run Terraform to catch schema errors early
terraform plan -detailed-exitcode
```

## Field Naming Conventions

- **snake_case** for all field names (not camelCase)
- **Past tense for timestamps:** `created_at`, `extracted_at`, not `create_date`
- **Explicit nullability:** Always specify `mode: NULLABLE` or `mode: REQUIRED`
- **Descriptive names:** `assignee` not `user_id` (unless it's actually an ID)

## Deprecation Pattern

Don't delete fields immediately — mark as deprecated:

```yaml
- name: old_field
  type: STRING
  mode: NULLABLE
  description: "DEPRECATED — use new_field instead. Retained for backward compatibility."
```

Then remove after a deprecation window (e.g., after all downstream consumers migrate).

## Schema Evolution

**Safe changes** (no data loss):
- Add nullable columns
- Widen types (INT64 → FLOAT64, STRING → TEXT)
- Add new tables

**Unsafe changes** (require migration):
- Delete columns
- Rename columns (better: add new column, deprecate old)
- Narrow types
- Change nullability (nullable → required)

For unsafe changes, use view-layer aliasing or staged migrations to avoid data loss.

## Multi-Source Schema Patterns

When multiple source systems feed one gold entity:

**Option 1: Shared base schema**
```yaml
# schemas/base_ticket.yml - common fields
- name: key
  type: STRING
  mode: REQUIRED

- name: summary
  type: STRING
  mode: NULLABLE
```

Then extend per-source with source-specific fields (include via tooling or manual composition).

**Option 2: Union schema**
All sources share one superset schema; unused fields are NULL for each source.

**Option 3: Separate source schemas**
Each source has its own schema; gold layer maps/joins them.

Engineering-demand uses Option 3 (separate YAML per source, gold layer joins).
