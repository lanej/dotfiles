# Josh Lane’s Go style guide

I want Go code that makes decisions explicit, preserves failure information, and catches routine mistakes before review. Small, understandable changes matter more than satisfying a large collection of stylistic preferences. Use strict defaults for new projects and introduce them into existing projects without bundling a repository-wide cleanup into a feature PR.

The [lint profile](../ai/skills/go/assets/golangci.yml) is the executable policy; the [check runner](../ai/skills/go/assets/check-go.sh) pins its tools. This guide explains the choices and their consequences. Repository-specific requirements can strengthen these defaults. Passing the checks does not establish that a business decision is correct.

## Defaults at a glance

| Concern | Default | Consequence |
| --- | --- | --- |
| Enum values | Named type, typed constants, intentional zero value | Unknown input remains visible; integer and string conversions still need validation. |
| Enum handling | Exhaustive switches and enum-keyed maps; explicit runtime fallback | Adding a constant identifies consumers that need a decision, including unchanged files. |
| Variants with different data | Declared sum-type interface and exhaustive type switch | Each variant carries its own data; this approximates a closed union rather than adding a native Go language guarantee. |
| Errors | Check returned errors, blank assignments, and type assertions | Ignoring a failure requires a local, named, explained exception. |
| Resource lifetime | Close bodies, rows, statements, and spans; propagate cancellation | Acquiring a resource creates an explicit cleanup obligation. |
| Concurrency | Vet plus uncached race tests | Lock-copying and common mistakes are checked statically; the race detector covers executed paths. |
| Security | Security lint plus reachable-vulnerability analysis | Known dangerous patterns and reachable vulnerable calls fail; dependency updates remain deliberate. |
| Formatting | `gofumpt` and `goimports` | One formatting policy, applied explicitly rather than rewriting source during checks. |
| Readability | `wsl_v5` with bounded cuddling | Related setup can stay together; unrelated operations and long exits get visual separation. |
| Feedback | Tests included; finding and duplicate caps disabled | Agents receive the full diagnostic set in one iteration. |
| Exceptions | Specific linter and a concrete explanation; unused suppressions fail | Exceptions remain local and reviewable. |

The profile deliberately names its checks. It does not enable every available linter: mandatory comments, arbitrary line-length limits, or filling every field of a third-party struct do not reliably improve a decision or its implementation.

## Cuddling and whitespace

“Cuddling” means placing statements next to one another without a blank line. Keep a value and its immediate use together when that relationship makes the code easier to read. Separate unrelated preparation and visually distinguish the exit from a longer block.

| Setting | Default | Meaning |
| --- | --- | --- |
| `cuddle-max-statements` | `1` | At most one related statement may immediately precede a block, `go`, `defer`, or send. |
| `allow-first-in-block` | `true` | A value may stay beside a block when its first statement uses that value. |
| `allow-whole-block` | `false` | A use buried later in a block does not justify cuddling. |
| `branch-max-lines` | `2` | Longer blocks separate their final return or branch with a blank line; short guard clauses stay compact. |
| `case-max-lines` | `0` | Do not require a trailing blank line after every switch case. |

Before, two setup statements run into a control-flow decision, and the final return runs into the preceding block:

```go
payload := encode(job)
attempt := previousAttempt + 1
if err := send(payload, attempt); err != nil {
	return err
}
return nil
```

After, the immediate setup stays with its use, and the longer block has a clear exit:

```go
payload := encode(job)

attempt := previousAttempt + 1
if err := send(payload, attempt); err != nil {
	return err
}

return nil
```

Use `bash scripts/check-go.sh fmt path/to/file.go` for formatting. Use `bash scripts/check-go.sh fix ./internal/package` for available cuddling fixes in a chosen package, then inspect the diff and rerun lint. Fixes can change other files in that package. A retrofit requires explicit file paths for formatting so a convenience command does not become an accidental whole-project cleanup.

## Make state changes explicit

Use typed constants for simple states. Reserve zero for an intentional state or treat it as invalid. For wire and stored values, use explicit strings or fixed numeric assignments; reordering an `iota` block must not change persisted meaning.

```go
type State string

const (
	Pending   State = "pending"
	Succeeded State = "succeeded"
	Failed    State = "failed"
)

func Terminal(state State) (bool, error) {
	switch state {
	case Pending:
		return false, nil
	case Succeeded, Failed:
		return true, nil
	default:
		return false, fmt.Errorf("invalid state %q", state)
	}
}
```

Adding `Cancelled` must make every relevant consumer choose how to handle it. A `default` branch handles invalid values; it does not stand in for omitted declared cases. Enum-keyed maps follow the same rule. Intentional partial maps need a narrow exception explaining why absence is meaningful.

