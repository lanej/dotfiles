# Project skill rendering

`source-code` resolves project configuration during setup and writes the resulting commands and policy into installed `SKILL.md` entrypoints. Agents consume those entrypoints during project work. Canonical packages contain the sources used to produce them.

Use the [setup guide](repository-bootstrap.md) to configure a project. This reference inventories the source packages and defines how to maintain their rendered guidance.

## Source selection and assembly

Source selection and assembly are separate choices. A package can use a shared entrypoint or one selected by maturity; its text can then be preserved, rendered, or adapted for its installation location.

| Source selection | Packages | Assembly |
| --- | --- | --- |
| Maturity: `research`, `alpha`, `beta`, or `production` | Go, TypeScript, Python, Protobuf | Render the selected template with resolved project policy. |
| Maturity | Testing, code-comments | Inject shared guidance into the selected entrypoint. |
| Maturity | Rust | Install the selected entrypoint unchanged. |
| Shared | Project policy | Render the selected kind, authority, and adoption into one shared template. |
| Shared | Octo | Adapt the submission-guide path, then render repository automation policy. |
| Shared | Remaining curated skills | Preserve the entrypoint; copied packages adapt local resource paths where required, including Git and pull-request guidance. |

[`MATURITY_SKILLS` and `SKILL_TEMPLATE_BLOCKS`](../bin/source-code) declare these two axes. `SKILL_TEMPLATE_BLOCKS` is the executable inventory of rendered skills and their expected placeholders; `CONFIGURED_SKILLS` derives from it. The [bootstrap detector](../scripts/test-repo-bootstrap.py) checks declared templates across every stage and rejects unregistered placeholders. [`source-code-versions.json`](../ai/skills/source-code-versions.json) owns release versions, while [`project-only.json`](../ai/skills/project-only.json) controls exclusion from global skill synchronization.

Maturity templates live under `ai/skills/.maturity-profiles/<stage>/<skill>/`. Their sibling root packages supply shared references and assets; the root `SKILL.md` explains installation. Shared packages use `ai/skills/<skill>/SKILL.md`. Every installed entrypoint is exposed at `.agents/skills/<skill>/SKILL.md`, with Claude aliases pointing to the same package when selected.

## Rendered-skill inventory

The stage-specific template links below show beta. The same placeholder contract applies to all four stages. The project policy uses a shared template.

