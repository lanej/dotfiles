# Viewrule integration

The UI-review engine is now **Viewrule**, an independent tool intended for
[lanej/viewrule](https://github.com/lanej/viewrule). This repository owns the
installer, version pin, personal preferences, and Claude integration.

**Publication pending:** the first standalone release must exist before the
remote installer or its CI check can succeed. The source archive and local checkout
mode are usable now. Keep the extraction PR in draft until publication and pin validation.

## Install and use

Requires Node 22+, npm, and Python 3 for the dotfiles wrapper/installer.

```sh
cd ~/.files
make ui-review
# make claude links the existing Claude configuration and skills on a new machine.
cd /path/to/app
ui-review init --url http://localhost:3000
# Start the app and configure routes, viewports, and scoped rules in .ui-review/.
ui-review check
```

`make ui-review` verifies the archive checksum from `claude/ui-review/tool.json`,
installs into `~/.local/share/viewrule/releases/`, installs the pinned browser, and
switches `current` only after success. Both CLI names are linked in `~/.local/bin`.
The existing `.ui-review` project files and Claude Stop hook remain compatible.

## Develop the independent tool

```sh
cd ~/src/viewrule
npm ci
npm run browser:install
export VIEWRULE_DEV_DIR="$PWD"
cd /path/to/app
~/.files/bin/ui-review check
```

Export `VIEWRULE_DEV_DIR` before launching Claude so its hook uses the checkout too.
Unset it to return to the pinned install. No symlinking or vendoring the source into
this repository is needed. `VIEWRULE_BROWSER_PATH` selects an existing Chromium
executable when the standard browser cannot be installed.

## Preferences and feedback

The wrapper defaults `VIEWRULE_CONFIG_DIR` to `claude/ui-review` in this checkout.
Explicit `VIEWRULE_CONFIG_DIR` or legacy `UI_REVIEW_GLOBAL_DIR` overrides it.
Personal `preferences.json`, reusable `rules.json`, and global `feedback.jsonl`
remain here. Project selectors, thresholds, feedback, and approved screenshots
remain in each app's `.ui-review/` directory. The version pin is installer metadata,
not a design preference.

`/ui-review` remains the Claude skill. It uses the standalone CLI to capture,
inspect findings, and record the user's feedback. Stop enforcement remains opt-in
per application with `enforceOnStop: true`. A hook is an iteration aid; use the CLI
in application CI for required gates.

## Update, rollback, and remove

Update the version, versioned release URL, and SHA-256 in `tool.json` in one review,
then run `make ui-review`. Never use an unversioned latest URL. Roll back by restoring
an earlier reviewed pin and rerunning the installer. Old version directories are
retained; remove unused ones manually when desired.

Remove the `~/.local/bin/ui-review` and `viewrule` links and
`~/.local/share/viewrule` to uninstall this integration; remove its Claude Stop
hook at the same time. Project rules and references are retained. An explicitly
configured `VIEWRULE_INSTALL_ROOT` replaces the default install location.

## Verification and upstream docs

`make test-ui-review` runs one installation workflow with the real pinned package:
install, launch, and verify an opted-in project blocks without a current review.
It does not rerun the engine's browser regression. For an unpublished local archive:

```sh
VIEWRULE_ARCHIVE=/absolute/path/to/viewrule-0.1.0.tgz make test-ui-review
```

The archive must match the checksum pin. `python3 scripts/install-viewrule.py
--archive /absolute/path/to/viewrule-0.1.0.tgz` installs that same archive locally.

Engine documentation lives in the package under `docs/` and upstream:
[manual](https://github.com/lanej/viewrule/blob/main/docs/ui-review.md),
[architecture](https://github.com/lanej/viewrule/blob/main/docs/architecture.md),
[lifecycle](https://github.com/lanej/viewrule/blob/main/docs/lifecycle.md), and
[density roadmap](https://github.com/lanej/viewrule/blob/main/ROADMAP.md).
These URLs become available after initial publication.
