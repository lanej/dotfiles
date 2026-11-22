# Python / uv

Before selecting application tools or an API protocol, read [the installed project policy](../../source-code-lifecycle/SKILL.md). Apply the declared authority and adoption at the configured maturity; preserve external providers’ protocols and established stacks according to that policy.

Follow the verification commands in this skill’s installed entrypoint. Use the installed testing guidance for proportionate evidence and preserve existing repository gates and root configuration.

`uv` replaces pip, virtualenv, poetry, and pyenv. Standard `uv` subcommands work as documented;
this file covers only the defaults to hold to and the traps that have actually cost time.

## Never use pip

| Instead of | Use |
|---|---|
| `pip install X` | `uv add X` |
| `pip install -r requirements.txt` | `uv add -r requirements.txt` to import into a uv project; `uv sync` thereafter |
| `pip freeze > requirements.txt` | `uv lock` (commit `uv.lock`) |
| `python -m venv` + `source .venv/bin/activate` | nothing — `uv run` handles it |
| `python script.py` | `uv run script.py` |
| `pip install black` (global) | `uv tool install black` |

`uv pip ...` exists for legacy compat. Reach for it only when a project genuinely cannot migrate.

## Defaults

- **Never activate a venv.** `uv run <cmd>` syncs and executes in one step; activation drifts.
- **Pin the interpreter**: `uv python pin 3.11` writes `.python-version`. Commit it.
- **Commit `uv.lock`.** In CI use `uv sync --locked` / `uv run --locked` so a stale lockfile fails
  the build instead of being silently rewritten. `--frozen` skips the freshness check; use it only
  when deliberately consuming the existing lockfile without validating project metadata.
- **Dev deps go in a group**: `uv add --dev pytest ruff ty`.

## One-off scripts: PEP 723 inline metadata

Preferred over `--with` flags because the script stays self-describing and portable:

```python
# /// script
# dependencies = ["requests", "rich"]
# ///
```

Then `uv run script.py`. Use `uv run --with pandas --with matplotlib analyze.py` only for
throwaway invocations where editing the file isn't worth it.

Read [troubleshooting](troubleshooting.md) when investigating uv cache access, Unicode JSON output, or PostgreSQL connection arguments.
