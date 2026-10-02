# Bedrock router for Codex and ChatGPT SSH hosts

New sessions use Mantle in `us-west-2`, except `openai.gpt-6.1-sol`, which requires
`us-east-1`. A session stays in its initial region across model changes, and new
guardian agents and forks inherit their parent's region. Choosing GPT-6.1 Sol
in a West session returns an explicit conflict: start a new session to use it.

The Go service listens only on `127.0.0.1:18081`, forwards streaming responses, and uses the
bearer token supplied by Codex. Logs contain routing metadata, never tokens or
prompt bodies. Region pins survive restarts in `~/.codex/bedrock-router/sessions.sqlite3`,
which stores only hashed thread IDs and regions. `--state-file` overrides its path.

[`API-CONTRACT.md`](API-CONTRACT.md) defines the proxy and routing contract and
links the pinned upstream OpenAPI reference. Stored response operations use the
originating session's pin without requiring a body `model`; supply that session's
header when retrieving, canceling, deleting, or listing a response's input items.
An unknown session region returns `409 region_unknown`.

## Install or update

Use Go 1.26 or newer to build from source on macOS or Linux:

```sh
cd codex/bedrock-router
go run . install --config ./config.json
```

An already-built binary installs itself without a compiler:

```sh
./bedrock-router install --config ./config.json
```

The `install` subcommand copies the running binary into `~/.codex/bedrock-router`,
backs up and updates `config.toml`, links `.env` to your existing private
`~/.config/bedrock/env`, and installs a launchd or systemd user service.
Run it again after updating this checkout. Existing model, reasoning effort,
project settings, and MCP definitions are preserved. Configuration using extra
Bedrock provider settings or a different `.env` source requires a manual merge.
`--no-start` writes files without starting the service.

On Linux, allow the service to survive logout and start at boot:

```sh
loginctl enable-linger "$USER"
```

If your host requires administrator permission, run that command with `sudo`.
The service uses the system CA bundle. Existing Python-router session pins are
read directly from the same SQLite database.

## Configuration

[`config.json`](config.json) is the checked-in source for the loopback port,
default region, model-to-region mappings, regional discovery fallbacks, and
timeouts. It contains operational settings. Credentials stay in the private
environment file, and session pins stay in the runtime SQLite database.

The installer validates and copies this file beside the binary on every update,
and uses its port when updating the Codex provider URL. Edit the repository copy
and rerun the installer to apply a change. Standalone binaries use `config.json`
beside the executable when present, otherwise the same defaults embedded at build
time. Use `--config` to select another file:

```sh
bedrock-router --config ./config.json --check-config
bedrock-router --config ./config.json
```

Configuration files specify all fields; unknown fields, invalid regions, and
nonpositive timeouts are rejected. Command-line port and timeout flags override
the file. Regional discovery makes at most one attempt using `region_fallbacks`;
omitting a region's fallback disables discovery from that region.

## Streaming, concurrency, and timeouts

Independent sessions and established sessions stream concurrently. Only initial
region discovery is serialized for a session and its parent; waiting requests
can be canceled. Locks are removed when unused. Upstream HTTP/1.1 connections
are pooled, with no cap on active connections. HTTP/2 is disabled so a silent
stream's socket deadline cannot terminate other sessions.

The default upstream header timeout and stream silence timeout are **15 minutes**,
up from 5 minutes. The silence deadline resets on every upstream read; there is
no total response duration limit. Client writes also have a 15-minute deadline.
Change these in `config.json`, or override them on the command line:

```sh
bedrock-router --header-timeout 20m --stream-idle-timeout 20m --client-write-timeout 20m
```

Requests canceled by the client cancel their upstream request. Failures before
headers return a JSON error: `502` for connection failures and `504` for timeouts.
Failures after headers abort the HTTP stream. An SSE response ending without a
completion event is counted and logged as incomplete. Generations, HTTP 500s,
and partially delivered responses are never replayed.

## Monitoring

