---
name: python
description: Use uv for fast Python project management, script execution, dependency handling, and tool installation. AVOID pip - always use uv commands (uv add, uv sync, uv run) instead.
---

# Python / uv

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
- **Dev deps go in a group**: `uv add --dev pytest ruff mypy`.

## One-off scripts: PEP 723 inline metadata

Preferred over `--with` flags because the script stays self-describing and portable:

```python
# /// script
# dependencies = ["requests", "rich"]
# ///
```

Then `uv run script.py`. Use `uv run --with pandas --with matplotlib analyze.py` only for
throwaway invocations where editing the file isn't worth it.

## Gotchas

### `uv run` fails with a `~/.cache/uv` permission error in a sandboxed shell

This is a sandbox filesystem-allowlist gap, **not** a corrupted cache. `uv cache clean` never fixes
it and just wastes a step. Fixed 2026-08-25 by adding `~/.cache/uv` to
`sandbox.filesystem.allowWrite` in `~/.claude/settings.json`, alongside the existing `/tmp` entries.

If it recurs: check that setting first — the fix may have reverted, or `uv cache dir` may point
somewhere new. `dangerouslyDisableSandbox: true` is a stopgap only.

### `json.dumps` silently mangles non-ASCII

`ensure_ascii` defaults to `True`, converting em-dashes, arrows, and smart quotes to `\uXXXX`
escapes with no error or warning. Any script serializing user-authored text must pass
`ensure_ascii=False`:

```python
json.dumps(data, indent=2, ensure_ascii=False)
```
