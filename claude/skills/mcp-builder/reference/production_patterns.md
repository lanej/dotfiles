# Production MCP Server Patterns

Battle-tested patterns from a production TypeScript MCP server. Code-forward — adapt directly.

---

## 1. Usage Tracking

Intercept every tool call to accumulate per-tool call counts and last-called timestamps in a local JSON file. Use this data to make informed decisions about which tools to keep, promote to defaults, or retire.

**Why:** MCP servers with 20+ tool groups bloat the model's context window. Without usage data, trimming tools is guesswork.

### `src/core/usage.ts`

```typescript
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';

export interface ToolUsage { calls: number; lastCalled: string; }
export interface UsageStats { tools: Record<string, ToolUsage>; }

export function usageStatsPath(): string {
  return join(homedir(), '.config', 'myserver', 'usage.json');
}

export function readUsageStats(statsPath = usageStatsPath()): UsageStats {
  try {
    return JSON.parse(readFileSync(statsPath, 'utf-8')) as UsageStats;
  } catch {
    return { tools: {} };
  }
}

export function incrementToolCall(name: string, statsPath = usageStatsPath()): void {
  const stats = readUsageStats(statsPath);
  const record = stats.tools[name] ?? { calls: 0, lastCalled: '' };
  record.calls++;
  record.lastCalled = new Date().toISOString();
  stats.tools[name] = record;
  mkdirSync(dirname(statsPath), { recursive: true });
  writeFileSync(statsPath, JSON.stringify(stats, null, 2));
}
```

### Inject into `createMcpServer`

Wrap `server.tool` immediately after construction, before registering any handlers. The handler is always the last argument regardless of overload form.

```typescript
import { incrementToolCall } from '../core/usage.ts';

export function createMcpServer(context: MyContext): McpServer {
  const server = new McpServer({ name: 'myserver', version: VERSION });

  // Wrap tool registration to inject usage tracking
  const origTool = server.tool.bind(server);
  // @ts-ignore — wrapping overloaded method
  server.tool = (name: string, ...rest: unknown[]) => {
    const lastIdx = rest.length - 1;
    const origHandler = rest[lastIdx] as (...a: unknown[]) => Promise<unknown>;
    rest[lastIdx] = async (...a: unknown[]) => {
      const result = await origHandler(...a);
      incrementToolCall(name);
      return result;
    };
    return (origTool as (...a: unknown[]) => unknown)(name, ...rest);
  };

  // Register handlers AFTER wrapping
  registerIssuesTools(server, context);
  // ...
  return server;
}
```

### Display command

```typescript
// jira stats — show sorted table of tool usage
const stats = readUsageStats();
const entries = Object.entries(stats.tools).sort(([, a], [, b]) => b.calls - a.calls);
const nameWidth = Math.max(4, ...entries.map(([n]) => n.length));
console.log(`${'Tool'.padEnd(nameWidth)}  ${'Calls'.padStart(6)}  Last Called`);
for (const [name, usage] of entries) {
  const mins = Math.floor((Date.now() - new Date(usage.lastCalled).getTime()) / 60000);
  const rel = mins < 60 ? `${mins}m ago` : `${Math.floor(mins/60)}h ago`;
  console.log(`${name.padEnd(nameWidth)}  ${String(usage.calls).padStart(6)}  ${rel}`);
}
```

---

## 2. Resources vs. Tools

| | Tools | Resources |
|---|---|---|
| Triggered by | Model decision | Client attachment / passive injection |
| Protocol | `tools/call` | `resources/read` |
| Format | JSON (structured) | Markdown or plain text |
| Good for | Actions, mutations, queries with args | Read-only context, stable entities by URI |
| Client support | Universal | Only resource-aware clients (e.g. Claude Desktop) |

**Rule:** Implement tools first — they work everywhere. Add resources for entities with stable URIs that benefit from passive context injection (issues, docs, tickets). Never remove a tool just because a resource covers the same data; not all clients support resources.

### Registering a resource template

```typescript
import { ResourceTemplate } from '@modelcontextprotocol/sdk/server/mcp.js';

export function registerIssueResources(server: McpServer, context: MyContext): void {
  server.registerResource(
    'my-issue',                                          // internal name
    new ResourceTemplate('myapp://issues/{key}', { list: undefined }),
    { description: 'A Jira issue by key', mimeType: 'text/markdown' },
    async (uri, { key }) => {
      const issueKey = (Array.isArray(key) ? key[0] : key) ?? '';
      const data = await fetchIssue(issueKey);
      return {
        contents: [{ uri: uri.toString(), mimeType: 'text/markdown', text: renderMarkdown(data) }],
      };
    },
  );
}
```

