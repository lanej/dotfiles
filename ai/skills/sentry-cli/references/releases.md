# Release and deployment records

## Releases and deployment records

```bash
sentry-cli releases list --org example-org --project example-project
sentry-cli releases info --org example-org --project example-project 'example-project@1.2.3'
sentry-cli deploys list --org example-org --project example-project --release 'example-project@1.2.3'
```

Releases are shared across an organization. Reuse the application's actual SDK release identifier; choose a project-specific identifier when independent projects otherwise share version names.

For an authorized release workflow, these are the individual steps:

```bash
sentry-cli releases new --org example-org --project example-project 'example-project@1.2.3'
sentry-cli releases set-commits --org example-org --project example-project 'example-project@1.2.3' --auto
sentry-cli releases finalize --org example-org --project example-project 'example-project@1.2.3'
sentry-cli deploys new --org example-org --project example-project \
  --release 'example-project@1.2.3' --env production
```

Use the steps required by the existing pipeline. `set-commits --auto` uses the current Git checkout; verify that it represents the release being recorded. For an explicit range, use `--commit 'owner/repo@previous-sha..current-sha'` with the repository name registered in Sentry. Diagnose missing history before using `--ignore-missing`, which changes the associated commit range.

In 3.8.0, deployments use top-level `deploys` commands. Creating a deployment record or finalizing a release changes Sentry metadata; it does not deploy application code or verify what is serving. Record a completed deployment only after the deployment workflow establishes its outcome, then verify the Sentry record with `deploys list` or `releases info`.
