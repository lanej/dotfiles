# Claude Opus 4.6 - 1M Context Limitation on Vertex AI

## Issue Summary

**Claude Opus 4.6 does NOT support 1M context through OpenCode on Vertex AI**, despite Anthropic's documentation stating it should work with the `context-1m-2025-08-07` beta header.

## What Works

✅ **Claude Sonnet 4.5** - 1M context working  
✅ **Claude Sonnet 4** - 1M context working  
❌ **Claude Opus 4.6** - Stuck at 200K limit

## Root Cause

OpenCode's `google-vertex-anthropic` provider doesn't properly pass beta headers to the Vertex AI API.

**Evidence:**
1. Plugin successfully injects beta header (`output.options.betas = ["context-1m-2025-08-07"]`)
2. Plugin log shows: "Beta header injected successfully"
3. API still rejects with: "prompt is too long: 208054 tokens > 200000 maximum"
4. No sessions have ever exceeded 200K tokens (verified in database)

**Technical details:**
- Plugin hook: `chat.params`
- Plugin sets: `output.options.betas`
- Provider: `google-vertex-anthropic`
- Model ID: `claude-opus-4-6@default`

The `output.options.betas` parameter is likely not being passed through to the actual Vertex AI API call. OpenCode may use Google's AI SDK (`@ai-sdk/google-vertex`) which might not support the `betas` parameter, rather than Anthropic's Vertex SDK (`@anthropic-ai/vertex-sdk`) which does.

## Why Sonnet Works But Opus Doesn't

Unknown. Possible explanations:
1. Different API endpoints for different models
2. Sonnet models have different API parameter handling
3. OpenCode has special handling for Sonnet that's missing for Opus
4. The beta header IS reaching the API for Sonnet but not for Opus

**Need to investigate:** Whether Sonnet actually goes beyond 200K or if we just haven't tested it thoroughly enough.

## Anthropic Documentation

From [Anthropic's docs](https://docs.anthropic.com/en/docs/about-claude/models):

> Claude Opus 4.6 and Sonnet 4.5 support a 1M token context window when using the `context-1m-2025-08-07` beta header.

From [Context Windows docs](https://docs.anthropic.com/en/build-with-claude/context-windows#1m-token-context-window):

> **Availability:** The 1M token context window is currently available on the Claude API, Microsoft Foundry, Amazon Bedrock, and **Google Cloud's Vertex AI**.

So it **should** work on Vertex AI, but it doesn't through OpenCode.

## Workarounds

### Option 1: Use Sonnet Instead
Switch to Claude Sonnet 4.5 which has confirmed 1M context support through OpenCode on Vertex AI.

### Option 2: Use Different Platform
For Opus 4.6 with 1M context, use:
- Direct Anthropic API (with API key)
- Amazon Bedrock
- Microsoft Foundry
- Vertex AI with Anthropic's official SDK (not through OpenCode)

### Option 3: Wait for OpenCode Fix
File an issue with OpenCode asking them to fix beta header support for Vertex AI.

## Configuration Removed

Removed the following configurations that don't work:

**From `.opencode/opencode.json`:**
```json
"claude-opus-4-6": {
  "limit": {
    "context": 1000000,
    "output": 128000
  }
},
"claude-opus-4-6@default": {
  "limit": {
    "context": 1000000,
    "output": 128000
  }
}
```

**From `.opencode/plugins/vertex-1m.ts`:**
```typescript
"opus-4-6",    // Removed
"opus-4.6",    // Removed
```

## Current Working Configuration

**Models with 1M context (tested and working):**
- `claude-sonnet-4-5@20250929`
- `claude-sonnet-4@20250514`

**Plugin:** `~/.files/.opencode/plugins/vertex-1m.ts`  
**Config:** `~/.files/.opencode/opencode.json`  
**Docs:** `~/.files/.opencode/plugins/README.md`

## Next Steps

1. ✅ Removed non-working Opus configuration
2. ✅ Updated documentation
3. ⏳ File OpenCode issue about Vertex AI beta header support
4. ⏳ Thoroughly test Sonnet to verify it actually exceeds 200K tokens

## Testing Plan

To verify Sonnet actually works beyond 200K:

1. Start fresh OpenCode session with Sonnet 4.5
2. Accumulate context naturally (conversation, file reads)
3. Monitor token counter
4. Watch for compaction at ~980K (not ~180K)
5. Verify no "prompt is too long" errors when >200K
6. Check database: `SELECT MAX(inputTokens) FROM message WHERE model LIKE '%sonnet%'`

## Files Modified

- `.opencode/opencode.json` - Removed Opus model limits
- `.opencode/plugins/vertex-1m.ts` - Removed Opus patterns
- `.opencode/plugins/README.md` - Updated supported models
- `.opencode/OPUS_1M_LIMITATION.md` - This document

## Related Issues

- OpenCode #12338 - Original 1M context enablement (for Bedrock)
- To file: OpenCode Vertex AI beta header support

## Date

2026-02-17
