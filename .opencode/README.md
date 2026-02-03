# OpenCode Configuration

## Environment Variables

OpenCode MCP servers can access environment variables from `~/.env`.

### GitHub Token

The GitHub MCP server requires a GitHub personal access token. Instead of hardcoding it in `opencode.json`, we load it from the environment:

```bash
# In ~/.env
export GITHUB_PERSONAL_ACCESS_TOKEN="$(gh auth token)"
```

The MCP server configuration passes the environment variable through:

```json
{
  "github": {
    "command": [
      "podman",
      "run",
      "-i",
      "--rm",
      "-e",
      "GITHUB_PERSONAL_ACCESS_TOKEN",
      "ghcr.io/github/github-mcp-server"
    ]
  }
}
```

The `-e GITHUB_PERSONAL_ACCESS_TOKEN` flag passes the environment variable from the host into the container.

## Best Practices

- **Never hardcode secrets** in `opencode.json`
- Use `~/.env` for sensitive environment variables
- Load from `gh auth token` for GitHub credentials
- The `~/.env` file should be in `.gitignore`
