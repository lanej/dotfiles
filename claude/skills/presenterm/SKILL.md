---
name: presenterm
description: Build and run terminal-based presentations from markdown with presenterm - slide syntax, speaker notes, executable code blocks, mermaid/d2/LaTeX rendering, themes, and PDF/HTML export.
---

# presenterm

Terminal presentations from markdown. Slide bodies are ordinary markdown (headings, lists, tables,
fenced code, block quotes) — only the presenterm-specific extensions below need documenting.

## Slide structure

Slides are separated by `---` on its own line. First `#` is the slide title; a following `##` acts
as a subtitle on a title slide.

Speaker notes are HTML comments, visible only in presentation mode:

```markdown
<!-- speaker notes
- Mention the migration timeline
- Don't forget the cost table
-->
```

## Code block attributes

Appended after the language tag on the fence:

| Attribute | Effect |
|---|---|
| `+exec` | Runs on keypress `e` when the slide is shown; output appears below |
| `+exec_replace` | Runs automatically on slide load; output **replaces** the block |
| `+render` | Renders the block as an image (mermaid, d2, latex, typst) |
| `+width:80%` | Sizes a rendered image |

````markdown
```bash +exec
kubectl get pods
```

```d2 +render +width:80%
users -> lb -> api
```
````

Execution is opt-in at launch — a `+exec` block does nothing without the flag:

```bash
presenterm -x file.md              # enable +exec
presenterm -X file.md              # enable +exec_replace
presenterm --validate-snippets file.md   # typecheck without running
```

## Diagram and formula rendering

`+render` on `mermaid`, `d2`, `latex`, or `typst` blocks converts them to images at load time.
A missing renderer fails quietly, so install what the block needs: `mermaid` →
`@mermaid-js/mermaid-cli` (npm), `d2` → `d2`, `typst` → `typst`, `latex` → `typst` **and**
`pandoc` (pandoc converts the LaTeX to typst, typst rasterizes it). Tune output in `config.yaml`:

```yaml
typst:
  ppi: 300
mermaid:
  theme: dark
  background: "#2E3440"
  scale: 2.0
d2:
  theme: "Nord"
  scale: 1.5
```

## Running and exporting

```bash
presenterm file.md
presenterm -t catppuccin file.md     # --list-themes for the full set
presenterm --export-pdf file.md
presenterm -c /path/to/config.yaml file.md
```

Images need a terminal protocol; `--image-protocol auto` is the default. Force it when auto-detect
guesses wrong over SSH or in a multiplexer: `iterm2`, `kitty-local`, `kitty-remote`, `sixel`,
`ascii-blocks` (fallback).

## Config location

`~/.config/presenterm/config.yaml` (Linux),
`~/Library/Application Support/presenterm/config.yaml` (macOS).

```yaml
theme: catppuccin
image_protocol: auto
validate_overflows: true
enable_snippet_execution: false
```

## Keys during a presentation

`←`/`→` or `Space`/`Backspace` navigate; `g` jumps to a slide number; `e` executes a `+exec` block;
`f` fullscreen; `?` help; `q` quit.
