# Vertex AI

## Anthropic on Vertex AI — Critical Quirks

Failure modes found in direct use — follow exactly.

### Model IDs

Use **no version suffix** for the latest model on Vertex:

```typescript
// ✅ Correct (gets latest)
model: 'claude-sonnet-4-5'

// ❌ Wrong (version suffix not supported on Vertex)
model: 'claude-sonnet-4-6'
```

### SDK Selection

Use `@anthropic-ai/vertex-sdk`, **NOT** `@google-cloud/vertexai`:

```bash
npm install @anthropic-ai/vertex-sdk
```

The `@google-cloud/vertexai` package uses the wrong publisher path for Claude models and will fail with auth or routing errors.

**Publisher path:** Claude models live at `publishers/anthropic`, not `publishers/google`.

### anthropic_beta Header

Must be passed as an array in the request **body** — NOT as an HTTP header:

```typescript
// ✅ Correct: array in body
client.messages.create({
  model: 'claude-sonnet-4-5',
  max_tokens: 8000,
  anthropic_beta: ['interleaved-thinking-2025-05-14'],  // ← body, not header
  messages: [...]
});

// ❌ Wrong: HTTP header
headers: { 'anthropic-beta': 'interleaved-thinking-2025-05-14' }
```

### thinking Parameter

`{ type: 'adaptive' }` is **NOT** supported on Vertex. Use explicit `enabled` with a budget:

```typescript
// ✅ Correct for Vertex
thinking: { type: 'enabled', budget_tokens: 10000 }

// ❌ Not supported on Vertex
thinking: { type: 'adaptive' }
```

## BigQuery + Vertex AI

When combining BigQuery data with Vertex AI Claude calls, prefer the `bigquery` CLI skill for queries and pass results as structured context in the Claude API request body.
