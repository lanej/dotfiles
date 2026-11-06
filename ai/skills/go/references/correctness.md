# Go correctness defaults

Use the shipped `.golangci.yml` and `scripts/check-go.sh` as the starting point for new Go modules. Keep the copied files in the repository, review upgrades, and run the same full command locally and in CI. Existing project policy remains authoritative; reconcile stronger checks rather than replacing them.

## Protections

| Area | Enforcement |
| --- | --- |
| Enums | `exhaustive` checks switches and enum-keyed map literals. A `default` does not cover omitted constants; enum switches also require a runtime fallback. |
| Sum types | `gochecksumtype` checks type switches over interfaces marked `//sumtype:decl`. A `default` does not cover omitted variants. |
| Errors | Strict `errcheck` checks discarded errors, blank assignments, and unchecked assertions. `errorlint`, `nilerr`, and `nilnesserr` check common error-handling mistakes. |
| Lifetimes and cancellation | HTTP body, SQL row/statement, tracing span, context propagation, and cancellation analyzers. |
| Security | `gosec`, Unicode identifier checks, and call-graph-based `govulncheck`. |
| Concurrency | Vet's copy-lock, atomic, and cancellation checks; context checks; uncached `-race` tests on executed paths. |
| Tests and diagnostics | Tests are linted; test assertion and parallelism checks are enabled. All findings are reported without per-linter or duplicate caps. |
| Reproducibility | Pinned tools, strict formatting, read-only lint module resolution, and `go mod tidy -diff`. |

The profile explicitly selects correctness checks. It does not enable every linter: line-length rules, mandatory comments, arbitrary complexity thresholds, and full-field initialization of every third-party struct can create churn without proving correctness. Add project-specific constraints where their invariants justify them. One formatter policy avoids conflicting style tools.

## Enums and variants

Use typed constants; keep an intentional zero value. Use stable explicit strings or numeric assignments for persisted and wire values instead of relying on reorderable `iota` positions. Parse and validate untrusted inputs at boundaries: lint checks declared constants, not the entire underlying integer or string domain.

List all declared cases explicitly, including Unknown/Invalid if declared, then return an error or otherwise deliberately handle values outside the set. Intentional subsets need a local exception with a reason; a sparse lookup does not become a total domain function merely because its key type is an enum.

Use the following shape when variants carry different data:

```go
//sumtype:decl
type Result interface {
	isResult()
}

type Accepted struct{ ID string }
type Rejected struct{ Reason string }

func (Accepted) isResult() {}
func (Rejected) isResult() {}
```

Keep concrete variants in the declaring package and handle nil explicitly when allowed by the API. The marker pattern and linter approximate a closed sum type; Go does not provide native sealed types, and interfaces can still carry nil or be embedded elsewhere. Do not claim a compiler-level closed-world guarantee.

## Workflow and adoption

Run `bash scripts/check-go.sh lint` while editing. Apply formatting with `bash scripts/check-go.sh fmt`, then run the full command before handoff. The full run performs lint first for early feedback, then race tests and vulnerability analysis. `tools` preloads both tools when useful. Tools are cached under `${XDG_CACHE_HOME:-$HOME/.cache}/go-quality`, with independent versioned directories; no dotfiles checkout is needed after installation.

The runner pins golangci-lint 2.13.2 and govulncheck v1.9.0. It downloads official golangci-lint release binaries and checks their published SHA-256 before extraction. Govulncheck is built through Go's module tooling at its pinned version, separately from application dependencies. Actions are pinned to commits. Review pins together with the configuration; do not change them to `latest`. The vulnerability database stays live so newly disclosed problems are detected.

The default runner covers a single root module on macOS or Linux, amd64 or arm64. It disables inherited workspaces so parent `go.work` replacements cannot hide dependencies missing in a fresh checkout. Add explicit module/workspace, build-tag, operating-system, and native-service coverage as needed. Race tests require cgo and a C compiler; a static production build's `CGO_ENABLED=0` setting must not disable this check. Keep required integration checks alongside the default runner. CI uses the Go version specified by `go.mod`.

For a new repository before `go.mod` exists, pass `repo-bootstrap --go --init`. Existing root Go modules opt in automatically during bootstrap; `--no-go` installs the requested guidance without modifying checks. Repeated bootstrap runs remember the profile. Local mode excludes the copied files locally; CI enforcement requires committing them in tracked mode. Existing lint files or workflow paths are preserved by the installer's conflict policy, including alternate `.golangci` extensions.

Make the `Go quality` job required in the repository's branch rules when adopting it as a merge gate. A committed workflow runs checks but does not itself prevent an administrator from merging failed checks. Bootstrap does not change GitHub settings, migrate every existing repository, or install Git hooks.

Suppress only a particular finding with a concrete explanation, for example `//nolint:errcheck // A bytes.Buffer write cannot fail.` Keep `nolintlint` active to reject unspecified, unexplained, or ineffective suppressions. Native analyzer directives such as `//exhaustive:ignore` also need a local explanation; never use them to hide newly added enum values.

## Limits and sources

Lint catches known code patterns. Tests need independent expected behavior. The race detector covers paths actually run, and `govulncheck` detects known vulnerabilities reachable in the analyzed configuration. None proves domain correctness or rules out all concurrency or security defects.

- [Golangci-lint configuration](https://golangci-lint.run/docs/configuration/file/) and [linter settings](https://golangci-lint.run/docs/linters/configuration/).
- [Go race detector](https://go.dev/doc/articles/race_detector).
- [Go vulnerability management](https://go.dev/doc/security/vuln/).
