# Go

Before selecting application tools or an API protocol, read [the installed project policy](../../source-code-lifecycle/SKILL.md). Apply the declared authority and adoption at the configured maturity; preserve external providers’ protocols and established stacks according to that policy.

Follow the verification commands and enforcement in this skill’s installed entrypoint. Preserve existing repository checks.

For comment decisions, read the [shared comment guidance](../../code-comments/SKILL.md). For public library APIs, also read the [library comment guidance](../../library-code-comments/SKILL.md). Bootstrap bundles both with this skill in tracked or local mode; apply the library perspective only to library work and preserve project requirements.

## API client generation

For Go client generation from OpenAPI-described JSON APIs, prefer [Ogen](https://ogen.dev/). Source the authoritative OpenAPI specification, whether encoded as JSON or YAML, and pin the generator version. JSON samples or a standalone JSON Schema do not supply the full HTTP contract; establish the missing operations and protocol semantics before generation. Document a concrete compatibility constraint and a revisit condition when selecting another generator. Preserve established project tools unless a migration is authorized.

## Correctness

Fix findings at their cause. Use only narrowly scoped suppressions with the named linter and a concrete rationale. Static analysis and passing tests do not prove domain correctness or cover unexecuted race paths.

Use a named type and typed constants for simple enums. Give zero an intentional meaning or treat it as invalid. Handle every declared value explicitly in switches and enum-keyed maps; a `default` branch must not substitute for a missing declared case. Handle out-of-set values at runtime too: `State(99)` can still compile. For variants carrying different data, use an interface marked `//sumtype:decl` with an unexported marker method and concrete variants; require exhaustive type switches with `gochecksumtype`.

Fix findings at their cause. Use only narrowly scoped suppressions with the named linter and a concrete rationale, including intentional partial enum maps. Do not blanket-disable rules or loosen checks merely to obtain green output. Static analysis and passing tests cannot prove domain correctness or cover unexecuted race paths; retain independent behavioral expectations and meaningful tests.

## Use `gotestsum`, not bare `go test`

`gotestsum` wraps `go test` with readable, colorized output and failure re-runs. Fall back to
`go test` only if it isn't installed.

```bash
gotestsum ./...
gotestsum --watch ./...                 # TDD loop
gotestsum --format testdox ./...        # BDD-style names; also: dots, pkgname, testname
gotestsum -- -race -tags integration ./...   # flags after -- go to go test
gotestsum --rerun-fails=2 ./...         # isolate flakes
gotestsum --junitfile=junit.xml ./...   # CI
```

`--rerun-fails` is for *diagnosing* a flake, not for making CI green. A test that only passes on
re-run is a bug to fix.

## Existing repository checks

These examples describe available Go tools; use the installed profile selector and repository requirements to choose required commands.

```bash
gofmt -l .          # inspect output; this command alone does not fail on differences
go vet ./...
gotestsum -- -race ./...
```

Treat unformatted output as a failed check. Run the project's existing linter and security checks as well. The fallback above does not provide exhaustive-match enforcement; adopt the profile or reconcile equivalent checks before claiming those protections.

## Coverage

```bash
go test -coverprofile=cover.out ./... && go tool cover -html=cover.out
```

Read [troubleshooting](troubleshooting.md) when investigating stale editor diagnostics or environment settings.