| Skill and template | Placeholder | Effective inputs | Inserted content |
| --- | --- | --- | --- |
| [Go](../ai/skills/.maturity-profiles/beta/go/SKILL.md) | `verification` | Stage; generated gate selected or retained; rollout from `.go-quality.json` | [Installed](../ai/skills/go/references/profile-installed.md) or [guidance-only](../ai/skills/go/references/profile-uninstalled.md) verification; [strict](../ai/skills/go/references/rollout-strict.md) or [ratchet](../ai/skills/go/references/rollout-ratchet.md) enforcement when the gate is present. |
| [TypeScript](../ai/skills/.maturity-profiles/beta/typescript/SKILL.md) | `verification` | Stage; generated gate selected or retained; rollout from `.typescript-quality.json` | [Installed](../ai/skills/typescript/references/profile-installed.md) or [guidance-only](../ai/skills/typescript/references/profile-uninstalled.md) verification; [strict](../ai/skills/typescript/references/rollout-strict.md) or [ratchet](../ai/skills/typescript/references/rollout-ratchet.md) enforcement when the gate is present. |
| [Python](../ai/skills/.maturity-profiles/beta/python/SKILL.md) | `verification` | Stage; generated gate selected or retained | [Installed](../ai/skills/python/references/profile-installed.md) strict verification or [guidance-only](../ai/skills/python/references/profile-uninstalled.md) instructions. |
| [Protobuf](../ai/skills/.maturity-profiles/beta/protobuf/SKILL.md) | `verification` | Stage; generated gate selected or retained | [Installed](../ai/skills/protobuf/references/profile-installed.md) verification or [guidance-only](../ai/skills/protobuf/references/profile-uninstalled.md) instructions. |
| [Testing](../ai/skills/.maturity-profiles/beta/testing/SKILL.md) | `shared-guidance` | Stage | [Minimum effective testing](../ai/skills/testing/references/principles.md), including test selection, diagnostics, and verification boundaries. |
| [Code comments](../ai/skills/.maturity-profiles/beta/code-comments/SKILL.md) | `shared-guidance` | Stage | [Shared comment guidance](../ai/skills/code-comments/references/common.md), including usefulness, placement, and format. |
| [Project policy](../ai/skills/source-code-lifecycle/SKILL.md) | `project-policy` | Kind; authority; adoption | Selected kind, authority, and adoption fragments, such as [tool](../ai/skills/source-code-lifecycle/references/kind-tool.md), [owned](../ai/skills/source-code-lifecycle/references/authority-owned.md), and [hold](../ai/skills/source-code-lifecycle/references/adoption-hold.md). |
| [Octo](../ai/skills/octo-manager/SKILL.md) | `automation` | Stage; `octo-manager.toml` merging and notification settings; [notification defaults](../ai/skills/octo-manager/assets/notification-defaults.json) | [Enabled](../ai/skills/octo-manager/references/auto-merge-enabled.md) or [disabled](../ai/skills/octo-manager/references/auto-merge-disabled.md) merging, configured notification follow-up, and [evidence/reconciliation rules](../ai/skills/octo-manager/references/automation.md). |

Language selection alone does not enable a generated gate. A guidance-only entrypoint directs the agent to existing repository checks. When a gate is present, its entrypoint states `python3 scripts/check-source-code.py LANGUAGE`; the [stage command plan](../ai/skills/source-code-lifecycle/references/stages.json) determines the underlying runner mode. Stage and Go/TypeScript rollout are independent choices.

For Octo, `auto_merge = "project_stage"` enables the inherited default in research and alpha, and disables it in beta and production. Literal booleans select the default directly. Per-PR switches, notification states, queued operations, and observed outcomes still require current Octo evidence.

The installer omits inlined profile, rollout, kind, authority, adoption, Octo automation, and shared testing and comment fragments from the resulting package. It also omits the lifecycle tool catalog when adoption is `hold`; `new` and `backfill` retain it for applicable tool-selection tasks. Other technical references remain available for their stated procedures.

## Example: Go at beta with strict enforcement

For an active Go gate with stage `beta` and rollout `strict`, the installer combines the [beta template](../ai/skills/.maturity-profiles/beta/go/SKILL.md), [installed verification fragment](../ai/skills/go/references/profile-installed.md), and [strict enforcement fragment](../ai/skills/go/references/rollout-strict.md).

The source template contains:

```markdown
# go: beta

Protect supported behavior, affected integrations, and compatibility. Use independent expected outcomes and migration checks where relevant.

<!-- source-code:verification -->
```

The installed `.agents/skills/go/SKILL.md` contains these sections, with the runner mechanics between them omitted from this excerpt:

```markdown
## Verification

Run `python3 scripts/check-source-code.py go` for the installed lifecycle gate. The selected stage entrypoint controls required checks; standalone modes describe available tools and do not add another stage’s gates. Preserve stronger repository requirements. Missing tools and failed checks require resolution or a reported limit, never a silent skip.

## Enforcement: strict

All findings from checks required by the selected stage must pass without grandfathered diagnostic allowances. Fix findings at their cause; do not create a baseline to unblock a feature. Preserve the original project gate and merged strict policy. Change rollout only through an explicitly scoped configuration task.
```

The fragment link `(correctness.md)` becomes `(references/correctness.md)` in the entrypoint. The verification command and selected enforcement need no further profile lookup.

## Template contract

Each declared placeholder occupies an exact line of its own:

