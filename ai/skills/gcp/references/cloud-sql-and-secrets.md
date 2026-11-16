# Cloud SQL and Secret Manager

## Cloud SQL — Schema-Level Grants Don't Cascade to Tables

`GRANT ALL PRIVILEGES ON SCHEMA public TO <role>` only grants `CREATE`/`USAGE` on the schema itself — it does **not** cascade to privileges on tables that already exist inside it. A role with this grant can still get `permission denied for table` on every DML statement against pre-existing tables.

Compounding trap: Cloud SQL's `postgres`/`cloudsqlsuperuser` role is **not** a true Postgres superuser — it cannot `GRANT` on a table it doesn't own, even though it otherwise behaves like one. If migration DDL originally ran as a different IAM identity (e.g. a specific `user@domain.com`), that identity owns the tables, and only it (or a role it grants) can fix table-level access.

**Fix:** connect as the actual table-owning IAM identity and run explicit table-level grants, plus default privileges so future tables inherit them automatically:

```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "<role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "<role>";
```

(detail: memory "reference_cloudsql_schema_grant_not_cascading_to_tables")

## Secret Manager — Env Var Injection Includes Raw Bytes

When Cloud Run (or any GCP service) injects a Secret Manager secret as an environment variable, the raw bytes are used verbatim — including any trailing newline if the secret was stored with one.

`os.environ.get("MY_SECRET")` returns `"value\n"` not `"value"`. This causes silent bugs: length validators reject the value, comparisons fail, auth breaks.

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

This also fails even if the IAM binding (`secretmanager.secretAccessor`) was created in the same `tofu apply` run — IAM propagation lag can leave it ineffective when the creation validation runs.

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