`/healthz` returns active requests and streams, completed requests, response bytes,
failures, incomplete streams, cancellations, region counts, and pinned sessions.
`/metrics` exposes Prometheus counters and gauges. Scrape it locally to measure
throughput with `rate(bedrock_router_response_bytes_total[5m])` and request rate
with `rate(bedrock_router_requests_total[5m])`.

JSON logs record request start, session-lock wait, upstream headers, first-byte
latency, failures, and completion with status, duration, bytes, and outcome.
Request IDs correlate the events and are returned as `X-Router-Request-Id`.
Session references are shortened hashes. Logs never include authorization,
request bodies, output bodies, raw thread IDs, or raw transport error strings.
On macOS, logs are `~/.codex/bedrock-router/router.log` and `router.err.log`;
on Linux, use `journalctl --user -u codex-bedrock-router -f`. From any shell,
`bedrock-router logs` (installed onto PATH at `~/.local/bin/bedrock-router`)
tails the same logs on either platform; see "Checks and service management"
below.

## Private credentials

Create `~/.config/bedrock/env` privately on each host with these assignments:

```sh
export AWS_REGION=us-west-2
export AWS_BEARER_TOKEN_BEDROCK=<your-long-lived-bedrock-token>
```

Set its permissions to `600`. Never put the real token in this repository.
An SSH host uses its own token file. Codex must be available on the host's login
shell `PATH`; the ChatGPT app can then connect through its SSH host settings.
Restart the app or start a new remote session after installation.

`make codex` in the parent repository also manages `.codex/.env`; if it replaces
the credential link, rerun this installer after restoring the credential source.

## Checks and service management

Use standard `gofmt` for Go source. It has no style configuration; `.editorconfig`
sets editor indentation and line endings. `.golangci.yml` configures `wsl_v5`
to separate `if` blocks and add space after blocks, while allowing one related
statement next to its check. Error checks stay with their assignments; `else`
branches stay attached. Install `golangci-lint` 2.13.2 or newer for the commands
below. CI currently checks `gofmt` output; `make check-fmt` also checks spacing.

```sh
cd codex/bedrock-router
make fmt           # format Go source
make check-fmt     # check formatting without editing
go vet ./...
gotestsum -- -race ./...
```

Check health and service state from any shell (after `install`, `bedrock-router`
is symlinked onto PATH at `~/.local/bin/bedrock-router`):

```sh
bedrock-router status            # human-readable summary; exit 1 if unhealthy
bedrock-router status --quiet    # scripting: no output, exit 0/1
```

Tail logs:

```sh
bedrock-router logs               # last 50 lines
bedrock-router logs -f            # follow
bedrock-router logs -n 200
bedrock-router logs --stderr      # macOS only: router.err.log instead of router.log
```

For deeper diagnostics, the raw commands remain available: `curl --fail
http://127.0.0.1:18081/healthz`, `curl --fail http://127.0.0.1:18081/metrics`,
`launchctl print "gui/$(id -u)/com.joshlane.codex.bedrock-router"` (macOS),
`systemctl --user status codex-bedrock-router.service` (Linux).

On macOS, restart with:

```sh
launchctl kickstart -k "gui/$(id -u)/com.joshlane.codex.bedrock-router"
```

On Linux:

```sh
systemctl --user restart codex-bedrock-router.service
systemctl --user status codex-bedrock-router.service
```

For an older session whose region is not yet recorded, an encrypted-context
validation failure triggers one attempt in the other region with the entire
request unchanged. A successful attempt records that region for future turns.
This also lets an older guardian retain its own history's region when its parent
has a different pin.
An established pin never moves, and encrypted reasoning and compaction are never
removed. A model unavailable in a session's region requires a new session.

If a legacy history contains encrypted items created in both regions, neither
region can accept the complete history. Preserve the original session and start
a new session with a plain-text handoff of the task and current workspace state.
The router does not discard or rewrite encrypted items to bypass this error.
Upstream HTTP 400 responses count as failures; rejection logs identify encrypted
region mismatches for the original route and discovery attempt without logging
the error body.
