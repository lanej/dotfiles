# Strict Python profile

Install with `source-code setup --python`, or select `[checks.python] enabled = true` in authored TOML. Detection supplies Python guidance only. The profile is strict from adoption: there is no grandfathered diagnostic baseline. Preserve existing project requirements and configuration.

## Configuration and tools

The installer adds `scripts/check-python.py`, `.python-quality.json`, and a pinned, isolated uv tool project under `.python-quality/`. It leaves root `pyproject.toml`, Ruff/ty settings, dependency metadata, and existing CI unchanged. Generated Python CI runs the same lifecycle entrypoint used locally.

Use repeated `--python-path PATH` or TOML `paths = ["src", "tests"]` to choose files/directories; explicit extensionless scripts are supported. Paths must remain inside the repository. The default is `.`. `--no-python` opts out of updating an installed profile; it does not remove its files. Selection and retention are visible through `source-code explain`.

Commit the profile policy and lockfile. Provision tools explicitly with `python3 scripts/check-python.py tools`; checks verify the lockfile and installed environment with `uv sync --locked --check` and do not silently repair it. Checker installation ignores inherited environment redirection and uses `.python-quality/.venv`; linked tooling directories are rejected.

The locked toolchain uses Ruff format checking and safety/lint rules, `ty` with stronger diagnostics and Ruff annotation checks, and pip-audit. Ruff requires explicit function annotations, and ty uses its recommended stronger diagnostics with warnings treated as errors. Explicit `Any` in function signatures and blanket checker disables are rejected. Ty uses the root `.venv` for project imports and its target Python version, falling back to the pinned tooling environment when no root `.venv` exists. Provision the project environment with its supported Python version before checking version-specific APIs; the checker tooling itself requires Python 3.11+. Generic `type: ignore` comments cannot suppress ty diagnostics. Validated external JSON can be narrowed to explicit models at the boundary; casts do not replace input validation. Use precise, justified line-level exceptions only when the operation requires them, such as a constructed subprocess argv boundary. Do not add global rule disables or type ignores to make a gate pass.

## Lifecycle and project gates

| Stage | Introduced Python gate |
| --- | --- |
| research | Strict type checking, plus configured inherited gates. |
| alpha | Check-only formatting, lint/security rules, strict typing, project tests, and inherited gates. |
| beta / production | Alpha checks plus dependency vulnerability auditing. Production obligations still need project-specific evidence. |

Run `python3 scripts/check-source-code.py python` for the selected lifecycle gate. The standalone runner also supports `format`, `lint`, `typecheck`, `test`, `audit`, `alpha`, and `all`. Formatting is check-only.

Configure test argv and explicitly retained gate argv under `commands.test` and `commands.legacy` in `.python-quality.json`. The default test command is `uv run --locked pytest` in the application's environment; declare project dependencies/tests or configure an appropriate existing command. Project hooks are explicitly trusted repository code and retain their environment; the checker environment is isolated separately. Inherited gates run once for typecheck/research, test, alpha, and all. Preserve other repository gates even when they are not configured in this profile.

## Dependency audit boundaries

The full gate audits pinned checker dependencies and supported runtime uv locks associated with the root and selected source scope. Export uses locked metadata with builds disabled; the auditor does not install runtime packages. Known unsupported/unlocked dependency manifests fail the audit rather than claiming tooling-only runtime coverage. This includes pyproject, setup.py/setup.cfg, requirements inputs, Pipfile, Poetry/PDM locks, and Conda manifests. It never executes a manifest to discover dependencies.

An audit finding, unavailable service, stale lock/environment, missing test command, or uninspectable dependency declaration fails the corresponding gate. A successful audit reports known advisories for the exported locked dependencies under the current environment; it does not prove the software secure.
