# Viewrule integration

The UI-review engine is now **Viewrule**, an independent tool at
[lanej/viewrule](https://github.com/lanej/viewrule). This repository owns the
installer, version pin, personal preferences, and Claude integration.

**Current pin:** [Viewrule v0.8.0](https://github.com/lanej/viewrule/releases/tag/v0.8.0).
This experimental release retires Stop enforcement, adds explicit verification and
optional Git gates, and accepts the application's runtime URL for each review.
Source-only checks use `ui-review lint --target src`; rendered requirements still
use `check`, and source-only results cannot satisfy rendered-evidence verification.
The installer verifies the published archive against the checksum in `tool.json`.

## Install and use

Requires Node 22.18+, npm, and Python 3 for the dotfiles wrapper/installer.

```sh
cd ~/.files
make ui-review
# make claude links the existing Claude configuration and skills on a new machine.
cd /path/to/app
ui-review init
# Start the app and configure routes, viewports, and scoped rules in .ui-review/.
# Set APP_URL to the actual URL printed by this checkout's application server.
ui-review check --url "$APP_URL"
ui-review verify
```

`make ui-review` verifies the archive checksum from `claude/ui-review/tool.json`,
installs into `~/.local/share/viewrule/releases/`, installs the pinned browser, and
switches `current` only after success. Both CLI names are linked in `~/.local/bin`.
The existing `.ui-review` project files remain compatible; legacy `hook` calls are
harmless even without an installed engine. Review and verification find the nearest
`.ui-review/config.json` without crossing a `.git`
file or directory. Commit the setup files so Git carries them into new worktrees;
keep each worktree's `.ui-review` directory separate so review evidence stays local.
See the upstream [worktree setup guide](https://github.com/lanej/viewrule/blob/main/docs/worktrees.md).

## Develop the independent tool

```sh
cd ~/src/viewrule
npm ci
npm run browser:install
export VIEWRULE_DEV_DIR="$PWD"
cd /path/to/app
~/.files/bin/ui-review check --url "$APP_URL"
```

Export `VIEWRULE_DEV_DIR` before launching Claude so its CLI uses the checkout too.
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
inspect findings, and record the user's feedback. `enforceOnStop` is accepted but
ignored. Optional `ui-review pre-commit --project apps/web` and `pre-push` gates
verify existing evidence only for changed UI inputs in the selected application.
They do not capture, stage, stash, or install hooks. Use the CLI in application CI
for required gates; see upstream [Git integration](https://github.com/lanej/viewrule/blob/main/docs/git-gates.md).

## Update, rollback, and remove

Update the version, versioned release URL, and SHA-256 in `tool.json` in one review,
then run `make ui-review`. Never use an unversioned latest URL. Roll back by restoring
an earlier reviewed pin and rerunning the installer. Old version directories are
retained; remove unused ones manually when desired.

For the 0.8.0 migration, this repository removes its Viewrule Stop registration and
makes old wrapper calls return an empty decision. Run `/viewrule:setup` after
updating the plugin to migrate recognized Viewrule handlers in other user/project
settings, then restart existing Claude sessions. Preserve unrelated hooks and
review any custom handlers reported by setup. Rerun `check` after upgrading because
the engine change invalidates previous evidence.

Remove the `~/.local/bin/ui-review` and `viewrule` links and
`~/.local/share/viewrule` to uninstall this integration; remove its Claude Stop
hook at the same time. Project rules and references are retained. An explicitly
configured `VIEWRULE_INSTALL_ROOT` replaces the default install location.

## Verification and upstream docs

`make test-ui-review` runs one installation workflow with the real pinned package:
install, launch, commit project setup, and explicitly verify missing evidence from
a nested worktree directory. It checks harmless legacy Stop calls and Git gates
that skip unrelated changes but reject UI changes without a current review.
An unconfigured worktree must not inherit its parent checkout's configuration.
It does not rerun the engine's browser regression. For an unpublished local archive:

```sh
VIEWRULE_ARCHIVE=/absolute/path/to/viewrule-0.8.0.tgz make test-ui-review
```

The archive must match the checksum pin. `python3 scripts/install-viewrule.py
--archive /absolute/path/to/viewrule-0.8.0.tgz` installs that same archive locally.

Engine documentation lives in the package under `docs/` and upstream:
[manual](https://github.com/lanej/viewrule/blob/main/docs/ui-review.md),
[architecture](https://github.com/lanej/viewrule/blob/main/docs/architecture.md),
[lifecycle](https://github.com/lanej/viewrule/blob/main/docs/lifecycle.md), and
[density roadmap](https://github.com/lanej/viewrule/blob/main/ROADMAP.md).
