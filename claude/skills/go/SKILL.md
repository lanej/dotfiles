---
name: go
description: Go development with gotestsum for testing, standard tooling, and best practices
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

## Environment

```bash
CGO_ENABLED=0                          # static binaries; required for scratch/distroless images
GOOS=linux GOARCH=amd64                # cross-compile
GOPRIVATE=github.com/myorg/*           # skip the proxy and checksum DB for private modules
```

`GOPRIVATE` is the usual fix when `go mod download` 404s or fails checksum verification on an
internal repository.
