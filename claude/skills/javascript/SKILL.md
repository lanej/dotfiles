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
