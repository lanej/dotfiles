# Go troubleshooting

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
