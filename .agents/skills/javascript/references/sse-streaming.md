# SSE streaming state

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
