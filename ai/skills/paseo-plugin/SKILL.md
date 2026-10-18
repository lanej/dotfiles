---
name: paseo-plugin
description: Build and manage trusted local Paseo plugins. Use when the user asks to create, edit, install, reload, enable, disable, remove, or troubleshoot a Paseo plugin; add lifecycle hooks; transform agent configuration, environment, MCP servers, or workspace creation; automate permissions or turn follow-ups; add a screen, sidebar header or footer item, or workspace panel; add Command Center items or slash commands; add composer pills or attachment sources; transform, render, or append agent timeline items; contribute a theme; use Paseo from plugin code; or add plugin RPCs.
---

# Paseo plugins

Build or manage the requested plugin directly. Use the current public docs to catch contract changes, but keep working from this skill if the network is unavailable.

**User's request:** $ARGUMENTS

## Check current documentation

Fetch [https://paseo.sh/llms.txt](https://paseo.sh/llms.txt) first. Select and fetch the current plugin Markdown pages from that index before changing a plugin:

- [Plugin quickstart](https://paseo.sh/docs/plugins.md) ([browser page](https://paseo.sh/docs/plugins))
- [Publishing](https://paseo.sh/docs/plugins/publishing.md): npm package contents, dependencies, Git preparation, and private registries.
- [Plugin reference](https://paseo.sh/docs/plugins/reference.md) ([browser page](https://paseo.sh/docs/plugins/reference))

Use the deployed docs when they disagree with this skill. Do not send the user away to read them instead of completing the work.

In the Paseo repository, use `public-docs/plugins/reference.md` for the checkout's API, including
unreleased changes. Use `docs/plugins.md` for maintainer guidance. Complete contracts belong in the
public docs; this skill indexes the references and examples.

## What a plugin can contribute

When selecting a contribution or lifecycle hook, read [the contribution catalogue](references/contributions.md) for registrations, use cases, contracts, and official examples. Then read the applicable guide below.

## Create the project

Before initializing a plugin or changing its manifest or runtime entries, read [the project setup guide](references/project-setup.md) for version requirements, runtime boundaries, entry functions, and cleanup.

## Workspace panels, screens, and mobile UI

Before adding a panel, screen, or sidebar item, read [the surface examples and mobile requirements](references/surfaces.md). Apply its selectors, theme colors, compact layout, and SDK import boundaries.

## Choose the correct API

Before calling Paseo or adding daemon behavior, read [the SDK, RPC, and logging guide](references/sdk-and-rpc.md). Use the existing SDK for normal Paseo operations and RPC for plugin-specific behavior.

## Composer contributions

Before adding attachment sources, slash commands, or composer pills, read [the composer examples](references/composer.md) for registration, context, host ownership, and teardown.

## Timeline contributions

Before transforming, rendering, or appending timeline items, read [the timeline examples](references/timeline.md) for streaming identity, schema checks, payload limits, and persistence.

## Themes

Before contributing a theme, read [the theme example](references/themes.md) for palette fields and client compatibility.

## Hosts and trust

Plugins are installed per daemon and are trusted, unsandboxed code. Backend code can access files, processes, credentials, and network services on the daemon machine. Client contributions run inside the Paseo app. Do not install a plugin the user has not authorized or source code you have not inspected.

### Check the global switch before installing

Identify the target daemon and inspect its root `pluginsEnabled` value in `config.json`. For the local daemon, `paseo daemon status --json` reports its `home`; the file is `<home>/config.json`. Treat a missing field as `false`. Do not infer the global value from a plugin's `disabled` status, because an individual plugin can also be disabled.

If `pluginsEnabled` is already `true`, continue without asking the user to enable it.

If it is false or absent, stop and ask the user for explicit permission before editing or enabling anything. Include this warning in the request:

> Plugins are trusted, unsandboxed code. Backend plugin code can access your daemon machine, including files, processes, credentials, and network services. Client plugin code runs inside the Paseo app. May I enable plugins on this daemon?

Do not continue unless the user agrees. After permission:

1. Preserve the rest of `config.json` and set the root `pluginsEnabled` field to `true`.
2. Run `paseo reload --json` against that daemon.
3. Require `pluginsEnabled` in `appliedPaths`, or accept an empty `appliedPaths` only after re-reading the file and confirming the live plugin catalog is enabled.
4. Run `paseo plugin ls` and verify the intended plugin reaches `running` after installation.

If the user asks to disable the global switch, set `pluginsEnabled` to `false`, run `paseo reload --json`, and verify configured plugins report `disabled`.

Do not edit a local config when the target is a remote daemon. Perform the edit on the daemon machine, or ask the user to use **Settings → Plugins → Enable plugins**. `paseo reload --host <url>` reloads the remote daemon's own file but does not edit it.

When the same screen or sidebar item exists on several connected hosts, Paseo shows it once. The screen header has a host picker; a sidebar item uses the host of the screen on display, else the host last picked in one of the plugin's screens. The selected host owns the bundle, SDK calls, RPCs, and query cache. An offline selected host does not fall through to another host. Attachment sources stay scoped to the composer's host.

## Publishing a listing

Write `OVERVIEW.md` beside `paseo-plugin.json` for the plugin page inside Paseo.
It helps someone decide whether to install your plugin; the install command is already at
the top of that page. A README assumes a GitHub audience and carries installation
instructions, technical details, and badges. Long, AI-generated READMEs make people read
past that material to understand what a plugin does.

`OVERVIEW.md` is required to list your plugin in the registry. Commit it beside
`paseo-plugin.json` in the source repository at the pinned commit. The registry resolves it
relative to the manifest, under `pluginPath` for monorepos. Include it in the published npm
package too; the scaffold's `files` list includes it. Replace the scaffold's guidance comment
with useful facts before publishing.

The repository overview takes precedence over a registry import stopgap. Online validation
fails when the pinned commit has no `OVERVIEW.md`, except for unchanged imported records
that already carry `plugins/<owner>/<slug>.md` in the registry repository. Every version bump
requires a repository overview and removes the stopgap in the same PR. A bump without the
repository overview fails validation. README files do not supply the overview.

Author overviews and registry stopgaps follow the same content contract, in this order.
Choose headings only when they help; length follows complexity. A theme needs one paragraph.

1. Explain what the plugin is and does in plain terms first.
2. Explain how it works only when that is not obvious.
3. Explain setup when needed: settings, accounts, tokens, providers, external tools, or other
   plugins. Include applicable daemon version and operating system requirements. Setup
   guidance is allowed; installation instructions are not.
4. Explain capabilities and settings worth understanding, what each option does, what the
   plugin reads or sends and where, permissions, and known limits.

Use sentence case and plain factual language, with no em dashes. Omit installation commands,
badges, changelog, contributing or license sections, marketing, and unsupported claims.
Avoid implementation filler such as empty cleanup functions, catalogs of theme-token fields,
or lists of absent features. Keep only what helps someone choose the plugin.

If your plugin is an unchanged imported record, you can propose an author-written overview
to replace the registry stopgap. Do not add import credit to your own `OVERVIEW.md`.

See [Your listing page](https://paseo.sh/docs/plugins/publishing.md#your-listing-page).

## Typecheck and manage

When editing a plugin, typecheck its source before install or reload:

```bash
npm run typecheck
paseo plugin install /absolute/path/to/plugin
paseo plugin install /absolute/path/to/plugin --id another-runtime-id
paseo plugin install npm:@acme/paseo-review
paseo plugin install npm:@acme/paseo-review@1.2.0
paseo plugin install github:owner/repository
paseo plugin install github:owner/repository --ref main
paseo plugin update my-plugin
paseo plugin ls
paseo plugin reload my-plugin
paseo plugin logs my-plugin
paseo plugin disable my-plugin
paseo plugin enable my-plugin
paseo plugin remove my-plugin
```

For npm, ensure npm is on the daemon's `PATH`; use that host's registry configuration and credentials. Install selectors choose
content once; they do not pin updates. `install` and `add` are aliases. Follow the
[publishing guide](https://paseo.sh/docs/plugins/publishing.md) for Paseo's package contents and
preparation requirements; standard npm publishing commands apply.

Use `--host <url>` when managing a daemon other than the CLI default. A Git source that must install or generate something declares `build` in `paseo-plugin.json` as a list of argv arrays; Paseo runs them without a shell on install and update and keeps the old version if one fails. Plugin source edits require `paseo plugin reload`; config changes to the global switch require `paseo reload`. A failed plugin reload stays failed; inspect `paseo plugin ls` for the load error and `paseo plugin logs <id>` for subprocess output, fix the source, typecheck, and reload again. `remove` keeps local source directories and deletes managed Git/npm installations.

Do not restart the daemon to load source changes. Restarting it can kill the agent performing the work.

For an old mixed entry, follow the standalone [runtime-entry migration guide](https://paseo.sh/docs/plugins/migration) mechanically.

## Verify the outcome

After a change:

1. Run `npm run typecheck`.
2. Install or reload the exact runtime ID.
3. Run `paseo plugin ls` and require `running` with no error.
4. Confirm the contribution on the intended host. Open the Command Center with **⌘K** (macOS) or **Ctrl+K** (Windows/Linux). Type `/` in the composer for slash commands. For timeline work, run an agent turn that produces the source item and watch it while it streams, not only after it completes. For UI work, check a wide desktop window and a compact/mobile client, and switch theme to confirm text still uses `foreground` / `foregroundMuted`.
5. Exercise the changed action or RPC, including its error state.

Common failures:

- Missing sidebar item: wrong host, plugin not `running`, the item is hidden in Settings > Sidebar, or its component throws (an invalid Lucide icon name throws).
- Unavailable client module: client bundles can use only the host-provided modules in the linked surface guide.
- RPC rejection: input or output failed its Zod schema, or the handler threw. Inspect `paseo plugin logs <id>` for handler output.
- Plugin exits or reload fails: inspect `paseo plugin ls` for status and `paseo plugin logs <id>` for initialization, cleanup, or crash output.
- Stale UI: source was edited without `paseo plugin reload <id>`.
- Timeline item shows "Plugin timeline item unavailable": no renderer registered for that `kind` and `version`, the renderer schema rejected `data`, or the plugin is not running on that host.
- Transformer has no effect: `query.itemType` does not match the source type, the transform returned `undefined`, or it threw and was skipped; check the app console for `[Plugins] Timeline transformer failed`.
- Slash command not offered: name collides with a built-in or another plugin, the context is `agent` on a draft, or the composer has attachments.
- Append rejected: the caller is not a plugin session, `data` exceeds 64 KiB, or the host predates `features.pluginTimelineItems`.
