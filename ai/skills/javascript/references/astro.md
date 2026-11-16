# Astro content and static output

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
