# Bedrock router for Codex and ChatGPT SSH hosts

Routes `openai.gpt-6.1-sol` to Mantle in `us-east-1`; all other models go to
`us-west-2`. Listens only on `127.0.0.1:18081`, forwards streaming responses,
and uses the bearer token supplied by Codex. Logs contain routing metadata,
never tokens or prompt bodies.

## Install or update

Use Python 3.11 or newer on macOS or Linux:

```sh
python3 codex/bedrock-router/install.py
```

On older Linux hosts, install a user-owned Python runtime with `uv`:

```sh
uv python install 3.13
uv run --python 3.13 --no-project codex/bedrock-router/install.py
```

The installer copies the checked-in source into `~/.codex/bedrock-router`,
backs up and updates `config.toml`, links `.env` to your existing private
`~/.config/bedrock/env`, and installs a launchd or systemd user service.
Run it again after updating this checkout. Existing model, reasoning effort,
project settings, and MCP definitions are preserved. Configuration using extra
Bedrock provider settings or a different `.env` source requires a manual merge.
`--no-start` writes files without starting the service.

On Linux, allow the service to survive logout and start at boot:

```sh
loginctl enable-linger "$USER"
```

If your host requires administrator permission, run that command with `sudo`.
The installer selects the Linux system CA bundle, including the CentOS/Rocky
path needed by managed Python runtimes.

## Private credentials

Create `~/.config/bedrock/env` privately on each host with these assignments:

```sh
export AWS_REGION=us-west-2
export AWS_BEARER_TOKEN_BEDROCK=<your-long-lived-bedrock-token>
```

Set its permissions to `600`. Never put the real token in this repository.
An SSH host uses its own token file. Codex must be available on the host's login
shell `PATH`; the ChatGPT app can then connect through its SSH host settings.
Restart the app or start a new remote session after installation.

`make codex` in the parent repository also manages `.codex/.env`; if it replaces
the credential link, rerun this installer after restoring the credential source.

## Checks and service management

```sh
python3 -m unittest discover -s codex/bedrock-router -p 'test_router.py'
curl --fail http://127.0.0.1:18081/healthz
```

On macOS, restart with:

```sh
launchctl kickstart -k "gui/$(id -u)/com.joshlane.codex.bedrock-router"
```

On Linux:

```sh
systemctl --user restart codex-bedrock-router.service
systemctl --user status codex-bedrock-router.service
```

After a cross-region encrypted-reasoning validation failure, the router retries
once with only the reasoning ciphertext removed. It preserves visible messages,
reasoning summaries, and tool calls/results. Encrypted compaction is never
removed: a task containing it must remain in its original region or begin a new
task with a visible handoff summary.
