# Math notation in QMD

Use inline math for short expressions and symbol references, and display math for equations whose structure deserves its own line. Keep each display delimiter on a separate source line. Preserve the project’s notation and define units, indices, and consequential assumptions.

## Display equations and definitions

```markdown
The weighted mean is

$$
\bar{x} = \frac{\sum_i w_i x_i}{\sum_i w_i}
$$

where:

- $x_i$ is observation $i$.
- $w_i$ is its nonnegative weight, with a positive total weight.
```

For compact definitions, an aligned block can keep the definitions next to the equation:

```latex
$$
\bar{x} = \frac{\sum_i w_i x_i}{W}
\qquad \text{where} \qquad
\begin{aligned}
  W &= \sum_i w_i \\
  x_i &= \text{observation } i \\
  w_i &= \text{weight of observation } i
\end{aligned}
$$
```

Use a separate list when definitions are too long for the available width. For a later equation that reuses the same terms, define only new terms and refer back to the established definitions. A derived quantity can have its own formula row instead of an ambiguous prose definition. Use `\tfrac` when a compact fraction helps inside an aligned definition.

## Symbols and spacing

- Use `\text{}` for word labels and label subscripts: `C_{\text{total}}`. Keep variable indices as variables: `x_i`.
- Use `\mathcal{S}` for a set when that notation is meaningful to the document.
- Use `\lvert x\rvert` for absolute value or cardinality. For tall contents that need scalable fences, use `\left\lvert ... \right\rvert`.
- Keep mathematical symbols in math mode. Renderer and font support differ; verify the actual HTML, PDF, or Word output before prescribing Unicode substitutions.
- Use font commands appropriate to math mode; avoid formatting a symbol as a code identifier merely to change its appearance.

## Verification

Inspect the rendered equation for missing glyphs, unexpected literal delimiters, cramped fractions, unreadable subscripts, and overflow. Check that the definitions and units describe the actual equation. Rendering success does not establish mathematical correctness. Avoid universal assumptions about one LaTeX engine, font, or page width; follow the project’s selected output and dependencies.

See [Quarto’s math syntax](https://quarto.org/docs/authoring/markdown-basics.html#equations) and [equation cross-references](https://quarto.org/docs/authoring/cross-references.html#equations) for supported notation and numbering.
