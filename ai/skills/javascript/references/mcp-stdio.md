# Node.js MCP stdio clients

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
