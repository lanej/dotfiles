---
name: source-code
description: Use when installing, inspecting, validating, or upgrading project engineering profiles with the source-code CLI, choosing tracked or shadow setup, or changing lifecycle stage and language checks. Excludes ordinary coding work under an existing project policy.
---

# Source-code project setup

Manage the `source-code` CLI and its project installations. This workstation skill supplies tool usage, not engineering policy: it does not select Builder, testing, comments, or a lifecycle stage for ordinary coding tasks. Follow the target repository’s instructions and its explicitly installed project skills.

## Inspect the target

Resolve the intended checkout and inspect existing repository instructions, `.source-code.json`, and `AGENTS.override.md` when present. Reuse an assigned worktree; setup operates on that checkout and does not allocate worktrees. Existing policy records the installed lifecycle stage, skill pins, check profiles, and detection evidence. Read authored `source-code.toml` at the target Git root when present; it expresses desired policy separately from generated state.

Use `source-code --help` and the chosen subcommand’s `--help` for the installed version’s supported options. If the command is missing, the dotfiles workstation set supplies it; `make source-code-config` from the owning dotfiles checkout links it explicitly. Do not apply unrelated workstation configuration or assume a newer release is installed.

Run `source-code detect --repo PATH --json` to inspect language evidence without changing files. Detection selects guidance for Go, TypeScript, JavaScript, Python, and Rust. Generated check profiles are a separate choice: root Go modules enable Go setup by default, while TypeScript checks require `--typescript`. For a new guidance-only install, use `--no-go --no-typescript`; these flags do not uninstall existing profiles. `--no-detect-languages` saves a detection opt-out.

## Set up or change a profile

Use authored TOML for reviewable project configuration. It requires `schema_version = 1`; top-level stage, mode, skills, agents, pr_template, detect_languages, and policy_version map to the CLI selections. Nested `[checks.go]` and `[checks.typescript]` tables select enabled/rollout, with projects for TypeScript. Read subcommand help and the owning setup guide for the full contract. Explicit CLI values override TOML, then saved selections and defaults apply. `--config PATH` selects an alternate file relative to the invocation directory; supply that explicit path again on later commands. Ordinary setup and upgrades never rewrite the authored file.

Use the requested stage and visibility; preserve saved selections on an existing installation. New installations default to beta and full generated checks. The available stages are research, alpha, beta, and production; lowering a stage relaxes introduced checks and requires reviewing the preview. A stage does not waive repository gates or certify readiness.

Choose tracked mode to share project policy, or `--mode shadow` to exclude managed files through Git’s local exclusions while leaving shared instructions unchanged. Shadow mode is local Git visibility, not secret storage or a guarantee that other tools cannot see the files. Use `--skills` for a curated subset, `--agents codex` for Codex discovery only, and `--pr-template none` to omit a template when requested. Check subcommand help for strict/ratchet adoption of existing Go or TypeScript code.

Preview the actual requested arguments before applying them. For example, private research guidance in an existing repository without generated language checks or a PR template:

```sh
source-code setup --repo PATH --stage research --mode shadow --no-go --no-typescript --pr-template none --dry-run
```

Review affected paths, conflicts, selected skills, and checks; then apply the same arguments without `--dry-run` within the user’s authorized setup scope. Do not replace existing instructions, customized files, or linked sources to make installation pass. The default conflict policy fails; inspect the reported files before choosing a supported resolution. Setup does not stage, commit, push, or publish repository changes.

## Validate and upgrade

Run `source-code validate --repo PATH` to check authored TOML, installed package structure, links, policy metadata, and version pins without running project code. It reports configuration-only validation when no installation exists, and warnings for desired/installed drift; `--strict` fails on those warnings. `--strict` also fails on advisory/customization warnings; `--skills-dir PATH` checks a skill package or tree without requiring an installation. Structural validity does not establish engineering quality or passing application checks.

Use `source-code upgrade --repo PATH --dry-run` to preview updates from the installed command’s source checkout, retaining saved selections. It does not fetch releases automatically. Review policy and skill version changes separately from lifecycle stage changes, then apply the upgrade within the requested scope and validate again. Preserve local customizations; report conflicts, unsupported versions, or partial installations rather than claiming a complete upgrade. Do not hand-edit pins or generated summaries to bypass checks.

Report the target checkout, selected stage and visibility, guidance versus installed check profiles, validation results, and any unresolved conflict. Keep project test results separate from installer validation.
