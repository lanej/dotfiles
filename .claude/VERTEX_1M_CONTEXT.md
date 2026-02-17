# 1M Token Context on Vertex AI - Claude Code Status

## Current Status: Testing in Progress

The 1M token context window for Vertex AI is **documented** in Claude Code docs but the implementation method is not explained.

## What We Know

### Confirmed from Documentation

From https://code.claude.com/docs/en/google-vertex-ai:

> ## 1M token context window
>
> Claude Sonnet 4 and Sonnet 4.5 support the 1M token context window on Vertex AI.
>
> **Note**: The 1M token context window is currently in beta. To use the extended context window, include the `context-1m-2025-08-07` beta header in your Vertex AI requests.

**Key fact**: If it's in the official docs, it MUST be supported somehow.

### What We've Found

1. **CLI flag exists**: `claude --betas context-1m-2025-08-07` (but marked "API key users only")
2. **No documented env var**: `ANTHROPIC_BETAS` not in settings docs
3. **Disable flag exists**: `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` can DISABLE betas

## Current Test Configuration

Added to `.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_USE_VERTEX": "1",
    "ANTHROPIC_VERTEX_PROJECT_ID": "easypost-platform",
    "ANTHROPIC_BETAS": "context-1m-2025-08-07"
  }
}
```

### Testing Needed

**To verify if this works:**

1. Start a new Claude Code session
2. Check token usage percentage in status
3. If based on 1M tokens → it works!
4. If based on 200K tokens → doesn't work, need different approach

## Alternative Possibilities

### Option A: Automatic Enablement

Maybe Claude Code **automatically** sends the beta header for Vertex AI users when using Sonnet 4/4.5? Test by checking token percentage.

### Option B: Wrapper Script

Update `~/.files/bin/claude-wrapper` to add `--betas` flag:

```bash
# Launch Claude Code with 1M context beta header
exec command claude --betas context-1m-2025-08-07 "$@"
```

**Problem**: Flag says "API key users only" - unclear if it works with Vertex AI.

### Option C: Feature Request

If no current method works, file feature request for Vertex AI beta header support.

## OpenCode Comparison (Already Working)

OpenCode fully supports 1M context for Vertex AI:

**Plugin** (`~/.files/.opencode/plugins/vertex-1m.ts`):
```typescript
output.options.betas = ["context-1m-2025-08-07"]
```

**Model config** (`~/.files/.opencode/opencode.json`):
```json
{
  "provider": {
    "google-vertex-anthropic": {
      "models": {
        "claude-sonnet-4-5@20250929": {
          "limit": {
            "context": 1000000,
            "output": 64000
          }
        }
      }
    }
  }
}
```

Result: Auto-compaction triggers at ~980K tokens (1M - 20K reserve).

## Supported Models (1M Context with Beta Header)

| Model | Context Window | Output Limit |
|-------|----------------|--------------|
| Claude Opus 4.6 | 200K → 1M (with beta) | 128K |
| Claude Sonnet 4.5 | 200K → 1M (with beta) | 64K |
| Claude Sonnet 4 | 200K → 1M (with beta) | 64K |

**NOT supported:**
- All Haiku variants (200K max)
- All Claude 3 models (200K max)
- Legacy Claude 4 variants (200K max)

## Cost Impact

**Long-context pricing applies when >200K tokens:**

| Model | ≤ 200K | > 200K |
|-------|--------|--------|
| Sonnet 4.5 input | $3/MTok | $6/MTok (2x) |
| Sonnet 4.5 output | $15/MTok | $22.50/MTok (1.5x) |

**With prompt caching (90% discount):**
- Cache read ≤200K: $0.30/MTok
- Cache read >200K: $0.60/MTok

**Extra cost**: ~$0.30 per million cached tokens when >200K.

## Next Steps

1. ✅ Added `ANTHROPIC_BETAS` env var to settings.json
2. ⏳ Test with new Claude Code session
3. ⏳ Verify token percentage shows 1M base
4. Document working solution or file feature request

## Related Files

- Claude Code config: `~/.files/.claude/settings.json`
- OpenCode plugin: `~/.files/.opencode/plugins/vertex-1m.ts`
- OpenCode config: `~/.files/.opencode/opencode.json`
- OpenCode docs: `~/.files/.opencode/plugins/README.md`
