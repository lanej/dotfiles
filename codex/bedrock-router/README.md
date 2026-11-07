# Bedrock router

The router is maintained in [lanej/bedrock-router](https://github.com/lanej/bedrock-router), with its own implementation, tests, CI, installation, and releases. Follow that repository's installation instructions. Dotfiles no longer installs, upgrades, or restarts the router.

For an existing installation, use a standalone version that supports `install --keep-env --preserve-mcp`, preserves the existing service's environment file and session database, and provides both the OpenAI Responses and Anthropic Messages routes used by Codex and Pi. Do not replace it with the older v0.1.1 release.

The installed binary, configuration, and session database remain under `~/.codex/bedrock-router`. Moving the source checkout does not require restarting the service. Personal shell shortcuts, including `cxd`, remain in dotfiles. The `bedrock` tool selection still prepares shared credentials; it no longer installs a router. Existing router settings, MCP selections, and runtime state remain externally managed.

The optional live Paseo integration check uses a separately built router and its configuration:

```sh
PASEO_TASK_ROUTER_BIN="$HOME/src/bedrock-router/bedrock-router" \
PASEO_TASK_ROUTER_CONFIG="$HOME/src/bedrock-router/config.json" \
node scripts/test-paseo-task-router.mjs
```

This check starts a temporary instance with isolated session state and requires working Bedrock credentials and Pi. It does not change the installed service.
