---
name: go
description: Go development conventions including gotestsum for testing, standard tooling (gofmt, go vet, -race flag), and best practices for the Go environment. Use when developing, testing, or debugging Go code. Don't use for deployment, containerization, or Rust/Python projects.
---

# Go

Standard `go` tooling works as documented. This file covers the test-runner preference and the
flags that matter in this workspace.

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

## Pre-commit sequence

```bash
gofmt -l .          # non-empty output = unformatted files
go vet ./...
gotestsum -- -race ./...
```

`-race` matters: Go's data races are silent until they aren't, and CI rarely reproduces them.

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

**Fix:** Never trust the diagnostic at face value. A plain `go test ./...` reporting `(cached)` PASS
is not sufficient evidence either — it proves the code passed at some earlier point, not that it
reflects the current tree. Force a non-cached run before treating the diagnostic as real:
```bash
go build -a ./...          # -a forces rebuild of all packages, bypasses build cache
go test ./... -count=1     # -count=1 disables test result caching
```
Clean run = diagnostic was stale, proceed. Reproduced failure = real, fix it. (detail: memory
"feedback_go_stale_lsp_diagnostics")

## Environment

```bash
CGO_ENABLED=0                          # static binaries; required for scratch/distroless images
GOOS=linux GOARCH=amd64                # cross-compile
GOPRIVATE=github.com/myorg/*           # skip the proxy and checksum DB for private modules
```

`GOPRIVATE` is the usual fix when `go mod download` 404s or fails checksum verification on an
internal repository.
