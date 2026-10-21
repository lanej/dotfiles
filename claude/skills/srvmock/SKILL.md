---
name: srvmock
description: Use srvmock to reproduce EP Services deployments locally, inspect packaged configuration, and run acceptance, benchmark, load, or process-recovery checks. Use when deploying a service or PR-stack tip on a development VM through its production deploy-hooks.
---

# srvmock

Use the installed `srvmock --help` and deployment hooks as the authority for the
host's implementation. The tool builds and activates service artifacts through
`srvenv` and Supervisor; it is not a generic container runner.

## Source and isolation

- Pin the requested source commit. Ordinary builds use committed source from
  the selected branch; uncommitted source changes are excluded.
- The tested implementation puts the branch name directly in version-directory
  names. Use a flat, named branch without `/` for the srvmock checkout.
- Service state is isolated by service name, not by checkout. The default name
  is the checkout directory basename. `git config srvmock.servicename NAME`
  overrides it, but Git configuration can be shared between worktrees. Prefer
  a uniquely named task checkout when that supplies the correct service name.
- Choose unused ports and service-specific sockets, readiness files, and logs.
  Inspect existing deployments before activation or process-recovery tests.
  Align port-dependent test URLs too: AVCass's `CANARY_URL` must target the
  same instance as `PORT`, rather than a previous deployment.
- The tested host requires a development VM hostname ending in
  `devvm.easypo.net`, installed Supervisor/srvenv tooling, and sudo for service
  registration and `/srv` setup.

## Configuration

`srvmock config` displays the effective configuration. It has no `config set`
interface; remote `srvctl SERVICE config set KEY=VALUE` is a different command.

Edit the local ignored `.env-override` before building. Srvmock reads that file
and `.env-secrets` from the invoking checkout, appends their contents to the
generated `.env-runtime`, and packages the generated environment with the
service. The override file itself need not appear in the deployed version.
Configuration changes require a new build. Verify selected values inside the
active service, rather than assuming the working checkout is its configuration:

```sh
srvmock shell -c 'printenv PORT AMS_RELEASES GEOCODE_DB'
```

Avoid dumping credential-bearing configuration when only selected values are
needed. Mock deployments change `HOME`; use absolute canonical paths for shared
data and toolchains when required.

## Production build behavior

Deploy hooks already execute inside `srvenv`. Invoke build tools directly;
development `withenv` explicitly rejects nesting inside `srvenv`.

Srvmock removes `.git` metadata before the build hook. Applications that stamp
immutable source artifacts need a source identity supplied by their build
interface, not a Git lookup in the stripped snapshot.

For AVCass, set `AVCASS_SOURCE_COMMIT` in `.env-override` to the full lowercase
SHA returned by `git rev-parse HEAD`. Refresh it after source commits change.
The archive build checks it against srvmock's `.revhash` prefix. Checkout builds
still require clean schema inputs and an exact HEAD match; do not bypass those
checks or fabricate a full SHA from a short revision.

Read the service's post-deploy hook before activation. For AVCass it runs the
dataset downloader and cleanup. Point `AMS_RELEASES` at a task-owned directory
containing links to the selected canonical datasets, with every configured
engine dataset directly beneath it. This keeps cleanup away from the shared
release cache. Preserve that directory while the deployment needs it.
Record dataset versions and any local departures from production, such as
`SKIP_SIMPLE_MLOCK=1`.

## Build, activate, and inspect

From the clean service checkout:

```sh
srvmock build
srvmock versions
srvmock activate EXACT_VERSION_LABEL
srvmock sc status
srvmock ps
```

`srvmock deploy` builds and activates HEAD and accepts no ref argument.
Use an exact version label when other builds could make `latest` ambiguous.
Check both HTTP startup and native-engine health: a readiness marker alone
does not prove postal datasets or workers are healthy.

Versions live under `/srv/_versions/NAME`, the active service at `/srv/NAME`,
and mock state/logs/home under `/srv/var/NAME/mockdeploy`.
`srvmock srvinit stop` runs the stop flow. Inspect the requested scope before
using `srvmock clean`; it can remove versions, configuration state, and logs.

## Acceptance and pressure

Use service-owned checks before benchmarking. Record source and dataset
versions, workload, worker count, warm-up, concurrency, latency percentiles,
HTTP errors, and application outcomes.

Serial-versus-concurrent equality establishes repeatability within one build;
it does not establish equivalence to an old build or correctness against
historical fixtures. Exact canaries can differ because of contract changes,
datasets, or regressions. Retain expected/actual differences and diagnose them;
update expectations only after reviewing the change against its data and contract.
Prefer generated postal fixtures with declared expected results for stable
acceptance. AVCass's `make test-acceptance` exercises generated DVDComm ranges
through native workers and both HTTP APIs, using a compatible pinned seed and
controlled RDI files. Ancillary postal and DPV records still depend on the seed;
record it and use separate fixed geometry fixtures for location assertions.
Keep HTTP readiness independent of exact response expectations so healthy
services report correctness differences instead of startup timeouts.

For bounded-concurrency load, separate successful throughput and latency from
overload rejections. AVCass's Connect endpoint can return HTTP 429 with
`resource_exhausted` when its native queue is full. A deliberate saturation test
should confirm accepted responses, expected rejection bodies, and recovery,
rather than counting fast rejections as verification throughput.

Only signal PIDs verified to belong to this deployment. After worker/controller
termination or deadline pressure, confirm replacement, health, and successful
verification. Retain useful evidence and named commits, remove task-owned
temporary worktrees and disposable builds, and leave any requested running
deployment's artifacts and required data aliases available.