`list: undefined` — template is discoverable but not listable (correct when there's no sensible default enumeration, e.g. all issues in a Jira instance).

### URI scheme convention

```
myapp://issues/{key}          → an issue by key
myapp://issuelinks/{id}       → a link relationship by ID
myapp://projects/{key}        → a project
```

Use the app name as the scheme. Keep it flat — sub-resources (`myapp://issues/{key}/links`) add surface area without new information if the parent resource already includes the child data.

### Markdown rendering for resources

Optimise for context injection — human-readable, not machine-parseable. Example issue resource:

```typescript
function issueToMarkdown(key: string, issue: RichIssue): string {
  const lines = [
    `# ${key}: ${issue.summary}`,
    '',
    `**Status**: ${issue.status} · **Type**: ${issue.type} · **Priority**: ${issue.priority}`,
    `**Assignee**: ${issue.assignee ?? 'Unassigned'}`,
  ];
  if (issue.links.length > 0) {
    lines.push('', '## Links');
    for (const link of issue.links) {
      if (link.outwardIssue) lines.push(`- ${link.type} → ${link.outwardIssue}`);
      else if (link.inwardIssue) lines.push(`- ${link.type} ← ${link.inwardIssue}`);
    }
  }
  if (issue.description) lines.push('', '## Description', '', issue.description);
  return lines.join('\n');
}
```

### Aligned table for relationships

For link/relationship resources, an aligned 3-column table reads better than prose:

```typescript
function alignedTable(h1: string, h2: string, h3: string, c1: string, c2: string, c3: string): string {
  const w1 = Math.max(h1.length, c1.length);
  const w2 = Math.max(h2.length, c2.length);
  const w3 = Math.max(h3.length, c3.length);
  const row = (a: string, b: string, c: string) =>
    `| ${a.padEnd(w1)} | ${b.padEnd(w2)} | ${c.padEnd(w3)} |`;
  const sep = `| :${'-'.repeat(w1 - 1)} | :${'-'.repeat(w2 - 2)}: | :${'-'.repeat(w3 - 1)} |`;
  return [row(h1, h2, h3), sep, row(c1, c2, c3)].join('\n');
}

// Usage: link type name as middle header, relation phrase centred in data row
alignedTable('From', link.type.name, 'To', fromCell, `*${link.type.inward}*`, toCell);
```

Output:
```
| CN-887 — [GLS] - New Carrier Integration [Inbox] | Polaris work item link | CNPD-39 — [GLS Group] - New Carrier Integration [In Development] |
| :------------------------------------------------ | :--------------------: | :---------------------------------------------------------------- |
| CN-887 — [GLS] - New Carrier Integration [Inbox] | *is implemented by*    | CNPD-39 — [GLS Group] - New Carrier Integration [In Development] |
```

---

## 3. Tool Config Gating

Allow users to enable/disable tool groups without modifying code. Gate resources and tools for the same domain behind the same flag.

```typescript
// src/core/tools.ts
import { z } from 'zod';

const ToolConfigSchema = z.object({
  enableIssues:    z.boolean().default(true),
  enableProjects:  z.boolean().default(true),
  enableUsers:     z.boolean().default(true),
  enableComments:  z.boolean().default(true),
  // Less-used groups default to false — opt-in
  enableAttachments: z.boolean().default(false),
  enableAuditlog:    z.boolean().default(false),
});

export type ToolConfig = z.infer<typeof ToolConfigSchema>;
export const DEFAULT_TOOL_CONFIG = ToolConfigSchema.parse({});

const SERVICE_MAP = {
  issues:      'enableIssues',
  projects:    'enableProjects',
  attachments: 'enableAttachments',
} as const;

