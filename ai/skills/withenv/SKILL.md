---
name: withenv
description: Use when running or debugging legacy EasyPost application commands with epenv or withenv, selecting per-command .env profiles in agent shells, or creating missing direnv configuration through epenv. Production srvenv uses its existing workflow.
---

# Legacy EasyPost command environments

Use `epenv PROFILE COMMAND [ARG ...]` for direct application commands from agent or interactive shells. It selects configuration on every invocation, delegates clean loading to `withenv`, and creates missing direnv configuration as needed. Direnv supplies the interactive shell's default environment; the parent shell remains unchanged when the command runs.

Inspect the repository's Makefile or task runner first. Use its existing recipes when they already invoke `withenv`; pass selectors to that runner rather than wrapping it again. Keep the repository's interpreter and dependency setup.

## Choose configuration per command

Prefer `epenv PROFILE COMMAND [ARG ...]` for direct application commands. Each invocation finds the nearest `.env` root within the current filesystem, requires `.env` and `.env-PROFILE`, and delegates to `withenv` with only those files selected and inherited `EXTRA_ENVFILES` cleared.

```sh
epenv test venv/bin/pytest tests/unit
```

When the selected application root has no `.envrc`, `epenv` calls `ep-direnv ensure` before execution. A non-bare repository with a GitHub EasyPost origin and tracked root `.env` qualifies for the shared generated `.envrc`, exact-content automatic approval, and worktree hooks. Tracked `.envrc` files are never generated over.

For routine use, let `epenv` handle setup instead of writing `.envrc` or approving it separately. Existing `.envrc` entries, including dangling symlinks, skip setup and keep their approval status. Repeated commands need no setup writes. The command profile stays in the child invocation; the generated `.envrc` keeps the shared interactive default. Setup failures stop the command.

Install the wrapper, shared helper, and direnv library with `make epenv` from `~/.files` if they are missing.

Profile names identify files, not `EP_ENVIRONMENT` values; the selected file controls those values. Missing profile files fail before the command runs. `.env-override` and `.env-secrets` are excluded unless the selected configuration itself sources them. Repeat `epenv` on every agent command because separate tool calls may use separate shells. It preserves command arguments, working directory, and exit status.

For recipes that invoke `withenv` internally, pass their selectors directly; an outer `epenv` selector does not survive a second clean environment load. For example: `ENVFILE=".env .env-test" make pytest EXTRA_ENVFILES=""`.

`withenv` finds the nearest ancestor containing `.env`, otherwise uses the current directory. Run from the intended checkout so another project's `.env` cannot become the root.

The default source order is `.env`, `.env-build`, `.env-runtime`, `.env-override`, `.env-secrets`. Later assignments win. `ENVFILE` replaces this list; `EXTRA_ENVFILES` appends to it. These are whitespace-separated shell-file paths, not named profiles. Use the repository's actual files; a `.env-test` example does not establish that a project has one.

```sh
# Append the repository's test overrides after all default files.
EXTRA_ENVFILES=.env-test withenv venv/bin/pytest tests/unit

# Select only the base and test files, excluding local override/secrets files.
ENVFILE=".env .env-test" EXTRA_ENVFILES="" withenv venv/bin/pytest tests/unit
```

The second form, like `epenv test`, also clears any inherited extra-file selection. For a recipe that already calls `withenv`, use its supported selector, for example `make pytest EXTRA_ENVFILES=.env-test` in claims-service. Inspect test prerequisites before running database setup or cleanup recipes.

Setting `ENVFILE` immediately before a bare command does not reload direnv. Setting `EP_ENVIRONMENT`, `DATABASE_URI`, `PATH`, or `PYTHONPATH` before `withenv` does not carry those variables into the child: `withenv` clears the incoming environment. Put loading-time configuration in the selected files. For a command-only override after loading, use `withenv env NAME=value command`; this does not change which files were sourced.

## Boundaries that matter

- Direnv's missing override/secrets fallback to the primary checkout is specific to the shared direnv loader. `withenv` reads files from its selected project root and does not inherit that fallback or the resulting values. Configure needed worktree files explicitly instead of assuming primary-checkout credentials will survive.
- Direnv's Python path and virtualenv path additions also do not survive the clean boundary. Use the repository's interpreter path and apply necessary command overrides after loading.
- `epenv` skips local setup inside `srvenv`, and `withenv` rejects `IN_SRVENV=1`. Use the established service command directly there.
- The installed `withenv` does not reliably stop on every sourcing error. For a configuration failure, inspect the relevant file and verify the required non-secret settings rather than treating command startup as proof of successful loading.

When diagnosing selection, inspect file names and assignment order. Verify required non-secret settings with targeted assertions; avoid printing the whole environment or credential values. Changing the interactive default or implementing a direnv loader is a separate configuration change, not needed for per-command selection.
