---
name: github-actions
description: Use when authoring, formatting, or reviewing GitHub Actions workflows, including component path filters and GCP deployment authentication and permissions.
---

# GitHub Actions

Prefer expanded block-style YAML: put each sequence item on its own line, including single-item lists, and expand mappings rather than using inline flow collections. Apply this to triggers, branches, paths, runner labels, and matrix values so diffs isolate each change. Preserve the nesting required by the workflow schema.

For GCP deployment workflows, use keyless OIDC federation, scope trust to the intended repository and protected ref, grant deployment permissions per resource, and deploy Cloud Run images by digest. Preserve the target project’s infrastructure ownership and publication authority.

Read the relevant references before changing a workflow or its authentication:

| Task | Read |
| --- | --- |
| Workload Identity Federation, shared pools, runtime service accounts, least-privilege grants | [GCP authentication](references/gcp-authentication.md) |
| Independent deployable components, path filters, image digests, IaC drift | [Deployment layout](references/deployment-layout.md) |
| Step ordering, actual execution evidence, missing ambient credentials | [Runtime verification](references/runtime-verification.md) |
| Pending runs with no jobs, concurrency, approvals, billing, runner availability | [Queued runs](references/queued-runs.md) |

Static review does not establish that a workflow executes correctly. Observe an authorized real run and verify the deployed artifact when deployment is in scope; report an unavailable run as a validation gap. Do not infer live deployment from a successful build or image push.
