# TypeScript style guide

Project lifecycle stages select engineering effort and the generated CI gate. Use `python3 scripts/check-source-code.py typescript` for the selected stage; beta and production run the full profile described below. Research and alpha defer some added checks while retaining inherited repository gates. See [source-code setup](repository-bootstrap.md#lifecycle-stages).

Prefer explicit state, visible failures, and validated boundaries over a long list of stylistic preferences. The profile combines the TypeScript compiler, typed ESLint, separate formatting, and a shrinking diagnostic budget for existing code. Passing these checks does not establish business correctness.

## Adopt the profile

Start with a Git repository containing a `package.json`, a `tsconfig.json`, and the dependencies needed to compile its source. Select a different config with `--typescript-project path/to/tsconfig.json`; repeat the option for independent leaf projects.

```sh
source-code setup --repo ~/src/service --typescript --pr-template none
cd ~/src/service
node scripts/check-typescript.mjs tools
node scripts/check-typescript.mjs
```

TypeScript adoption is opt-in. Tracked TypeScript source selects `ratchet` by default; a new project without tracked source selects `strict`. Choose `--typescript-rollout strict` explicitly when an existing repository is ready. `--typescript-retrofit` explicitly selects the legacy adoption path. Both modes also install the shared comment policy and the library caller guidance; apply the library perspective to public library APIs. These guidance files follow the selected tracked or Git-excluded local installation mode.

Bootstrap copies configuration, a runner, CI, and a portable skill. It does not install packages, rewrite application files, replace executable ESLint configuration, or change application dependencies. The explicit `tools` command installs exact tool versions in `.typescript-quality`, separate from the application's dependencies, using npm with lifecycle scripts disabled. Review and commit its generated `package-lock.json`. Subsequent installations use `npm ci`; normal checks never install tools. This pins transitive dependencies in each adopted project rather than claiming that exact direct versions alone pin the entire dependency graph.

The supplied CI workflow assumes npm for application installation. For pnpm or modern Yarn, adapt that installation step to the project's pinned package manager and frozen lockfile. Existing npm/pnpm/Yarn `lint`, `typecheck`, and `check-types` scripts become separate, blocking gates. Existing ESLint configuration without a `lint` script is rejected instead of silently abandoning it. Original scripts must be check-only, including lifecycle hooks. Review generated command arrays before executing them; the profile is not a sandbox for repository commands.

## What is enforced

| Concern | Enforcement |
| --- | --- |
| Nulls and indexed access | Strict checking, explicit strict subflags, `noUncheckedIndexedAccess`, exact optional properties. |
| State handling | Exhaustive union switches; default does not cover a missing variant. Use compiler-checked `satisfies Record<Union, Value>` for total maps. |
| Unsafe boundaries | Explicit `any`, unsafe use of `any`, non-null assertions, and narrowing type assertions fail. Validate `unknown` at the boundary. |
| Async failures | Floating promises fail, including `void promise`; promise callbacks and error-sensitive `return await` are checked. |
| Error values | Throw Error objects, narrow catch values, and handle rejection deliberately. |
| Control flow | Strict Boolean expressions, missing returns, switch fallthrough, unreachable code, unused locals and parameters. |
| Suppressions | Named ESLint rules and explanations; unused suppressions fail. `@ts-ignore` and `@ts-nocheck` fail; `@ts-expect-error` needs a description. Suppression-policy findings cannot be baselined. |
| Formatting | Prettier checks separately, respecting project configuration. Only explicit `fmt FILE...` rewrites source. |
| Existing protections | Original lint/typecheck scripts, the original compiler configuration, tests, and dependency audit remain blocking. |

The runner reads each project's existing tsconfig, preserving module resolution, JSX, path aliases, and library choices. It applies the options from the [strict compiler profile](../ai/skills/typescript/assets/tsconfig.strict.json) in memory. Every strict subflag is explicit, so an inherited `strictNullChecks: false` cannot defeat `strict: true`. The same strict TypeScript Programs are passed to [typed ESLint](../ai/skills/typescript/assets/eslint.config.mjs); lint does not silently use the weaker original config during adoption.

The reference compiler is TypeScript 5.9.3, with ESLint 9.39.1, typescript-eslint 8.48.0, and Prettier 3.6.2. These are deliberate exact pins, not claims about the latest versions. Project configs requiring a different compiler must review and update the isolated toolchain before adoption. Keep original compiler/build commands as independent gates. Review strict preset changes when upgrading; `strictTypeChecked` is not a permanently frozen rule list.

## Exhaustiveness is not input validation

```typescript
type Result =
  | { kind: "accepted"; id: string }
  | { kind: "rejected"; reason: string };

function unreachable(value: never): never {
  throw new Error(`Unhandled result: ${String(value)}`);
}

function describe(result: Result): string {
  switch (result.kind) {
    case "accepted":
      return result.id;
    case "rejected":
      return result.reason;
    default:
      return unreachable(result);
  }
}

const terminal = {
  accepted: true,
  rejected: true,
} satisfies Record<Result["kind"], boolean>;
```

Adding a variant breaks the switch and the total mapping. The runtime guard throws instead of returning the unexpected object under an asserted return type. External JSON still needs real validation before becoming a `Result`; TypeScript types disappear at runtime. Retain the project's existing validator rather than introducing a second schema system automatically.

## Retrofit without a cleanup campaign

```sh
source-code setup --repo ~/src/service --typescript-retrofit --pr-template none
cd ~/src/service
node scripts/check-typescript.mjs tools
node scripts/check-typescript.mjs baseline
node scripts/check-typescript.mjs
```

Commit source before creating the one-time baseline. Baseline creation refuses dirty or untracked analyzed source, an existing baseline, broken original compilation, missing modules, malformed configuration, parser failures, and suppression-policy violations. It records only additional strict compiler, lint, and formatting findings. It does not run source fixes.

Analyze the full configured project, not changed lines. Newly added files have no allowances. A new union variant must fail an untouched consumer if that consumer is now non-exhaustive. Git-visible TypeScript outside the selected configs fails coverage instead of being silently skipped. Tests need to be included in one of those configs. Declaration files are compiler-checked and formatted but not linted as executable TypeScript.

The baseline counts signatures consisting of path, checker, diagnostic, message, and source excerpt. Line movement alone does not consume an allowance. Indistinguishable replacements can share a count; formatting has one finding per file. This is a debt budget, not a defect-identity ledger or proof of compliance. Review baseline edits like policy changes.

After repairing old findings:

```sh
node scripts/check-typescript.mjs ratchet
git diff -- .typescript-quality-baseline.json
```

`ratchet` refuses growth. Normal checks reject stale allowances until the reduction is committed. Partial `lint` and `typecheck` checks only evaluate their own portions of the budget; only a full ratchet rewrites it. Original project checks, test failures, and audit failures are never grandfathered.

## Commands and scope

Use `lint` while implementing, `typecheck` for compiler feedback, and the full command before handoff. `test` and `audit` run the policy's explicit argv arrays. Missing commands and failed tools fail closed. `fmt` always requires file paths, including in strict projects, so formatting cannot turn a feature into a repository-wide rewrite.

The first version targets ordinary TypeScript/TSX projects on Node 22+ and Git. It accepts multiple independent leaf configs but rejects project-reference builds; retain the real reference-build command and adapt coverage deliberately rather than claiming a partial check is complete. Framework-embedded TypeScript, JavaScript, workspace orchestration, platform-specific builds, services, and native dependencies need project-specific integration.

Generated paths can be excluded explicitly in `.typescript-quality.json` with a concrete reason. Exclusions narrow lint, formatting, and source inventory; they do not suppress compiler errors in files the program imports. Review these exclusions. No global test-file exemption is supplied.

Import restrictions, cycle checks, resource ownership, runtime schema validation, and security analysis depend on the application. Retain existing gates and add concrete project constraints; this profile does not claim to infer dependency direction, prove cleanup, or provide a TypeScript equivalent of Go's reachable-call vulnerability analysis. The default audit is the package manager's dependency advisory check.

Commit the installed profile, policy, tool lockfile, and any baseline. Make the `TypeScript quality` job required in branch rules; creating a workflow alone cannot prevent a merge. No Git hooks or GitHub administration settings are changed by bootstrap.

## References

- [TypeScript compiler options](https://www.typescriptlang.org/tsconfig/)
- [Typed linting](https://typescript-eslint.io/getting-started/typed-linting/)
- [typescript-eslint shared configs and stability](https://typescript-eslint.io/users/configs/)
- [Floating promise handling](https://typescript-eslint.io/rules/no-floating-promises/)
- [Unsafe type assertions](https://typescript-eslint.io/rules/no-unsafe-type-assertion/)
