# 1M Token Context on Vertex AI - Claude Code Limitation

## Current Status: Not Supported

Claude Code **does not currently support** the 1M token context window for Vertex AI Claude models.

## Background

- **OpenCode**: ✅ Supports 1M context via plugin system (implemented in `.opencode/plugins/vertex-1m.ts`)
- **Claude Code**: ❌ No mechanism to inject beta headers

### Why It Doesn't Work

The 1M context window requires the `context-1m-2025-08-07` beta header to be sent with API requests:

```typescript
// What OpenCode does (works):
output.options.betas = ["context-1m-2025-08-07"]

// What Claude Code needs (doesn't exist):
// No way to inject beta headers in settings.json
```

### What We've Tried

1. **Searched settings.json schema**: No `betas` field
2. **Checked environment variables**: No relevant env vars
3. **Reviewed documentation**: Mentions feature but not implementation
4. **Searched .claude/ directory**: No references to 1M context

## Documentation Reference

From https://code.claude.com/docs/en/google-vertex-ai:

> ## 1M token context window
>
> Claude Sonnet 4 and Sonnet 4.5 support the 1M token context window on Vertex AI.
>
> **Note**: The 1M token context window is currently in beta. To use the extended context window, include the `context-1m-2025-08-07` beta header in your Vertex AI requests.

**Problem**: The docs don't explain *how* to include the beta header in Claude Code.

## Possible Solutions

### Option 1: Feature Request

File an issue requesting beta header support in settings.json:

```json
{
  "env": {
    "CLAUDE_CODE_USE_VERTEX": "1",
    "ANTHROPIC_VERTEX_PROJECT_ID": "easypost-platform"
  },
  "vertexAi": {
    "betas": ["context-1m-2025-08-07"]
  }
}
```

### Option 2: Use OpenCode

OpenCode fully supports 1M context for Vertex AI:
- Plugin injects beta header automatically
- Model-specific limits configured
- Auto-compaction works correctly at ~980K tokens

Installation:
```bash
cd ~/.files
make opencode
```

### Option 3: Wait for Official Support

Monitor Claude Code releases for beta header support.

## Current Limits (Claude Code on Vertex AI)

| Model | Context Window |
|-------|----------------|
| Claude Opus 4.6 | 200K tokens |
| Claude Sonnet 4.5 | 200K tokens |
| Claude Sonnet 4 | 200K tokens |

All models will auto-compact at ~180K tokens (200K - 20K reserve).

## Workaround Impact

Without 1M context support:
- Must manually manage sessions at 200K boundary
- Cannot leverage extended context for long conversations
- Frequent compaction disrupts workflow

## Related Files

- OpenCode plugin: `~/.files/.opencode/plugins/vertex-1m.ts`
- OpenCode config: `~/.files/.opencode/opencode.json`
- OpenCode docs: `~/.files/.opencode/plugins/README.md`

## Next Steps

1. File feature request with Claude Code team
2. Use OpenCode for sessions requiring >200K context
3. Monitor Claude Code changelog for beta header support
