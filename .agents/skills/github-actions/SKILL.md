---
name: github-actions
description: GitHub Actions workflow design for deploying to GCP — Workload Identity Federation (keyless OIDC), per-resource least-privilege IAM, path-filtered multi-workflow layouts, and digest-based Cloud Run deploys. Use when creating or editing .github/workflows/*.yml that build/push images or deploy to GCP, when setting up CI auth to a cloud provider, or when a workflow needs to trigger on specific file paths for one of several deployable components in the same repo.
---

# GitHub Actions

For GCP deployment workflows, use keyless OIDC federation, scope trust to the intended repository and protected ref, grant deployment permissions per resource, and deploy Cloud Run images by digest. Preserve the target project’s infrastructure ownership and publication authority.

Read the relevant references before changing a workflow or its authentication:

| Task | Read |
| --- | --- |
| Workload Identity Federation, shared pools, runtime service accounts, least-privilege grants | [GCP authentication](references/gcp-authentication.md) |
| Independent deployable components, path filters, image digests, IaC drift | [Deployment layout](references/deployment-layout.md) |
| Step ordering, actual execution evidence, missing ambient credentials | [Runtime verification](references/runtime-verification.md) |
| Pending runs with no jobs, concurrency, approvals, billing, runner availability | [Queued runs](references/queued-runs.md) |

Static review does not establish that a workflow executes correctly. Observe an authorized real run and verify the deployed artifact when deployment is in scope; report an unavailable run as a validation gap. Do not infer live deployment from a successful build or image push.
