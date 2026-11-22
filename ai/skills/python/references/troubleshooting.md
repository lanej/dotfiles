# Python troubleshooting

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

### pg8000 has two identically-named `paramstyle` attributes — only one is load-bearing

Setting the package-level `pg8000.paramstyle` attribute is a silent no-op; `cursor.execute()`
actually reads `pg8000.dbapi.paramstyle` at call time. Getting this wrong produces real param-
substitution failures with no exception pointing at the cause. Set `pg8000.dbapi.paramstyle`, not
`pg8000.paramstyle`. A unit test built against a mocked cursor cannot catch this — verify with a
real (or at least real-shaped) `pg8000` connection. (detail: memory "reference_pg8000_paramstyle_aliasing")

Read [worktree runtime lessons](worktree-lessons.md) when running verification in a fresh or relocated checkout.
