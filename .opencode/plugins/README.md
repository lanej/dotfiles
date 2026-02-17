# OpenCode Plugins

## vertex-1m.ts

Enables 1M token context window for Claude models on Google Vertex AI.

### Background

By default, Claude models on Vertex AI have a 200K token context window. The `context-1m-2025-08-07` beta header enables a 1M token context window for supported models.

This plugin hooks into OpenCode's `chat.params` to inject the beta header into the provider options, similar to the [Bedrock plugin pattern](https://github.com/anomalyco/opencode/issues/12338#issuecomment-3909808717).

### Supported Models

- Claude Opus 4.6
- Claude Opus 4.5
- Claude Opus 4
- Claude Sonnet 4.5
- Claude Sonnet 4

### Configuration

The plugin is automatically loaded via `opencode.json`:

```json
{
  "plugin": [
    "opencode-gemini-auth@latest",
    "file://{config}/plugins/vertex-1m.ts"
  ]
}
```

### Verification

The plugin successfully injects the beta header into API requests. To verify 1M context is actually enabled:

1. Watch the token counter in OpenCode TUI during long sessions
2. If it exceeds 200K without erroring, the beta header is working
3. Compaction should trigger at ~980K tokens (with `compaction.reserved: 20000`)

**Note**: The model will still report "200K token context window" when asked about its limits, as it doesn't know about beta features. This is expected behavior - the actual API limit is what matters, not the model's self-report.

### Implementation Details

- **Provider ID**: `google-vertex-anthropic` (not `google`)
- **Hook**: `chat.params` 
- **Option injected**: `output.options.betas = ["context-1m-2025-08-07"]`
- **Compaction reserve**: 20,000 tokens (triggers at ~980K)

### Related Configuration

See `.opencode/opencode.json`:
- `compaction.reserved: 20000` - Token buffer for 1M context
- `compaction.auto: true` - Auto-compact when approaching limit
- `compaction.prune: true` - Remove old tool outputs to save tokens
