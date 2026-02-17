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
  ],
  "compaction": {
    "auto": false,
    "prune": true,
    "reserved": 20000
  }
}
```

**IMPORTANT**: Set `compaction.auto: false` to disable automatic compaction. Without this, OpenCode will compact at ~180K tokens (200K - 20K reserved) because it doesn't know about the increased 1M limit. You'll need to manually compact sessions using `<Leader>+c` when needed.

### Verification

The plugin successfully injects the beta header into API requests. To verify 1M context is actually enabled:

1. Watch the token counter in OpenCode TUI during long sessions
2. If it exceeds 200K without API errors, the beta header is working
3. Manually compact sessions when needed using `<Leader>+c`

**Note**: The model will still report "200K token context window" when asked about its limits, as it doesn't know about beta features. This is expected behavior - the actual API limit is what matters, not the model's self-report.

### Limitations

**OpenCode doesn't know about the increased limit**: OpenCode's compaction system uses the model's advertised context window (200K) to determine when to compact. Even though the API will accept 1M tokens with the beta header, OpenCode will try to compact at ~180K.

**Workaround**: Disable automatic compaction (`compaction.auto: false`) and manually compact when truly needed. This allows you to use the full 1M context window, but requires manual session management.

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
