# Workflow layout and artifact deployment

## Path-filtered multi-workflow layout

GitHub Actions has **no per-job path filter** — `on.push.paths` applies to the whole workflow file. If a repo deploys N independent components (e.g. a frontend+backend service and a separate worker job), don't try to cram them into one workflow with conditional job logic — write **one workflow file per deployable component**, each with its own `paths:` filter:

```yaml
# .github/workflows/deploy-service-a.yml
on:
  push:
    branches:
      - main
    paths:
      - 'src/service_a/**'
      - 'Dockerfile.service_a'

# .github/workflows/deploy-service-b.yml
on:
  push:
    branches:
      - main
    paths:
      - 'src/service_b/**'
      - 'Dockerfile.service_b'
```

A push touching both path sets triggers both workflows concurrently — that's correct and expected, not a race condition to guard against (each targets a different GCP resource).

**Verify path filtering actually works**, don't just trust the YAML: push a change to an explicitly out-of-scope path (e.g. a DAG file neither workflow should care about) and confirm neither workflow run appears in `gh run list`. Path filter bugs are easy to write (a too-broad glob, a missing leading `/`) and silent — they either over-trigger (wasted deploys) or under-trigger (a real change ships without a deploy) with no error either way.

## Digest-based Cloud Run deploy, not `:latest`

Build and push both a floating tag and a content-addressed digest, but **deploy by digest**:

```yaml
- name: Build and push
  run: |
    docker build -t "${IMAGE}:latest" -t "${IMAGE}:${{ github.sha }}" .
    docker push "${IMAGE}:latest"
    docker push "${IMAGE}:${{ github.sha }}"
    DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${IMAGE}:${{ github.sha }}" | cut -d'@' -f2)
    echo "digest=${DIGEST}" >> "$GITHUB_OUTPUT"

- name: Deploy
  run: |
    gcloud run deploy my-service --image="${IMAGE}@${{ steps.build.outputs.digest }}" --region=us-central1
```

Pushing a new `:latest` image alone does **not** trigger a new Cloud Run revision — Cloud Run only redeploys when the deploy command runs with a resolved reference. Deploying by digest (rather than `:latest`) also makes the deployed artifact byte-verifiable: after a workflow run, `gcloud run services describe`/`gcloud run jobs describe` and compare the serving image's digest against what the workflow pushed — an exact match is real end-to-end proof, "the workflow reported success" is not.

**Known, accepted drift**: if Terraform's `google_cloud_run_v2_service`/`_job` resource pins `image` to a floating tag (`:latest`) for its own initial-create/plan purposes, a CI deploy-by-digest will cause `tofu plan` to show drift on that field afterward. This is expected, not a bug — reconcile it the next time Terraform runs against that resource, don't try to make CI itself keep Terraform state in sync (that would require giving the CI SA far broader Terraform-apply permissions for no real benefit).