When variants carry different data, use an interface marked `//sumtype:decl`, an unexported marker method, and concrete variant types. Handle each variant and any permitted nil value explicitly. Interfaces can still contain nil and be embedded elsewhere, so this remains a tooling convention rather than a sealed Go type.

## Preserve errors and isolate decisions

Return errors to the layer that can make a meaningful decision. Wrap when adding context, preserve error identity, and use `errors.Is` or `errors.As` when inspecting it. Avoid collapsing “not found,” “rejected,” and “outcome unknown” into one successful empty result.

Keep domain decisions exercisable with explicit inputs. Put I/O, clocks, retries, and resource management at the boundary where practical. Introduce an interface when it isolates a meaningful dependency or demonstrates a real substitution need. A small function does not need an interface hierarchy.

Comment on rationale, constraints, and consequences. Ordinary Go documentation comments remain appropriate. Explain a deliberate exception near the relevant code:

```go
//nolint:errcheck // A bytes.Buffer write cannot fail.
buffer.WriteString(value)
```

Do not turn off a check globally because one call needs an exception. Do not add a suppression just to make an agent’s current change pass.

## Adopt without a cleanup campaign

New repositories use whole-project strict checks. Existing repositories default to a ratchet when bootstrap finds an existing config or tracked Go source. The initial adoption changes tooling and records current lint debt; it does not rewrite Go files.

Start with committed Go source, including any source needed to analyze the project. YAML and JSON golangci-lint v2 configurations can be merged; migrate v1 first. TOML configurations require explicit conversion. Config merging needs PyYAML; the installer can use the workstation’s `uv` to cache a pinned parser when it is absent.

```sh
repo-bootstrap --repo ~/src/service --go-retrofit --pr-template none
cd ~/src/service
bash scripts/check-go.sh baseline
bash scripts/check-go.sh
```

The original config, comments, and existing check remain intact. A separate `.golangci.strict.json` combines the project’s build context, extra linters, and custom settings with this profile. The added profile owns the settings and defaults for its checks, so inherited opt-in or ignore settings cannot disable them. Custom settings for additional project checks are retained; full-tree reporting and the added profile’s exclusions apply to that layer. The original check still runs under the original settings. Existing exclusions therefore remain effective in the original gate without exempting new test files from the added defaults. If the original config changes, bootstrap must regenerate the merged layer before checks pass.

The baseline stores counts by file, linter, message, and reported source excerpt, independently of line numbers. Moving an unchanged finding does not force unrelated cleanup. A new file has no allowance. A new diagnostic in an existing file also fails, including an old enum switch made incomplete by a constant added elsewhere. Compilation errors are never baselined.

This is a budget of reported findings, not proof of individual defect identity. An indistinguishable finding can occupy the same budget, and formatters may report only one finding for a whole file. A partially cleaned file can therefore need additional work before its formatting allowance disappears. Do not describe a ratcheted repository as entirely compliant.

After fixing existing findings, reduce the allowance explicitly:

```sh
bash scripts/check-go.sh ratchet
git diff -- .go-quality-baseline.json
```

Commit that reduction with the fix. Normal lint fails while resolved allowances remain, and `ratchet` refuses to add findings. Baseline creation refuses an existing baseline and dirty, untracked, or ignored Go source. Review baseline edits like policy changes; manually enlarging it would weaken the protection. Race tests, module tidiness, the original lint gate, and vulnerability checks remain full checks and are not grandfathered.

Use `--go-rollout strict` when the repository is ready for full enforcement. The [repository bootstrap guide](repository-bootstrap.md) describes local versus tracked installation. Commit the checks and require the `Go quality` job in branch rules when adopting it as a merge gate; a workflow file alone cannot prevent an administrative merge.

## Check the real build surfaces

Run `bash scripts/check-go.sh lint` while implementing and the full command before handoff. The default runner covers one root module on macOS or Linux. Local checks use the active compatible Go toolchain; `go.mod` supplies minimum and toolchain requirements rather than an exact local pin. CI selects its toolchain from `go.mod` with setup-go. It disables inherited workspaces for parity with a fresh checkout. Add the actual module, build-tag, platform, service, and native-dependency configurations the project relies on.

Go and Python 3.9+ are required for the portable runner. Race tests need cgo and a C compiler. The runner caches golangci-lint 2.13.2 and govulncheck v1.9.0 outside the project, verifies the linter release checksum, and keeps tool dependencies out of the application module. Initial tool setup and vulnerability analysis need network access. Failures to run a check are failures to resolve or report, never silent success.

The race detector only sees executed paths. Vulnerability analysis only sees known issues in the analyzed configuration. Tests still need independent expected behavior; repeating the implementation in a test does not establish that its decision is right.
