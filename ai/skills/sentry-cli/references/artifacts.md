# Source maps and native debug symbols

## Source maps and debug symbols

For a JavaScript build that uses Debug IDs:

```bash
sentry-cli sourcemaps inject --dry-run ./dist
sentry-cli sourcemaps inject ./dist
sentry-cli sourcemaps upload --org example-org --project example-project ./dist --wait
```

Generate source maps first. Injection modifies local JavaScript and matching source maps, so apply it to the intended build output before upload and deployment. Ship those same injected artifacts; rebuilding afterward can break the match. If the build integration already injects Debug IDs, follow that integration's workflow.

For Debug ID uploads, `--release` and `--dist` are optional. Add them when the application's artifact workflow requires them, and match the SDK values exactly. Read the [source map upload guide](https://docs.sentry.io/platforms/javascript/sourcemaps/uploading/cli/) when configuring SDK or build compatibility, URL prefixes, or release-based matching.

For native debug information:

```bash
sentry-cli debug-files check ./path/to/debug-file
sentry-cli debug-files upload --org example-org --project example-project ./path/to/symbols --wait
```

Inspect upload output and processing errors. Successful upload and processing establish artifact availability; verify a matching event to establish that its stack trace is correctly symbolicated. `sourcemaps explain` is unavailable in 3.8.0; use current Sentry troubleshooting tools rather than older examples.