export function isToolEnabled(config: ToolConfig, tool: keyof typeof SERVICE_MAP): boolean {
  return config[SERVICE_MAP[tool]];
}
```

```typescript
// createMcpServer — tools AND resources share the same gate
if (isToolEnabled(toolConfig, 'issues')) {
  registerIssuesTools(server, context);    // tools
  registerIssueResources(server, context); // resources — same gate
}
```

```typescript
// CLI flags for --only / --without
export function toolConfigFromFlags(only?: string[], without?: string[]): ToolConfig {
  if (only?.length) {
    // disable all, then enable named
    const cfg = ToolConfigSchema.parse(Object.fromEntries(
      Object.values(SERVICE_MAP).map(k => [k, false])
    ));
    for (const name of only) cfg[SERVICE_MAP[name as keyof typeof SERVICE_MAP]] = true;
    return cfg;
  }
  if (without?.length) {
    const cfg = { ...DEFAULT_TOOL_CONFIG };
    for (const name of without) cfg[SERVICE_MAP[name as keyof typeof SERVICE_MAP]] = false;
    return cfg;
  }
  return DEFAULT_TOOL_CONFIG;
}
```

---

## 4. stdio Transport Gotcha

**Do not use `StdioServerTransport` from `@modelcontextprotocol/sdk/server/stdio.js` in Bun.**

That class accesses `process.stdout` in its constructor, which switches Bun's stdout to 64 KB block-buffered mode. This silently truncates all large CLI output when piped.

Instead, write a thin custom transport that uses `writeSync(1, ...)` to bypass Bun's internal buffer:

```typescript
// src/mcp/stdio-transport.ts
import { writeSync } from 'node:fs';

export class SafeStdioTransport {
  onmessage?: (msg: Record<string, unknown>) => void;
  onerror?: (err: Error) => void;
  onclose?: () => void;

  private buffer = '';

  async start(): Promise<void> {
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk: string) => {
      this.buffer += chunk;
      this.drain();
    });
    process.stdin.on('error', (err: Error) => this.onerror?.(err));
    process.stdin.on('end', () => this.onclose?.());   // ← fires when stdin closes
    process.stdin.resume();
  }

  async send(message: Record<string, unknown>): Promise<void> {
    writeSync(1, `${JSON.stringify(message)}\n`);
  }

  async close(): Promise<void> {
    process.stdin.pause();
    process.stdin.removeAllListeners();
    this.onclose?.();
  }

  private drain(): void {
    for (;;) {
      const idx = this.buffer.indexOf('\n');
      if (idx === -1) break;
      const line = this.buffer.slice(0, idx).trimEnd();
      this.buffer = this.buffer.slice(idx + 1);
      if (!line) continue;
      try {
        this.onmessage?.(JSON.parse(line) as Record<string, unknown>);
      } catch (err) {
        this.onerror?.(err instanceof Error ? err : new Error(String(err)));
      }
    }
  }
}
```

**Key:** `onclose` fires when stdin closes. The server shuts down when onclose fires. This matters for testing — see next section.

---

## 5. Testing Without a Real MCP Client

**Do not close stdin before reading all responses.** The transport fires `onclose` on stdin end, which shuts down the server. If the server is mid-async-operation (e.g. awaiting a network call), closing stdin kills it before it can respond.

Use Python's `threading` module to read responses concurrently while keeping stdin open:

```python
import subprocess, json, threading

def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    proc = subprocess.Popen(
        ['myserver', 'mcp', 'stdio'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    result = {}
    done = threading.Event()

    def reader():
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if msg.get('id') == 2:
                    result['msg'] = msg
                    done.set()
                    return
            except Exception:
                pass

    threading.Thread(target=reader, daemon=True).start()

    init = json.dumps({
        'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
        'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                   'clientInfo': {'name': 'test', 'version': '1'}},
    })
    call = json.dumps({
        'jsonrpc': '2.0', 'id': 2,
        'method': 'tools/call',
        'params': {'name': tool_name, 'arguments': arguments},
    })

    proc.stdin.write(init + '\n' + call + '\n')
    proc.stdin.flush()

    # Wait for response BEFORE closing stdin
    if done.wait(timeout=15):
        contents = result['msg'].get('result', {}).get('content', [])
        return json.loads(contents[0]['text']) if contents else {}

    proc.stdin.close()
    proc.wait()
    return {}
```

**For resources** (`resources/read`):

```python
call = json.dumps({
    'jsonrpc': '2.0', 'id': 2,
    'method': 'resources/read',
    'params': {'uri': 'myapp://issues/PROJ-123'},
})
# ... same pattern; extract result['msg']['result']['contents'][0]['text']
```
