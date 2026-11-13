# TypeScript correctness defaults

Use the [compiler options](../assets/tsconfig.strict.json), [typed lint profile](../assets/eslint.config.mjs), and [runner](../assets/check-typescript.mjs) as one policy. Install with `repo-bootstrap --typescript` or `--typescript-retrofit`; a separate `tools` invocation installs pinned dependencies without changing the application's package manifest. Review and commit the generated quality-tool lockfile.

Use discriminated unions, explicit state transitions, and compiler-checked total maps. Validate `unknown` at I/O boundaries. A cast is not a validator; `void promise` is not a rejection handler. Throw a runtime error in an unreachable-case helper rather than returning a value whose static type is `never`.

The runner preserves original project configuration and commands, applies additional strict compiler options in memory, and passes those same Programs to ESLint. Never filter to changed lines. Include tests and every Git-visible TypeScript file in the selected project configs; uncovered files fail. The initial implementation accepts independent leaf projects, not project-reference build graphs or framework-embedded source.

New projects use strict enforcement. Retrofits require committed source and a one-time baseline. Original compilation, parser/configuration failures, missing modules, suppression-policy violations, original project checks, tests, and audits cannot be baselined. New diagnostics fail even in unchanged consumers. After fixing old findings, run `node scripts/check-typescript.mjs ratchet`; it can only shrink the budget. A signature budget can reuse indistinguishable findings and formatting is file-granular, so do not claim individual defect identity or full legacy compliance.

Use `lint` during implementation and the full command before handoff. `typecheck`, `test`, and `audit` isolate checks; `fmt` requires explicit file paths. Preserve stronger application-specific architecture, import, lifecycle, build, and security checks. Inspect policy commands and adapt the npm-oriented CI installation step for other package managers. These checks do not infer business rules or validate runtime data.

Read the [published TypeScript guide](https://lanej.github.io/dotfiles/reference/typescript-style/) for examples, deployment constraints, and adoption tradeoffs. The source guide is `docs/typescript-style.md` in lanej/dotfiles.

Biome 2.6.7 is a required, pinned correctness gate in `lint` and full validation, including CI. Its findings cannot enter the retrofit baseline. The focused rules catch debugger statements, duplicate cases, class members and object keys, sparse arrays, unreachable code and unsafe finally blocks. Typed ESLint and Prettier remain responsible for the existing broader analysis and formatting contracts.
