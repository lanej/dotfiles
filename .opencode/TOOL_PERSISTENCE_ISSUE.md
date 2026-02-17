# Tool Persistence Issue with 1M Context Window

## Issue Summary

When using the 1M token context window on OpenCode with Vertex AI Claude models, **tools intermittently become unavailable** at token counts well below the compaction threshold.

**Observed behavior:**
- Session at **182K tokens** (18% of 1M limit)
- Compaction configured to trigger at ~980K tokens (1M - 20K reserved)
- Bash tool suddenly reports as unavailable
- Error message shows bash is not in the available tools list

## Evidence

### Configuration (Working)

**1M context IS properly enabled:**
- Token counter shows: `182,775 tokens / 18% used`
- Math: 182,775 ÷ 0.18 = **1,015,416 tokens total** ✓
- Plugin loaded: `file://{config}/plugins/vertex-1m.ts` ✓
- Model limits configured: 1M context for Sonnet 4.5 ✓
- Beta header injected: `context-1m-2025-08-07` ✓

**Compaction settings:**
```json
{
  "compaction": {
    "auto": true,
    "prune": true,
    "reserved": 20000
  }
}
```

Should trigger at: 1,000,000 - 20,000 = **980,000 tokens**

### Error

At 182K tokens, model attempted to call bash and received:

```
Model tried to call unavailable tool 'bash'. Available tools: invalid, question, 
read, glob, grep, task, webfetch, todowrite, skill, gspace_*, sequential-thinking_*, 
memory_*, bigquery_*
```

**Note**: Bash is completely missing from the available tools list.

## Root Cause Analysis

This is **NOT a 1M context enablement issue** - the 1M context is working correctly.

**Possible causes:**

1. **Tool definition pruning bug**: OpenCode may be incorrectly pruning tool definitions from the system prompt when using extended context
2. **Prompt caching issue**: Tool definitions might not be properly cached, causing them to be lost
3. **Context window management**: The model's internal context management might be dropping tool schemas
4. **Beta feature instability**: The 1M context beta might have bugs with tool persistence

## Related Issues

- [OpenCode #12338](https://github.com/anomalyco/opencode/issues/12338) - Original 1M context enablement issue
- This appears to be a **separate issue** from context enablement

## Workarounds

### Short-term

**1. Start fresh sessions more frequently:**
- When approaching 150-200K tokens, start a new session
- This avoids hitting the tool persistence issue
- Preserve work by compacting manually before 150K if needed

**2. Manual compaction:**
- Trigger compaction manually if tools disappear
- This may refresh the tool definitions

### Long-term

**File a bug report** with OpenCode:

**Title**: Tool definitions lost in 1M context sessions at ~180K tokens

**Description**:
```
When using 1M context window (context-1m-2025-08-07 beta) with Vertex AI 
Claude Sonnet 4.5, tool definitions intermittently become unavailable at 
~182K tokens, well below the 980K compaction threshold.

Expected: Tools remain available throughout the full 1M context
Actual: Tools disappear from available list at ~18% usage

Configuration:
- Model: claude-sonnet-4-5@20250929
- Provider: google-vertex-anthropic
- Context limit: 1000000 tokens
- Compaction: auto=true, reserved=20000
- Plugin: vertex-1m.ts (beta header injection)

Error: "Model tried to call unavailable tool 'bash'"
```

## Monitoring

**Watch for these patterns:**

- Tool unavailability starting around 150-200K tokens
- Specific tools becoming unavailable (bash, edit, write)
- Tools working fine early in session, then disappearing
- Error mentioning tools not in available list

**Log when it happens:**
- Current token count
- Which tools are missing
- What triggered the tool call
- Session age / message count

## Verification Steps

To confirm the issue:

1. Start a session with 1M context enabled
2. Accumulate >180K tokens naturally (don't pad artificially)
3. Attempt to use bash tool
4. Check if bash appears in error message's available tools list

## Configuration Files

- Plugin: `~/.files/.opencode/plugins/vertex-1m.ts`
- Config: `~/.files/.opencode/opencode.json`
- This doc: `~/.files/.opencode/TOOL_PERSISTENCE_ISSUE.md`

## Status

- **1M Context**: ✅ Working correctly
- **Tool Persistence**: ❌ Intermittent failures at ~180K tokens
- **Workaround**: ✅ Start fresh sessions before 150K tokens
- **Bug Report**: ⏳ To be filed
