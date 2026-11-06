---
name: go
description: Use when creating, modifying, testing, or reviewing Go code. Apply the portable Go correctness profile with exhaustive enums and sum types, strict error handling, security analysis, race tests, and vulnerability checks; preserve repository-specific policy.
---

# Go

Use the repository's Go checks early and before handoff. Use `repo-bootstrap --go` for new projects or `repo-bootstrap --go-retrofit --pr-template none` for existing repositories. Bootstrap detects root modules, preserves an existing lint config, and defaults existing code to a shrinking lint baseline. Read [the adoption instructions](references/correctness.md) before installing or merging the profile; they also describe copying the portable assets without dotfiles. Commit the checks and policy so other machines and CI use them.

Preserve and extend existing project checks; reconcile an existing configuration instead of replacing or weakening it. For nested modules, workspaces, build tags, platform-specific code, or native dependencies, adapt the checks and CI matrix to the actual build surfaces. The supplied runner covers one root module on its host platform. Run relevant extra configurations explicitly.

## Correctness checks

Run `bash scripts/check-go.sh lint` during implementation, `bash scripts/check-go.sh fmt path/to/file.go` to apply formatting, and `bash scripts/check-go.sh` before delivery. Use `fix ./path/to/package` for available cuddling fixes and review their diff. The same full command runs in CI: formatting, module tidiness, strict lint, uncached race tests, and reachable-vulnerability analysis. `test` and `vuln` modes isolate failures. Read [the correctness guide](references/correctness.md) when adopting, tuning, or explaining the profile.

The runner caches pinned tools outside the project, verifies the linter release checksum, and keeps tool dependencies out of the application's `go.mod`. Initial setup and vulnerability analysis need network access. Missing tools, unavailable dependencies, or failed checks are failures to resolve or report; never silently skip a gate. Preserve all findings for batch repairs. Respect an explicitly adopted ratchet: initialize its baseline only on committed existing Go source before adding new work, and use `ratchet` to remove resolved findings. Never grow a baseline or use changed-line filters, blanket exclusions, or omitted tests to silence new findings. New file paths are strict; analysis still checks unchanged consumers affected by a new enum value.

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

## Existing projects without the profile

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

## Stale gopls/LSP Diagnostics After a Concurrent Write

An editor/LSP diagnostic reporting `undefined: <Symbol>` or a similar compile error right after your
own edit, a dispatched sub-agent's commit, or a peer session's commit just defined that symbol is
frequently a stale gopls index, not a real error — gopls doesn't reliably invalidate its package
index the instant another process writes and commits new Go source. Recurring pattern, confirmed 7+
times in one session (`fraud-detector`, 2026-09-26).

**Fix:** Check with the actual compiler before treating the diagnostic as real. Go's build and test caches are content-addressed; `(cached)` is not itself evidence that a changed source tree was ignored. Use an uncached test run when resolving uncertainty:
```bash
go build ./...
go test ./... -count=1     # -count=1 disables test result caching
```
If both pass, investigate editor state rather than rewriting valid code. If the compiler reproduces the failure, fix it.

## Environment

```bash
CGO_ENABLED=0                          # static binaries; required for scratch/distroless images
GOOS=linux GOARCH=amd64                # cross-compile
GOPRIVATE=github.com/myorg/*           # skip the proxy and checksum DB for private modules
```

`GOPRIVATE` is the usual fix when `go mod download` 404s or fails checksum verification on an
internal repository.
