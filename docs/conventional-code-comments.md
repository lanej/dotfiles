# Conventional code comments

Use `TAG: explanation` within the language's normal comment syntax when a
recognizable annotation helps readers find rationale, constraints, or consequences.
Use uppercase tags immediately followed by a colon and a space. Put optional
ownership and issue references in the explanation, not between the tag and colon.

| Tag | Use |
| --- | --- |
| `TODO` | Planned work. |
| `FIXME` | A known defect. |
| `HACK` | A temporary workaround; explain why it is needed and when it can go. |
| `NOTE` | Context that helps readers understand the code. |
| `WHY` | Rationale for a decision or otherwise surprising behavior. |
| `WARN` | A hazard or consequence callers and maintainers must avoid. |
| `PERF` | A performance constraint or tradeoff. |
| `SEE` | A reference to relevant documentation, code, or an issue. |

```python
# WHY: Preserve ordering because callers use the first match.
# FIXME: Expired credentials currently bypass the refresh path.
# TODO: Add cancellation support; see project/repo#123.
# HACK: Retry once until the upstream timeout defect is fixed; owner: API team.
```

Explain information the code does not make clear. Keep ordinary comments,
documentation comments, and docstrings when those forms communicate better.
Honor each repository's conventions and adopt these tags incrementally while
working on relevant code. Do not tag every comment or rewrite unrelated comments.
There is no bulk migration, snippet requirement, or lint enforcement.

Neovim uses the existing `Comment.nvim` editing commands and
`todo-comments.nvim` highlighting and search. `<leader>an` opens annotations in
FzfLua; `:TodoQuickFix` populates quickfix, where `]q` and `[q` navigate matches.
Plugin default tags and legacy `WTF`, `DAFUQ`, `GAH`, and `REF` remain recognized;
prefer the conventional tags above for new annotations.
