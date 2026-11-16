---
name: gcp
description: Use when working with GCP service behavior, authentication, IAM, Cloud Run, Cloud SQL, Secret Manager, monitoring, billing, Cloud Build, Workflows, or Anthropic models on Vertex AI.
---

# GCP

Use the service notes below for observed failure modes and operational details. Read only the references relevant to the task. Verify version-sensitive limits, model support, and workarounds against current official documentation before applying them; retain the target project’s authority and deployment rules.

| Task | Read |
| --- | --- |
| Claude on Vertex AI: SDK, model IDs, request parameters, BigQuery context | [Vertex AI](references/vertex-ai.md) |
| ADC scopes, Cloud Run deployment roles, BigQuery billing-project permissions | [Authentication and IAM](references/authentication-and-iam.md) |
| PostgreSQL grants, secret bytes, secret mounts at job creation | [Cloud SQL and Secret Manager](references/cloud-sql-and-secrets.md) |
| Alert rate limits and resource-specific cost labels | [Monitoring and billing](references/monitoring-and-billing.md) |
| Native IAP, ingress, service calls, disposable GCS analysis jobs | [Cloud Run access](references/cloud-run-access.md) |
| Cloud SQL proxy sidecars, container limits, job arguments, deployment verification | [Cloud Run jobs and deployments](references/cloud-run-jobs.md) |
| Build substitutions and workflow definition size | [Cloud Build and Workflows](references/cloud-build-and-workflows.md) |

Use `opentofu` for Terraform/OpenTofu resource authoring, `github-actions` for CI authentication and deployment workflows, and `bigquery` for query execution and cost discipline. This skill supplies GCP service details alongside that guidance.
