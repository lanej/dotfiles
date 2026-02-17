# OpenCode Plugins

## vertex-1m.ts

Enables 1M token context window for Claude models on Google Vertex AI.

### Background

By default, Claude models on Vertex AI have a 200K token context window. The `context-1m-2025-08-07` beta header enables a 1M token context window for specific Claude 4 models.

**This requires TWO configuration pieces:**
1. **Beta header injection** - The plugin injects the beta header into API requests
2. **Model-specific context limits** - OpenCode needs to know the actual 1M limit for compaction

This plugin hooks into OpenCode's `chat.params` to inject the beta header, similar to the [Bedrock plugin pattern](https://github.com/anomalyco/opencode/issues/12338#issuecomment-3909808717).

### Supported Models

According to [Anthropic's documentation](https://docs.anthropic.com/en/docs/about-claude/models), only these models support the 1M context window with the beta header:

- **Claude Opus 4.6** (`claude-opus-4-6`)
- **Claude Sonnet 4.5** (`claude-sonnet-4-5@20250929`)
- **Claude Sonnet 4** (`claude-sonnet-4@20250514`)

**NOT supported** (stay at 200K):
- All Haiku variants (including Haiku 4.5)
- Claude 3 models
- Most legacy Claude 4 variants (Opus 4.5, Opus 4.1, etc.)

### Configuration

**Two-part configuration required in `opencode.json`:**

```json
{
  "plugin": [
    "opencode-gemini-auth@latest",
    "file://{config}/plugins/vertex-1m.ts"
  ],
  "provider": {
    "google-vertex-anthropic": {
      "models": {
        "claude-opus-4-6": {
          "limit": {
            "context": 1000000,
            "output": 128000
          }
        },
        "claude-sonnet-4-5@20250929": {
          "limit": {
            "context": 1000000,
            "output": 64000
          }
        },
        "claude-sonnet-4@20250514": {
          "limit": {
            "context": 1000000,
            "output": 64000
          }
        }
      }
    }
  },
  "compaction": {
    "auto": true,
    "prune": true,
    "reserved": 20000
  }
}
```

**Configuration explained:**
1. **Plugin** - Injects `context-1m-2025-08-07` beta header for supported models
2. **Model limits** - Tells OpenCode the actual 1M context limit (so compaction triggers at ~980K, not ~180K)
3. **Compaction** - Auto-compaction enabled, triggers at (1M - 20K reserve) = ~980K tokens

### Pricing Warning

**Long-context pricing applies to requests exceeding 200K tokens.**

From [Anthropic's pricing documentation](https://docs.anthropic.com/en/about-claude/pricing#long-context-pricing):
- Requests ≤ 200K tokens: Standard pricing
- Requests > 200K tokens: Long-context pricing (higher rate)

**Cost implications:**
- A 500K token session costs MORE than 2.5x a 200K session
- Monitor token usage in OpenCode TUI
- Consider manual compaction before hitting long-context pricing threshold

### Verification

To verify the 1M context is working:

1. **Check configuration**: Ensure both plugin and model limits are configured
2. **Watch token counter**: OpenCode TUI shows current token usage
3. **Observe compaction**: Auto-compaction should trigger near ~980K (not ~180K)
4. **Test with >200K**: Accumulate >200K tokens without API errors

**Note**: Models will still report "200K token context window" when asked about their limits (they don't know about beta features). The actual API limit is what matters.

### Implementation Details

- **Provider ID**: `google-vertex-anthropic` (not `google`)
- **Hook**: `chat.params` 
- **Option injected**: `output.options.betas = ["context-1m-2025-08-07"]`
- **Model-specific limits**: Override `limit.context` and `limit.output` per model
- **Compaction trigger**: (1M context) - (20K reserve) = ~980K tokens

### Troubleshooting

**Auto-compaction still triggers at ~180K:**
- Check that `provider.google-vertex-anthropic.models` is configured with `limit.context: 1000000`
- Verify you're using a supported model (Opus 4.6, Sonnet 4.5, or Sonnet 4)
- Restart OpenCode after configuration changes

**API errors at >200K tokens:**
- Verify plugin is loaded: Check OpenCode startup logs
- Confirm model is supported: See "Supported Models" section above
- Check Google Vertex AI region: Beta features may not be available in all regions
