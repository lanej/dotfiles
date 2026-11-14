# Update ancillary projects

Use `project-update` for an individual project or the registered set. Each project owns its build, installation and restart behavior; the driver coordinates commands without managing processes. uv, Python 3.11+ and Git are required; the command uses uv to select a compatible Python. Run `make shell` to link the command after the change is checked out in your normal dotfiles source, or invoke `./bin/project-update` directly.

```sh
project-update status --all --fetch
project-update update --all
project-update pull octo-manager
project-update build octo-manager
project-update restart octo-manager
project-update update zellij --dry-run
```

`update` runs pull → build → restart for each selected project. A failed step stops that project's sequence; independent projects still run. Commands emit progress and child output on stderr and one JSON result array on stdout. Exit 0 means complete, 1 means failure, 2 means invalid usage, and 3 means activation still requires manual work. There is no rollback across projects. Never infer that a process runs the latest revision from a successful build or an installed binary.

`pull` resolves the remote's current default branch, fetches it and fast-forwards a clean checkout already on that branch. It prefers `upstream` when present, otherwise `origin`; a registry entry can select `remote` explicitly. It preserves dirty checkouts, detached heads, topic branches, local commits and diverged history. It never stashes, resets, changes branches or pushes. Projects sharing a checkout pull it once per invocation. Concurrent mutations through this command are locked per checkout; this does not lock other Git tools.

`status` reports checkout revision, dirtiness, upstream revision and project-specific installed state. Its default upstream information is explicitly cached or unknown. Use `--fetch` to query the current default branch. A missing running revision is unknown, not evidence that installed and running versions match. `--dry-run` prints the selected steps and adapter argv without fetching, building, locking or restarting.

## Registered projects

| Project | Source and build | Restart |
| --- | --- | --- |
| `octo-manager` | `~/src/octo-manager`; frozen dependencies and the existing revision-specific installer with `--no-start`. Uses Octo's platform-specific private Bun when installed, otherwise Bun from PATH. | Requires the checkout revision to be installed, then uses Octo's existing installer/service controls. No service manager returns restart-required with its foreground command. Existing hooks and state are preserved. |
| `bedrock-router` | `~/src/bedrock-router`; Go build into a revision-specific cache, then its native installer with `--no-start --keep-env --preserve-mcp`. | Verifies that the staged and installed binary match, then uses the native installer to reload the service and check health. |
| `zellij` | Dotfiles' default branch; existing runtime, helper, plugin and configuration targets. The curated runtime policy and compatible pins remain authoritative. | Inspects existing sessions. Active sessions return restart-required and stay running. Exited/resurrectable sessions need no restart. New sessions load the installed version. |

Zellij's upstream default branch is a clean mirror and does not contain the curated fork features. Updating this installation therefore pulls the dotfiles default branch and installs its selected runtime; it does not replace the runtime with upstream main. The `zellij` entry includes its runtime and plugins in one update, following the existing installation conditions: configuration for every runtime, status compilation for non-release runtimes, and copy-hop for the patched runtime. Build includes installation but does not intentionally stop a running process. Zellij configuration also affects newly opened sessions.

The project scope is Zellij (including its plugins), Bedrock Router and OctoManager. `--all` means these three registered entries. A missing checkout is reported as a failure rather than skipped. Bedrock Router uses the standalone [lanej/bedrock-router](https://github.com/lanej/bedrock-router) source checkout, not the old dotfiles implementation. Its installer preserves environment and MCP choices and honors `CODEX_HOME`; credentials and session state remain in their existing locations. After staging, the adapter records the installed source revision and binary hash beside the binary. Status checks that hash, so the installed revision stays visible when the checkout advances and becomes unknown if the binary is replaced outside this command.

## Add a project

The bundled registry is `config/project-updates.toml`. Use `--config PATH` for a machine-specific replacement registry. Paths expand `~` and `{dotfiles}`. Command arguments also expand `{python}` to the driver's Python executable. Commands are argv arrays, executed in the checkout without a shell; the driver appends one action.

```toml
[projects.example]
path = "~/src/example"
command = ["./scripts/project-update"]
remote = "origin"
```

Implement `build`, `restart` and `status` in that project's adapter. `status` must write one JSON value to stdout. Other actions may write diagnostic output. `build` installs or stages the selected checkout; `restart` activates the built version using the project's existing mechanism and returns 3 when manual activation remains. An optional `clean` removes only project-owned build artifacts and never participates in `update` automatically. The bundled adapters currently reject `clean` rather than deleting releases, sessions, dependencies or state. Adapter failures propagate unchanged, except that the driver aggregates each project's result. The driver implements `pull`; adapters must not pull implicitly.

Validate with `make test-project-update`. The detector uses real local Git remotes and controlled project adapters; it does not compile workstation software or restart live services.
