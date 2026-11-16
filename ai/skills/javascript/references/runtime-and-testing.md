# Runtime compatibility and testing failures

## Library Compatibility Gotchas

### Optional/lazy-loaded peer dependencies fail silently at runtime, not at build/test/lint
A component that dynamically imports an optional peer dependency (chart libraries like ECharts, PDF/canvas renderers, syntax highlighters commonly do this) can pass `tsc`/`vite build`/lint/unit tests cleanly even when that dependency was never added to `package.json` — none of those steps actually execute the dynamic `import()` call, and the component's own error boundary may swallow the runtime failure with zero console output. This surfaces only on the first feature that newly exercises that dependency path. Fix: after wiring in a new usage of any library with lazy/optional dependencies, run a live render/runtime smoke check (Playwright drive, browser-mode test, or manually running the app) in addition to the normal build+lint+test suite — don't treat green CI as sufficient for that one class of change. (detail: memory "feedback_optional_peerdep_runtime_failure_invisible_to_tests")

### LobeHub / antd-style + Zustand 5 Conflict

`@lobehub/ui` and `antd-style` bundle Zustand 3.x internally. Mixing them with Zustand 5 crashes every state update with:

```
TypeError: h.use is not a function
```

**Fix:** NEVER import `@lobehub/ui` or `antd-style` in projects using Zustand 5. Use `antd` + `theme.useToken()` instead.

**Check before adding LobeHub deps:**
```bash
find node_modules -path '*antd-style*zustand*'
```

### Playwright + antd TextArea

`page.fill()` does NOT trigger React `onChange` on antd `TextArea` components.

**Fix:** Use `page.type()` instead:
```typescript
// ❌ Broken with antd TextArea
await page.fill('textarea', 'my text');

// ✅ Works
await page.type('textarea', 'my text');
```

### Stale TS Language-Server Diagnostics in Worktree/Multi-Session Environments

"Cannot find module" or similar TS language-server diagnostics surfacing in tool output are frequently stale false positives, not real errors — especially with multiple git worktrees or concurrent sessions editing overlapping files in the same monorepo. The language server's module-resolution cache doesn't reliably track fast concurrent filesystem changes across worktrees. Recurring pattern, confirmed across 5+ separate sessions.

**Fix:** Never trust an IDE/language-server diagnostic block at face value. Verify with the real toolchain before treating it as a regression:
```bash
tsc -b          # module-resolution / type errors
vitest run      # test failures
vite build      # build failures
```
Clean run = diagnostic was stale, proceed. Reproduced failure = real, fix it. A plausible-looking diagnostic is not an exception to this check — plausibility is exactly the failure mode.

### React Testing Library Text-Collision False Failures

`getByText(...)` throws `getMultipleElementsFoundError` when the queried string appears more than once in the rendered tree — not necessarily a bug in the component, often just two unrelated pieces of UI (or two test fixture values) that happen to render identical text. Recurred twice in the same repo within 24 hours: once from two fixture rows independently landing on the same formatted value (e.g. two unrelated metrics both displaying "90%", or a capture-rate constant colliding with an unrelated leaderboard row that also happened to be "39.4%"), and once from a panel's `<Card title="X">` heading colliding with a `KpiTile`'s plain-text metric label rendering the same string `"X"` elsewhere in the same panel.

**Fix, in order of preference:**
1. If the collision is a coincidental fixture-value clash (not a real UI ambiguity), change one of the fixture's numbers so the test data is text-unique — cheapest fix, no test logic change.
2. If the collision is a real duplicate in the UI (e.g. a title and a label legitimately share the same string), stop using `getByText` for that assertion and query more specifically: `getByRole("heading", { name: "X" })` to target only the semantic heading, or `getAllByText("X")` with a length assertion if multiple matches are actually expected and desired.
Don't "fix" a real UI duplication by making the test pass via `getAllByText()[0]` without checking which element you actually got — that hides which of the two elements is under test.

### jsdom Doesn't Catch Real-Browser CSS Layout/Intrinsic-Sizing Bugs

A 100%-green vitest/jsdom run is not sufficient evidence a CSS sizing or layout change renders correctly — jsdom doesn't perform real layout. Confirmed instance: an inline `<svg>` with no `width`/`height` attribute, sized via `width: auto; height: auto; max-width: 116px; max-height: 27px` to fit a bounding box, rendered as an invisible 0×0 box in a real browser while 611/611 vitest tests, lint, and build all passed. Unlike `<img>`, an inline `<svg>` with no `width`/`height` attribute has no browser-default intrinsic size — with both axes `auto` inside a shrink-to-fit container, it resolves to zero, a real layout computation jsdom never runs. Component structure, props, and test assertions were all correct; only actual browser layout exposed the failure.

**Fix:** give the element a real fixed `width` baseline (mirroring how a same-page `<img>` is already sized) plus `max-height` to reflow for a wider aspect ratio, rather than relying on `auto`/`auto` for both axes.

**Verify:** for any change touching inline SVG sizing, `auto` width/height on a non-`<img>` element, or other CSS layout mechanics, do a manual browser/Playwright check — a screenshot plus `getBoundingClientRect()` on the affected element — before calling the change done. Re-running vitest alone does not confirm it.

### Bun:sqlite in Vitest

`bun:sqlite` is a Bun built-in unavailable in Node.js/Vitest. Tests using it must run via `bun test`.

**Fix:** Exclude from Vitest:
```typescript
// vitest.config.ts
export default {
  test: {
    exclude: ['**/sqlite-session-store.test.ts']
  }
}
```
