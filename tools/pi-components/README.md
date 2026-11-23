# Pi components

Reusable TypeScript terminal components on `@earendil-works/pi-tui`. This package has no dependency on the Pi coding agent, the daily driver, Socrates, Beads or a managed worktree. Its first component is the Vim-first selector used by the daily driver's Socrates adapter.

Install from a repository checkout with a local `file:` dependency on `tools/pi-components`. The package exports TypeScript source; callers need a TypeScript loader or bundler, as the Pi runtime and daily driver already provide. The package is private and is not published to npm. Package installation, scripts and tests use Bun from PATH at or above the minimum in `package.json` (`>=1.4.5`). [Studio](https://github.com/lanej/studio) consumes a vendored snapshot through its own lockfile; refresh that snapshot deliberately when changing this package.

## Selector

`createSelector` returns a Pi TUI `Component` with `render`, `handleInput`, and `invalidate`. The caller supplies a nonempty list, theme functions, a Markdown theme, the available height, a render callback and an `onSelect` callback. An index means an explicit Enter selection; `undefined` means cancellation. Completion fires once. Create a new component for each selection and keep its content stable while it is open.

```ts
import { createSelector } from "@lanej/pi-components";

const selector = createSelector({
  title: "Choose a deployment region",
  items: [
    { label: "West", description: "Primary region", details: "Near the customer." },
    { label: "East", description: "Recovery region" },
  ],
  theme, // accent, muted, bold, selected, and a Pi TUI Markdown theme
  height: () => terminal.rows - 2,
  requestRender: () => tui.requestRender(),
  onSelect: (index) => finish(index),
});
```

Mount the component in a Pi TUI container or return it from a Pi extension's `ctx.ui.custom` factory. The host owns overlay positioning, external cancellation, disposal and any later text input. The selector does not append special choices, persist answers or authorize work. Both prompt and items can carry Markdown explanations and caller-rendered `annotations`; annotation strings are trusted terminal output and may contain OSC 8 links, so sanitize untrusted data before constructing them. `selectorText`, `selectorLink` and `selectorLinks` provide terminal-safe plain text and HTTP(S) link rendering. Domain-specific source links and evidence validation belong to the caller.

Use `j`/`k` to move, `;` to enter visible letter hints, `l` to inspect details, and `h` to return. Completing a hint moves focus without submitting. Enter selects. Escape leaves hints or details before cancelling; Ctrl+C cancels directly. Focus follows resizing and scrolling. Wide layouts show a side preview; narrow layouts place it below the choices.

## Checks

```sh
bun install --cwd tools/pi-components --frozen-lockfile --ignore-scripts
bun run --cwd tools/pi-components quality:tools
make test-pi-components
```

The independent strict profile covers compiler, typed lint, formatting, interaction tests and dependency audit. Studio's independent workflow checks its vendored consumer. Native Socrates acceptance verifies the installed package through its real caller; it is described in [Studio's acceptance guide](https://github.com/lanej/studio/blob/main/acceptance/local-run.md).