```markdown
<!-- source-code:verification -->
```

Every expected placeholder must appear exactly once. Missing, unknown, duplicate, or malformed placeholders fail planning before installation writes. Templates have no expressions, conditional syntax, closing tags, or backward-compatibility fallbacks. Selection logic belongs in `configure_skill_packages()` in the [installer](../bin/source-code); Markdown supplies the instructions for the selected case.

Source fragments start relative to their `references/` directory. Inlining moves their headings down one level, such as H1 to H2, and rebases relative Markdown links to the entrypoint. External URLs and anchor-only links retain their targets. Authored Octo notification instructions are inserted as literal text, without evaluating template expressions.

Use fragments for selected commands and obligations that the entrypoint must state. Keep detailed adoption mechanics, tool provisioning, examples, and conditional procedures in supporting references, with a clear instruction about when to read them. Moving always-required instructions to a reference only adds another loading step.

## Storage and refresh

| Installed content | Linked storage | Copied storage | Refresh |
| --- | --- | --- | --- |
| Rendered entrypoints | Managed regular files | Managed regular files | Run setup or upgrade after source or configuration changes. |
| Shared entrypoints and resources that need no adaptation | Canonical directory or file links | Portable regular files | Links follow source edits immediately; copies refresh through setup or upgrade. |
| Path-adapted resources and generated checks | Managed regular files | Managed regular files | Run setup or upgrade. |
| Skill release registry | Canonical link | Copied registry matching installed pins | Live versions describe available source; they do not regenerate rendered files. |

Changing the stage requires setup or upgrade to select a different entrypoint. Authored settings and customized installed files retain normal conflict protection; preview updates before applying them. Do not edit generated instructions or manifest fingerprints to claim a refreshed installation.

## Inspect the right evidence

| Question | Inspect |
| --- | --- |
| Which source packages and placeholders exist? | The inventory above, `SKILL_TEMPLATE_BLOCKS`, and the canonical template files. |
| Which project policy and skill selections would apply, and why? | `source-code explain --repo PATH`, or `--json` for structured desired/recorded choices and origins. |
| What would this installation change? | `source-code setup --repo PATH --authority AUTHORITY --adoption ADOPTION --dry-run`, or `source-code upgrade --repo PATH --dry-run`. |
| Are installed files, links, and recorded metadata structurally consistent? | `source-code validate --repo PATH --strict`. |
| What instructions does the agent receive? | The installed `.agents/skills/<skill>/SKILL.md` and its explicitly referenced procedures. |

`explain` reports policy choices; it does not render an instruction preview or prove integrity. Validation checks installed structure and recorded state, and does not prove that an agent follows the instructions or that every compiled section reflects a later canonical edit. Read the installed entrypoint after applying an update. See the [inspection contract](repository-bootstrap.md#policy-inspection-and-agent-discovery) for command boundaries.

## Maintain the contract

1. Choose whether the change is shared guidance, a stage expectation, or a resolved project choice. Edit the corresponding reference, stage entrypoint, or renderer selection logic.
2. For a new rendered skill or placeholder, update `SKILL_TEMPLATE_BLOCKS`, its template sources, and this inventory together. Keep expected placeholders explicit and configuration decisions in Python.
3. Run `make test-repo-bootstrap`. Its existing workflow checks source declarations, all stages, both storage modes, selected commands and policies, and failure before writes for invalid sources. Inspect representative installed output when changing instructional meaning.
4. Follow the [skill-maintenance checks](skill-maintenance.md) for source instruction edits. Preview setup or upgrade against the intended project, apply the authorized update, and validate the installed package.

To locate the current template markers, include the hidden and ignored source directories:

```sh
rg --hidden --no-ignore --glob SKILL.md -n '^<!-- source-code:' ai/skills
```

Keep release versions, policy version, lifecycle stage, installation fingerprints, and template declarations separate. Each describes a different part of the installation contract.
