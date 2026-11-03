# Configuration and software installation requirements

Default setup must make the checkout useful for configuration before development runtimes exist. Software installation is a separate, explicit operation. These requirements govern the native OS baseline, machine TOML, composed tool sets, bootstrap, and full installation on macOS and Linux.

The requirements define intended behavior; the implementation and tests must remain consistent with them. See [issue #128](https://github.com/lanej/dotfiles/issues/128) for the regression that motivated this separation and the [README](../README.md#installation) for usage instructions. **MUST** and **MUST NOT** identify required behavior. Requirement IDs remain stable as implementation details change.

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

**SETUP-04 — Explicit composition and overrides.** Full resolution MUST apply shared defaults and the native platform, then explicitly selected sets, then individual machine properties. Parent sets apply before their including set; each set applies once; later selections override earlier values. Private sets may replace repository sets of the same name except the shared `base`. Additional tools, work context, and runtime-source choices MUST remain explicit rather than being inferred from the hostname or the presence of another application. Selecting `workstation` provides the broad tool bundle; it MUST NOT be selected implicitly.

**SETUP-05 — Validation before selected effects.** Configuration consumers MUST reject malformed TOML, unknown properties or sets, invalid types or values, dependency cycles, incompatible platform tools, and explicitly disabled required dependencies. Full installation may provision its configuration runtime first, but MUST validate the selected plan before running its optional tool installers or preparation/post-install hooks. A missing explicitly selected machine file MUST be an error for resolution, rather than silently falling back to another file.

**SETUP-06 — Inspection without application.** `make config` and `make plan` MUST inspect the same configuration used by full configuration and installation. They MUST NOT initialize or rewrite machine TOML, install software, or apply integrations. `make -n` and dry runs of basic linking targets MUST work without Python and leave managed configuration and software unchanged. Dry runs of resolved configuration may require its parser runtime, but MUST NOT provision that runtime automatically.

## Explicit software installation

**SETUP-07 — Minimal bootstrap.** Bootstrap MUST work without preinstalled Python and without valid machine TOML. It MUST stop after the native baseline and uv/Python provisioning; it MUST NOT install the selected workstation, language toolchains, editors, AI tools, or work integrations. The resulting runtime MUST be discoverable by subsequent Make commands even if `~/.local/bin` was absent from the caller's original `PATH`.

**SETUP-08 — Selected full installation.** Full installation MUST install only the resolved tool plan and its required dependencies, install shared dependencies once and before their dependents, then apply the selected configuration and integration hooks. Individual disables MUST be honored; disabled tools MUST NOT trigger their own installation or post-install hooks. The command MUST ensure its parser runtime is available so it can be invoked directly or retried independently of minimal bootstrap. A failed tool installation MUST stop the remaining installation phases and return failure.

## Convergence and maintenance

**SETUP-09 — Safe reruns and visible failures.** Setup MUST converge when rerun and preserve user-managed configuration outside its managed links and explicitly selected integrations. Disabling a tool MUST NOT implicitly uninstall an existing application. Configuration checklists MUST report failed steps, continue independent configuration steps where possible, and return nonzero when incomplete. Both installation stages MUST use the current checkout without implicitly pulling updates or switching its revision.

**SETUP-10 — Shared definitions.** Configuration and installation MUST derive their selections from the same sets and tool catalog. A checked-in projection that keeps first-stage Make independent of Python MUST be reproducible from those definitions and checked for drift. Tool versions, dependencies, configuration targets, and hooks MUST NOT acquire a separate, conflicting installation plan in the bootstrap path.

## Acceptance workflows

Keep protection in the existing feature detectors, following the repository's [verification policy](verification.md). The observable outcomes below are acceptance criteria, not a substitute for examining the implementation.

| Workflow | Required observations | Existing detector |
|---|---|---|
| Fresh configuration with only system utilities | Default and basic dry runs leave the home untouched. Actual setup creates the detected native TOML and links without Python or software installers. Edited TOML survives a rerun. Unsupported platform targets fail before writing configuration. | [Setup](../scripts/test-setup.py) |
| Compose, inspect, override, and reject a plan | Selected sets and machine overrides produce the expected tools and configuration; Make and bootstrap use the same file. Invalid selection fails before replacing the selected runtime. Generated schema and Make metadata remain consistent with the definitions. | [Configuration](../scripts/test-dotfiles-config.py) |
| Minimal bootstrap followed by explicit installation | Bootstrap succeeds with missing Python and invalid machine TOML, provisions only the runtime and native configuration, and leaves optional tools and work hooks untouched. Subsequent inspection finds the runtime without a shell restart. Explicit installation adds selected tools; a disabled editor skips installation and post-install setup. | [Bootstrap](../scripts/test-bootstrap.py) |

The bootstrap detector simulates package managers, release downloads, and compilation. It verifies orchestration and resulting filesystem state; it does not establish live package availability or upstream compatibility.
