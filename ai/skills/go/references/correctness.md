# Go correctness defaults

Use the shipped profile and `scripts/check-go.sh` as the starting point for Go modules. Keep the copied files in the repository, review upgrades, and run the same full command locally and in CI. Existing project policy remains authoritative; reconcile stronger checks rather than replacing them.

## Protections

| Area | Enforcement |
| --- | --- |
| Enums | `exhaustive` checks switches and enum-keyed map literals. A `default` does not cover omitted constants; enum switches also require a runtime fallback. |
| Sum types | `gochecksumtype` checks type switches over interfaces marked `//sumtype:decl`. A `default` does not cover omitted variants. |
| Errors | Strict `errcheck` checks discarded errors, blank assignments, and unchecked assertions. `errorlint`, `nilerr`, and `nilnesserr` check common error-handling mistakes. |
| Lifetimes and cancellation | HTTP body, SQL row/statement, tracing span, context propagation, and cancellation analyzers. |
| Security | `gosec`, Unicode identifier checks, and call-graph-based `govulncheck`. |
| Concurrency | Vet's copy-lock, atomic, and cancellation checks; context checks; uncached `-race` tests on executed paths. |
| Readability | `wsl_v5` permits one adjacent setup statement, compact exits for blocks up to two lines, and no mandatory trailing blank line for every switch case. |
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

Prefer `repo-bootstrap --go` for a new module or `repo-bootstrap --go-retrofit --pr-template none` for an existing repository. Bootstrap detects root modules, preserves existing config bytes and comments, merges YAML/JSON v2 policy into a separate strict layer, and retains the original lint gate. Existing configs or tracked Go source default to a ratchet; new projects default to strict. V1 configurations must be migrated first; TOML needs conversion.

Without dotfiles, copy the following files from this package's assets into a new project. Do not overwrite existing policy; use the installer when retrofitting.

| Asset | Project path |
| --- | --- |
| `golangci.yml` | `.golangci.yml` |
| `go-quality.json` | `.go-quality.json` |
| `check-go.sh` | `scripts/check-go.sh` |
| `go-quality.py` | `scripts/go-quality.py` |
| `go-quality.yml` | `.github/workflows/go-quality.yml` |

Run `bash scripts/check-go.sh lint` while editing. Use `fmt path/to/file.go` to format selected files and `fix ./path/to/package` for available cuddling fixes; inspect the diff. Ratchets reject an unscoped `fmt` to avoid whole-project cleanup. The full command runs lint first for early feedback, then race tests and vulnerability analysis. `test`, `vuln`, and `tools` isolate work.

For a retrofit, run `bash scripts/check-go.sh baseline` once, against committed existing Go source. This records existing strict lint/style findings without changing Go files. It rejects dirty, untracked, and ignored Go source, an existing baseline, or compilation errors. New files have no allowance; new diagnostics in old files also fail, including untouched consumers invalidated by new enum values. Do not apply changed-line filtering.

The baseline counts file/linter/message/source-excerpt signatures rather than line numbers. Moving an unchanged finding remains allowed; indistinguishable replacements can share its budget, and formatter findings may represent a whole file. Treat this as gradual adoption, not proof that all legacy code meets the guide. After fixes, `bash scripts/check-go.sh ratchet` removes resolved allowances; it cannot add new ones. Normal lint requires resolved allowances to be removed; commit that reduction with the fix. Manually enlarging a baseline is a policy weakening, not a way to fix a failed check.

Existing custom rules and build context are merged with the added defaults. The added layer owns its checker settings and defaults, strict reporting, and exclusions; the original gate remains unchanged and runs with fixing disabled. If its config changes, rerun bootstrap to refresh the merged copy. Local mode hides copied files and the baseline; shared CI requires tracked files. Existing workflows remain subject to normal conflict protection.

The runner pins golangci-lint 2.13.2 and govulncheck v1.9.0, verifies the official linter release SHA-256, and builds govulncheck separately from application dependencies. Tools are cached under `${XDG_CACHE_HOME:-$HOME/.cache}/go-quality`. Review upgrades rather than switching to `latest`; the vulnerability database remains live. Initial setup and scans need network access.

Go and Python 3.9+ are required by the portable runner. Config merging uses PyYAML; bootstrap can use the workstation's uv to cache PyYAML 6.0.3 when absent. The default runner covers one root module on macOS or Linux, amd64 or arm64. It sets `GOWORK=off` to avoid hidden parent-workspace replacements. Add explicit module/workspace, build-tag, platform, and integration coverage as required. Race tests need cgo and a C compiler even when production binaries are static.

Make the `Go quality` job required in branch rules to enforce a merge gate. Bootstrap does not change GitHub settings, migrate every existing repository, or install Git hooks. The human-readable [Go style guide](https://lanej.github.io/dotfiles/reference/go-style/) publishes the rationale, defaults, examples, and rollout tradeoffs alongside the dotfiles documentation.

Suppress only a particular finding with a concrete explanation. Keep `nolintlint` active for unspecified, unexplained, or ineffective suppressions. Native directives such as `//exhaustive:ignore` also need a local explanation and must not hide newly added enum values.

## Limits and sources

Lint catches known code patterns. Tests need independent expected behavior. The race detector covers paths actually run, and `govulncheck` detects known vulnerabilities reachable in the analyzed configuration. None proves domain correctness or rules out all concurrency or security defects.

- [Golangci-lint configuration](https://golangci-lint.run/docs/configuration/file/) and [linter settings](https://golangci-lint.run/docs/linters/configuration/).
- [Go race detector](https://go.dev/doc/articles/race_detector).
- [Go vulnerability management](https://go.dev/doc/security/vuln/).
