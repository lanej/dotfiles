# 1M Context Does NOT Work on Vertex AI via OpenCode

## Critical Finding

**The 1M token context window DOES NOT WORK for ANY model on Vertex AI through OpenCode.**

Despite:
- ✅ Plugin loading successfully
- ✅ Plugin injecting beta header (`context-1m-2025-08-07`)
- ✅ Plugin logs showing "Beta header injected successfully"
- ✅ Model limits configured correctly (1M context, 64K output)

**Result:** API still rejects requests at 200K tokens with:
```
prompt is too long: 208054 tokens > 200000 maximum
```

## Evidence

**Database query results:**
```sql
SELECT MAX(input_tokens) FROM message WHERE input_tokens > 200000;
-- Result: No rows (ZERO successful requests >200K)
```

**Tested models:**
- ❌ Claude Opus 4.6 - Failed at 208K tokens
- ❌ Claude Sonnet 4.5 - (Assumed to fail, not thoroughly tested)
- ❌ Claude Sonnet 4 - (Not tested)

## Root Cause

OpenCode's `google-vertex-anthropic` provider does not pass the `betas` parameter to the Vertex AI API.

**Technical details:**

1. **Plugin sets:** `output.options.betas = ["context-1m-2025-08-07"]`
2. **Plugin hook:** `chat.params`
3. **OpenCode provider:** `google-vertex-anthropic`
4. **Likely using:** `@ai-sdk/google-vertex` (Google's generic AI SDK)
5. **Should use:** `@anthropic-ai/vertex-sdk` (Anthropic's Vertex SDK with beta support)

The `@ai-sdk/google-vertex` package likely doesn't support Anthropic-specific beta headers.

## What This Means

**All Vertex AI models are limited to 200K tokens through OpenCode**, regardless of configuration:

- Claude Opus 4.6: 200K (not 1M)
- Claude Sonnet 4.5: 200K (not 1M)  
- Claude Sonnet 4: 200K (not 1M)
- Claude Haiku 4.5: 200K
- All others: 200K

## Alternatives

### Option 1: Use Direct Anthropic API

Switch from Vertex AI to direct Anthropic API:

**Pros:**
- Full 1M context support
- All beta features work
- Direct support from Anthropic

**Cons:**
- Different billing (not through GCP)
- Need Anthropic API key
- Different rate limits

### Option 2: Use Amazon Bedrock

Switch to Bedrock provider:

**Pros:**
- 1M context confirmed working (OpenCode issue #12338)
- Plugin system already supports it

**Cons:**
- AWS instead of GCP
- Different billing

### Option 3: Wait for OpenCode Fix

File an issue asking OpenCode to fix Vertex AI beta header support.

**Timeline:** Unknown (could be weeks/months)

### Option 4: Use Vertex AI Directly

Bypass OpenCode and use Vertex AI API directly with Anthropic's SDK:

**Pros:**
- Full control over API calls
- Beta headers work

**Cons:**
- Lose OpenCode's tooling/UI
- Manual integration work

## Configuration Status

**Current config files:**
- `.opencode/opencode.json` - Has 1M limits for Sonnet models (doesn't work)
- `.opencode/plugins/vertex-1m.ts` - Injects beta header (doesn't reach API)
- `.opencode/plugins/README.md` - Documents the feature (misleading)

**Should we:**
1. ❌ Remove all 1M configurations (accept 200K limit)
2. ⚠️ Keep configs as-is (document they don't work, wait for fix)
3. ✅ File OpenCode issue (push for upstream fix)

## Recommended Actions

1. **File OpenCode GitHub issue:**
   - Title: "Vertex AI: Beta headers not passed to API (1M context doesn't work)"
   - Reference: This investigation
   - Request: Add proper beta header support for google-vertex-anthropic provider

2. **Update README with warning:**
   - Add prominent "DOES NOT CURRENTLY WORK" section
   - Explain the limitation
   - Point to GitHub issue

3. **Keep configurations:**
   - Leave plugin and model limits in place
   - When OpenCode fixes it, configs will work immediately
   - Debug logging available with `VERTEX_1M_DEBUG=1`

4. **For now: Use Sonnet 4.5 with 200K limit**
   - Accept the 200K limitation
   - Manually compact sessions as needed
   - Or switch to Bedrock/Direct API if 1M is critical

## Timeline

- **2026-02-16:** Initial implementation (plugin + model limits)
- **2026-02-17:** Discovered Opus doesn't work
- **2026-02-17:** Discovered NOTHING works (database shows zero >200K requests)
- **Next:** File OpenCode issue

## Files to Update

1. `.opencode/plugins/README.md` - Add "NOT WORKING" warning
2. Create GitHub issue with OpenCode
3. This document (for reference)

## Related Documentation

- `.opencode/OPUS_1M_LIMITATION.md` - Opus-specific analysis
- `.opencode/plugins/README.md` - Plugin documentation
- `.opencode/TOOL_PERSISTENCE_ISSUE.md` - Separate unrelated issue
- `.claude/VERTEX_1M_CONTEXT.md` - Claude Code investigation (also doesn't work)

## Contact

- OpenCode Issues: https://github.com/anomalyco/opencode/issues
- Related: Issue #12338 (Bedrock 1M context - WORKING)

---

**Bottom line:** The 1M context feature is completely non-functional on Vertex AI through OpenCode. The only way to get it working is to wait for an OpenCode fix or switch providers.
