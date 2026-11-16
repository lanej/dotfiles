# Set up or change a project profile

## Set up or change a profile

Use authored TOML for reviewable project configuration. It requires `schema_version = 1`; top-level stage, kind, authority, adoption, mode, skill_storage, skills, agents, pr_template, detect_languages, and policy_version map to the CLI selections. Nested `[checks.go]` and `[checks.typescript]` tables select enabled/rollout, with projects for TypeScript. `[checks.protobuf]` overrides automatic profile selection with enabled for strict Buf and JSON string field checks. `[checks.python]` selects enabled and paths for an opt-in strict Python profile; no ratchet baseline is introduced. Read subcommand help and the owning setup guide for the full contract. Explicit CLI values override TOML, then saved selections and defaults apply. `--config PATH` selects an alternate file relative to the invocation directory; supply that explicit path again on later commands. Ordinary setup and upgrades never rewrite the authored file.

Use `kind = "service"`, `"library"`, or `"tool"` in TOML, or `--kind KIND`, to select usage-specific obligations. Kind is optional, never inferred, and saved independently of lifecycle stage. Omission retains an installed kind; library kind selects caller documentation guidance.

New profiles install repository-only publication guidance with the core skills. It is selected through `skills` like other packages; curated subsets can omit it. Existing saved selections are retained. Setup installs that guidance into the target repository, never the workstation skill tree, and does not start a service or modify user-level hooks.

Select `authority = "owned" | "shared" | "upstream"` and `adoption = "hold" | "new" | "backfill"` in TOML, or pass `--authority` and `--adoption`. Setup and upgrade require both choices unless already configured or saved; never infer them from hosting or public visibility. Owned projects control their stack, shared projects need project agreement, and upstream contributions follow maintainer conventions. Hold preserves the stack, new applies the catalog to new independent surfaces, and backfill records migration direction but requires explicitly scoped migration work. Explain remains read-only with unset choices; legacy installs remain usable until their next setup/upgrade.

Use the requested stage and visibility; preserve saved selections on an existing installation. New installations default to beta and full generated checks. Research includes proofs of concept. The available stages are research, alpha, beta, and production; lowering a stage relaxes introduced checks and requires reviewing the preview. A stage does not waive repository gates or certify readiness.


New installations default to shadow mode and canonical skill links; existing copied installations retain their storage. Use `--skill-storage linked` for canonical project discovery links or `--skill-storage copied` for a portable package. Tracked linked setups version configuration, while skill links stay locally excluded. Keep the canonical checkout available.

Choose tracked mode to share project policy, or `--mode shadow` to exclude managed files through Git’s local exclusions while leaving shared instructions unchanged. Shadow mode is local Git visibility, not secret storage or a guarantee that other tools cannot see the files. Use `--skills data-pipeline`, `--skills ui-acceptance`, or `--skills ui-review` for optional project pipeline architecture or UI acceptance guidance. These are not selected by language detection; upgrades retain existing selections. The project-only `ui-review` skill supplies Viewrule operation and includes UI acceptance guidance for frontend projects. Use `--skills` for a curated subset, `--agents codex` for Codex discovery only, and `--pr-template none` to omit a template when requested. Check subcommand help for strict/ratchet adoption of existing Go or TypeScript code.

Preview the actual requested arguments before applying them. For example, private research guidance in an existing repository without generated language checks or a PR template:

```sh
source-code setup --repo PATH --stage research --authority upstream --adoption hold --mode shadow --no-go --no-typescript --no-python --no-protobuf --pr-template none --dry-run
```

Review affected paths, conflicts, selected skills, and checks; then apply the same arguments without `--dry-run` within the user’s authorized setup scope. Do not replace existing instructions, customized files, or linked sources to make installation pass. The default conflict policy fails; inspect the reported files before choosing a supported resolution. Setup does not stage, commit, push, or publish repository changes.
