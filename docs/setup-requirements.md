# Configuration and software installation requirements

Default setup must make the checkout useful for configuration before development runtimes exist. Software installation is a separate, explicit operation. These requirements govern the native OS baseline, machine TOML, composed tool sets, bootstrap, and full installation on macOS and Linux.

The requirements define intended behavior; the implementation and tests must remain consistent with them. See [issue #128](https://github.com/lanej/dotfiles/issues/128) for the regression that motivated this separation and the [installation guide](install.md) for usage instructions. **MUST** and **MUST NOT** identify required behavior. Requirement IDs remain stable as implementation details change.

## Command contract

| Command | Prerequisites | Permitted effects |
|---|---|---|
| `make` / `make base` | Make, Bash, standard system utilities | Initialize a missing machine TOML and link the built-in native configuration. |
| `make shell git` | Make, Bash, standard system utilities | Link the explicitly requested basic configuration. |
| `make configure` / `make setup` / `make all` | Python 3.11+ and tooling required by selected integrations | Apply resolved configuration and integrations without running the full catalog installation plan. |
| `make config` / `make plan` | Python 3.11+ | Inspect resolved settings or the installation plan. |
| `make bootstrap` / `bash bootstrap.sh` | Make, Bash, system utilities and download capability as needed | Apply the native baseline and provision only uv and Python. |
| `make install` / `bash bootstrap.sh install` | Bootstrap prerequisites | Ensure the configuration runtime exists, then install the selected tools and apply their configuration and integrations. |

## Default configuration

**SETUP-01 — No implicit software installation.** Default `make` and `make base` MUST install configuration only. They MUST NOT invoke package managers, provision runtimes, download or compile software, run authentication flows, or start services. They MUST work without Python, Node, uv, Cargo, or optional application binaries. A missing dependency MUST NOT silently turn a configuration command into bootstrap.

**SETUP-02 — Native baseline initialization.** Default `make` MUST detect macOS or Linux, initialize a missing machine TOML with `sets = ["macos"]` or `sets = ["linux"]`, and apply that platform's built-in configuration. Unsupported platforms MUST fail before initialization or configuration writes. This first stage MUST work without parsing machine TOML or loading private sets; machine overrides take effect in the resolved configuration and installation stages.

**SETUP-03 — Configuration destination and preservation.** Initialization and resolution MUST agree on the machine file location, in this order:

1. An explicitly supplied `DOTFILES_CONFIG` path.
2. `$XDG_CONFIG_HOME/dotfiles/config.toml` when `XDG_CONFIG_HOME` is supplied.
3. `~/.config/dotfiles/config.toml` otherwise.

Initialization MUST create missing parent directories and MUST preserve existing machine files byte for byte. It MUST NOT replace existing symlinks, including dangling links, or overwrite a file created concurrently. Rerunning default setup MUST preserve local set selections, comments, and individual properties. An existing invalid TOML file MUST NOT prevent applying the built-in baseline; commands that consume that TOML must report its error.

## Resolved configuration

**SETUP-04 — Explicit composition and overrides.** Full resolution MUST apply shared defaults including Git and the native platform, then the default shell and terminal sets, then explicitly selected sets, then individual machine properties. Parent sets apply before their including set; each set applies once; later selections override earlier values. Private sets may replace repository sets of the same name except the shared `base`. Additional tools, work context, and runtime-source choices MUST remain explicit rather than being inferred from the hostname or the presence of another application. Selecting `workstation` provides the broad tool bundle; it MUST NOT be selected implicitly.

**SETUP-05 — Validation before selected effects.** Configuration consumers MUST reject malformed TOML, unknown properties or sets, invalid types or values, dependency cycles, incompatible platform tools, and explicitly disabled required dependencies. Full installation may provision its configuration runtime first, but MUST validate the selected plan before running its optional tool installers or preparation/post-install hooks. A missing explicitly selected machine file MUST be an error for resolution, rather than silently falling back to another file.

**SETUP-06 — Inspection without application.** `make config` and `make plan` MUST inspect the same configuration used by full configuration and installation. They MUST NOT initialize or rewrite machine TOML, install software, or apply integrations. `make -n` and dry runs of basic linking targets MUST work without Python and leave managed configuration and software unchanged. Dry runs of resolved configuration may require its parser runtime, but MUST NOT provision that runtime automatically.

## Explicit software installation

**SETUP-07 — Minimal bootstrap.** Bootstrap MUST work without preinstalled Python and without valid machine TOML. It MUST stop after the native baseline and uv/Python provisioning; it MUST NOT install the selected workstation, language toolchains, editors, AI tools, or work integrations. The resulting runtime MUST be discoverable by subsequent Make commands even if `~/.local/bin` was absent from the caller's original `PATH`.

**SETUP-08 — Selected full installation.** Full installation MUST install only the resolved tool plan and its required dependencies, install shared dependencies once and before their dependents, then apply the selected configuration and integration hooks. Individual disables MUST be honored; disabled tools MUST NOT trigger their own installation or post-install hooks. The command MUST ensure its parser runtime is available so it can be invoked directly or retried independently of minimal bootstrap. A failed tool installation MUST stop the remaining installation phases and return failure.

**SETUP-12 — Prefer user-level installation.** Bootstrap and full installation MUST reuse suitable installed tools. When a versioned recipe has a direct install path, try it before installing a system package. Automatic npm installation MUST use a user-owned prefix. Report when the installer needs `sudo` for system packages or a system setting.

## Convergence and maintenance

**SETUP-09 — Safe reruns and visible failures.** Setup MUST converge when rerun and preserve user-managed configuration outside its managed links and explicitly selected integrations. Disabling a tool MUST NOT implicitly uninstall an existing application. Configuration checklists MUST report failed steps, continue independent configuration steps where possible, and return nonzero when incomplete. Both installation stages MUST use the current checkout without implicitly pulling updates or switching its revision.

**SETUP-10 — Shared definitions.** Configuration and installation MUST derive their selections from the same sets and tool catalog. A checked-in projection that keeps first-stage Make independent of Python MUST be reproducible from those definitions and checked for drift. Tool versions, dependencies, configuration targets, and hooks MUST NOT acquire a separate, conflicting installation plan in the bootstrap path.

**SETUP-11 — Shared runtime minimums.** Applications using Bun, Node, or another externally managed interpreter MUST declare a minimum supported runtime and use the environment's runtime. They MUST NOT install private copies, embed that interpreter in the distributed CLI, or require an exact runtime version. Native application binaries remain valid distribution artifacts. Full installation MUST combine the catalog baseline, installed-project declarations, and selected-project requirements, choose the greatest minimum for each runtime, and retain an installed version that already satisfies it. Unsupported ranges and explicitly disabled required runtimes MUST fail before optional installation. Application revisions and dependency lockfiles remain separate from runtime requirements.

### Project runtime requirements

JavaScript projects declare their Bun or Node minimum in `package.json`, for example `"engines": {"bun": ">=1.4.5"}`. The project installer validates the shared executable before changing its installation. Dotfiles reads those declarations when preparing an explicit installation and records successful installs under `${XDG_CONFIG_HOME:-~/.config}/dotfiles/runtime-requirements.d/<project>.json`. Projects contribute data; they do not rewrite the bootstrap script.

Each drop-in contains an `engines` object with one or more of `bun`, `node`, `go`, or `rust`. Requirements use `>=` followed by a stable numeric version. Exact versions, caret ranges, upper bounds, prereleases, and alternative ranges are rejected because taking the greatest minimum does not resolve those constraints. Numeric comparison means `1.10.0` exceeds `1.9.0`. An optional `source` string can identify the originating manifest.

```json
{
  "engines": {"bun": ">=1.4.5", "node": ">=24.0.0"},
  "source": "/path/to/project/package.json"
}
```

`make plan` reports each resolved runtime minimum and the declarations contributing to it without writing files or fetching source. For a new or updated external project, the preview uses the catalog and any last-installed declaration; `make install` reads the selected source manifests and resolves the final requirements before installing runtimes. Installed-project requirements remain active when a tool selection is disabled, since disabling a tool does not uninstall it; remove its declaration when the project is actually uninstalled. Setting a required runtime itself to `false` is an explicit conflict. The Python-free baseline and generated Make targets do not read these declarations.

## Acceptance workflows

Keep protection in the existing feature detectors, following the repository's [verification policy](verification.md). The observable outcomes below are acceptance criteria, not a substitute for examining the implementation.

| Workflow | Required observations | Existing detector |
|---|---|---|
| Fresh configuration with only system utilities | Default and basic dry runs leave the home untouched. Actual setup creates the detected native TOML and links without Python or software installers. Edited TOML survives a rerun. Unsupported platform targets fail before writing configuration. | [Setup](../scripts/test-setup.py) |
| Compose, inspect, override, and reject a plan | Selected sets and machine overrides produce the expected tools and configuration; Make and bootstrap use the same file. Invalid selection fails before replacing the selected runtime. Generated schema and Make metadata remain consistent with the definitions. | [Configuration](../scripts/test-dotfiles-config.py) |
| Minimal bootstrap followed by explicit installation | Bootstrap succeeds with missing Python and invalid machine TOML, provisions only the runtime and native configuration, and leaves optional tools and work hooks untouched. Subsequent inspection finds the runtime without a shell restart. Explicit installation adds selected tools; a disabled editor skips installation and post-install setup. | [Bootstrap](../scripts/test-bootstrap.py) |

The bootstrap detector simulates package managers, release downloads, and compilation. It verifies orchestration and resulting filesystem state; it does not establish live package availability or upstream compatibility.
