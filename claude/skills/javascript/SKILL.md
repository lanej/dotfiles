---
name: javascript
description: Node.js and JavaScript development patterns, gotchas, and library compatibility notes. Use when working with Node.js projects, TypeScript, React, antd, Zustand, Playwright, Bun, or Vitest.
---

# JavaScript / Node.js Skill

## Project Setup Basics

- Always check `package.json` first to understand available scripts before running anything
- Run `npm install` before attempting to execute Node.js scripts in a new project
- If a user specifies a script to run, use exactly what they specify

## Library Compatibility Gotchas

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

## SSE Streaming State Machine

When implementing Claude SSE streaming in a frontend:

### isStreaming Flag Order

Set `isStreaming: false` as the **FIRST** operation in the `done` handler — before appending the assembled message — so the UI re-enables input even if message assembly throws:

```typescript
// ✅ Correct order
eventSource.addEventListener('done', () => {
  set({ isStreaming: false });          // ← FIRST: re-enable UI
  appendMessage(assembleMessage());    // ← then handle message
});
```

**Safety net:** After the read loop exits, add a fallback in case the `done` branch was skipped:

```typescript
if (get().isStreaming) set({ isStreaming: false });
```

### Claude SSE Message Sequence

Claude SSE output is interleaved, not strictly sequential:

```
thinking block (once) → [text chunks ↔ tool_use/tool_result cycles]
```

Store a `segments: MessageSegment[]` array and **flush the text buffer on each `tool_use` event** to preserve interleave order in the rendered UI.

## MCP Stdio Servers (Node.js Implementation)

When building a Node.js client that connects to stdio MCP servers (pkm, memory):

### Spawn Once at Startup

Use `StdioClientTransport` from `@modelcontextprotocol/sdk/client/stdio.js` and create the transport **once at app startup**, not per-request:

```typescript
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

// ✅ Create once at startup
const transport = new StdioClientTransport({ command: 'pkm', args: ['mcp'] });
const client = new Client({ name: 'my-app', version: '1.0' }, { capabilities: {} });
await client.connect(transport);
```

### Auto-Respawn on Exit

```typescript
transport.onclose = () => sessions.delete(name);
// Re-create on next access — don't pre-spawn
```

### Environment Inheritance

Always spread `process.env` first so the child inherits `PATH` and critical env vars:

```typescript
new StdioClientTransport({
  command: 'pkm',
  args: ['mcp'],
  env: { ...process.env, ...server.env }  // ← process.env FIRST
});
```

## Astro

### Content Collections (v5+)

Config file location changed: `src/content/config.ts` → **`src/content.config.ts`** (at `src/` root, NOT inside `src/content/`). Must use explicit loaders — the legacy glob-by-convention format was removed.

```typescript
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'zod';  // import from 'zod' directly — astro:content re-export is deprecated

const guides = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/guides' }),
  schema: z.object({ title: z.string() }),
});
export const collections = { guides };
```

Rendering MDX content — `entry.render()` removed, use standalone `render()`:
```typescript
import { getCollection, render } from 'astro:content';
const entries = await getCollection('guides');
const { Content } = await render(entries[0]);
```

Entry ID: use `entry.id` (not `entry.slug`) in `getStaticPaths` params.

### Scripts Referencing public/ Files

`<script src="/public-file.js">` in a `.astro` page is processed by Vite (bundled). Files in `public/` can't be bundled — add `is:inline` to pass the tag through as an external reference:

```astro
<script src="/process-visual-renderer.js" is:inline></script>
```

Without `is:inline`, Astro throws: *"references an asset in the public/ directory. Please add the is:inline directive."*

**CRITICAL:** `is:inline` with `src` does NOT inline the file content. It keeps the `<script src="...">` tag verbatim — the browser still fetches it as an external file. Absolute paths (`/foo.js`) fail silently when the page is opened via `file://` (no server).

### True Script Inlining (for file:// / no-server builds)

To embed script content directly into the HTML (required for `file://` access or self-contained pages):

```astro
---
import pvData from '../../public/data/process-visual.js?raw';
import pvRenderer from '../../public/process-visual-renderer.js?raw';
---

<Fragment set:html={`<script>${pvData}</script><script>${pvRenderer}</script>`} />
```

`?raw` reads the file content as a string at build time. `Fragment set:html` emits it as raw HTML. Pair with `build.inlineStylesheets: 'always'` in `astro.config.mjs` to make the full page self-contained:

```js
// astro.config.mjs
export default defineConfig({
  build: { inlineStylesheets: 'always' },
});
```

**Verification:** after building, confirm `grep "src=" dist/index.html` returns zero external script refs, and `grep "_astro" dist/index.html` returns zero asset links.

### MDX: Escape `<` in Markdown Table Cells

Bare `<` in MDX table cells is parsed as a JSX tag opener. Build fails with: *"Unexpected character ',' in name, expected a name character."*

```mdx
<!-- ❌ breaks -->
| 1 | Low (<$100K) |

<!-- ✅ fix -->
| 1 | Low (&lt;$100K) |
```

Escape `<` as `&lt;` in any MDX markdown table cell containing it.

### Dev Server: public/index.html Not Served at /

Astro dev server does **not** serve `public/index.html` at `/` — the router intercepts first and 404s. Production build works correctly (`public/` files copy to `dist/` after page generation, overwriting Astro output).

Fix for dev: create `src/pages/index.astro` with the same content. In production, `public/index.html` overwrites it.

Other `public/` filenames (e.g., `/principles.html`, `/walkthrough.html`) serve correctly in dev — only the root `/` conflicts.
