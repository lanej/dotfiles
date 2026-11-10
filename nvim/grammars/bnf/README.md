# BNF grammar

Opening a `.bnf` file installs this bundled grammar through the configured Tree-sitter installer. The headless Neovim bootstrap includes it as well. Generated parser sources and compiled libraries stay untracked.

Use angle brackets for nonterminals, `::=` for definitions, and quoted strings for terminals. `|` separates alternatives, including a continuation line beginning with `|`. Both quote styles support backslash escapes; `""` represents an empty terminal. `#` starts a comment outside a quoted terminal.

```bnf
<expression> ::= <number> | <expression> "+" <number>
              | "(" <expression> ")"
<number> ::= "0" | '1'
<empty> ::= ""
```

The grammar provides highlights for the quoted-terminal BNF syntax shown above and retains the filetype's indentation.

Run `uv run --no-project scripts/test-nvim-bnf.py` to install and exercise it with real Neovim and the locked Tree-sitter plugins. The check requires `nvim`, `tree-sitter`, a C compiler, Git, and public GitHub access to fetch the plugins. `--plugins-dir PATH` can reuse clean checkouts at the locked revisions.
