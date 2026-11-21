# Source-code setup

Use `source-code setup` to bring the shared Builder, architecture, and pull-request guidance into a new or existing Git repository. New installations use linked canonical `ai/skills/` sources, with configuration-dependent packages assembled for the project. Canonical links follow source edits; setup or upgrade refreshes generated and adapted files. Use `--skill-storage copied` for portable, independently pinned packages instead. It preserves existing shared instructions and installs a project override that routes to the selected policy. It does not install software, modify global agent settings, stage files, or publish changes.

The command needs Python 3.11+ and Git 2.31+ on macOS or Linux. Run `~/.files/bin/source-code setup` directly, or use `source-code setup` after `make source-code-config` has linked the commands into `~/.local/bin`.

`repo-bootstrap` remains a compatibility alias for `source-code setup` and also requires `--authority` and `--adoption` on every invocation. Existing `.agents/repo-bootstrap.json` manifests, exclusion markers, and backup paths retain their names so either command can safely update an existing installation.

## Bootstrap a new repository

```sh
~/.files/bin/source-code setup --repo ~/src/new-project --authority owned --adoption new --init --dry-run
~/.files/bin/source-code setup --repo ~/src/new-project --authority owned --adoption new --init
```

`--init` creates the directory and initializes Git only if the target is not already a working tree. It refuses a nested initialization inside another repository. Without `--init`, the target must be an existing Git working tree; a subdirectory resolves to that working tree's root.

New installations default to **shadow mode**: configuration, generated checks, discovery links, and installation metadata stay local through Git’s `info/exclude`. Linked installations create `source-code.toml` when no authored configuration exists; existing configuration is never rewritten or untracked. Clones inherit no shadow-installed files; run `source-code setup` locally in each checkout. Existing installations retain their saved visibility. Choose `--mode tracked` explicitly to share project configuration and generated checks. Skill links remain local even in tracked mode; use `--mode tracked --skill-storage copied` to share portable pinned packages and their upgrade metadata.

## Retrofit an existing repository

```sh
~/.files/bin/source-code setup --repo ~/src/existing-project --authority shared --adoption hold --mode local --dry-run
~/.files/bin/source-code setup --repo ~/src/existing-project --authority shared --adoption hold --mode local
```

**Local mode** puts precise file exclusions in a marked block of Git's `info/exclude`; it leaves `.gitignore` unchanged. Installed skills remain usable on this machine, without appearing in normal `git status` or `git add .`. Existing tracked files cannot be hidden this way, so local mode refuses to manage paths already in the index. Higher-priority `.gitignore` negations that defeat an exclusion are reported before installation. Exclusion is not encryption or access control, and `git add -f` can still add these files.

`--mode shadow` is an alias for local mode. The manifest records `local`, so subsequent installs retain the same exclusions without needing the flag again. Skill storage is independent of visibility: linked skills are always local, while shadow mode also hides project configuration and generated checks. Canonical sources remain versioned in dotfiles. The manifest retains file fingerprints for safe updates and detects local modifications.

Linked worktrees are supported. Git shares `info/exclude` between worktrees: the same exact paths are excluded in sibling worktrees too. The installer does not untrack anything or change Git configuration. Worktrees requiring different tracking policies should not mix local and tracked installations at the same paths.

Existing `AGENTS.md`, `CLAUDE.md`, `.gitignore`, unrelated skills, and project PR templates are retained. The generated `AGENTS.override.md` is a small router: it directs the agent to read the authored `AGENTS.md` first, when present, then the generated `.agents/source-code.md`. That policy renders the resolved configuration: lifecycle stage, project kind, selected skills and resolved versions, and selected language gates. Change authored configuration and rerun setup or upgrade to regenerate it; validation checks both the router and generated policy against installed state. Codex loads the override instead of the same-directory `AGENTS.md`; this first-read instruction preserves the shared context. Claude installations add `.claude/rules/source-code.md` to route to the same override. Existing overrides and rules retain normal conflict protection. Start a new session or reload the client's skill catalog after installation.

## Installed content

New default profiles include the project-only `pull-request` skill, which owns writing and selects the applicable publisher. Choose `--skills octo-manager` explicitly for repository-local Octo initialization and validation guidance. Curated selections and upgrades preserve saved choices. Setup does not start Octo or install workstation hooks.

| Path | Purpose |
| --- | --- |
| `.agents/skills/builder/` | Existing Builder skill, architecture/construction references, and runnable examples |
| `.agents/skills/architecture/` | Architecture design/review entrypoint using Builder's canonical standard |
| `.agents/skills/git/` | Git workflow and portable PR references |
| `.agents/skills/octo-manager/` | Optional repository-only Octo integration |
| `.agents/skills/pull-request/` | PR drafting entrypoint, shared/GitHub writer instructions, and their writing references |
| `.agents/skills/testing/` | Stage-specific verification and retained-behavior guidance |
| `.agents/skills/source-code-lifecycle/` | Versioned lifecycle contract and command plans |
| `.source-code.json` | Schema version, policy version, stage, and installed languages |
| `AGENTS.override.md` | Generated router to authored project instructions and generated policy |
| `.agents/source-code.md` | Generated lifecycle, kind, pinned skills, and language gate instructions |
| `.agents/source-code-versions.json` | Live canonical registry link, or copied registry matching portable pins |
| `.claude/rules/source-code.md` | Claude's project-local route to the generated guidance, when selected |
| `scripts/check-source-code.py` | Selected lifecycle gate, shared by local execution and generated CI |
| `.source-code-stages.json` | Tracked command plan for linked installations; generated gates run without skill links |
| `.claude/skills/<name>` | Relative links to the same skill packages for Claude Code |
| `.agents/repo-bootstrap.json` | Local link ownership/source and file fingerprints; tracked for copied installations |
| `.github/pull_request_template.md` | GitHub template, the default in tracked mode |
| `.agents/templates/pull_request_template.md` | Local drafting template, the default in local mode |

Codex uses `.agents/skills`. Claude Code uses the individual `.claude/skills` links; existing directories and unrelated entries are preserved. Pass `--agents codex` to omit new Claude links. Other agents can read these Markdown packages explicitly, but the installer does not claim to configure their native discovery or tool permissions.

The architecture skill automatically includes Builder because it shares the standard. Separately delegated PR writers retain the draft-only boundary: installation does not authorize creating, updating, or merging a PR. It respects the target repository's required title and template fields.

Choose a subset or template independently:

```sh
# Architecture includes its Builder dependency; omit new Claude aliases.
source-code setup --repo ~/src/app --authority owned --adoption new --skills architecture --agents codex --pr-template none

# Keep an existing team PR template while sharing the skills.
source-code setup --repo ~/src/app --authority owned --adoption new --mode tracked --pr-template none

# Keep a private drafting template alongside an existing GitHub template.
source-code setup --repo ~/src/app --authority owned --adoption new --mode tracked --pr-template local
```

`--skills` accepts the names listed by `source-code setup --help`, comma-separated. The core includes Builder, architecture, data/interface planning, Git/PR workflow, CLI construction, testing, lifecycle, and shared comments. Language guidance covers Go, TypeScript, JavaScript, Python, Rust, and Protobuf; `gh-pr-stack`, `github-actions`, `just`, `data-pipeline`, `ui-acceptance`, and `ui-review` are available explicitly. These are curated project skills, selected independently of workstation skills. Language detection selects matching guidance; root Go modules retain their existing automatic check-profile behavior.

## Current-stage project guidance

Source-code selects separate entrypoints for testing, lifecycle, comments, Go, Rust, TypeScript, Python, and Protobuf at the configured maturity. Linked profiles reach the selected entrypoint under `ai/skills/.maturity-profiles/` through directory or individual file links; copied profiles materialize only the selected entrypoint, shared references, and required tool assets. Neither installed form exposes other-stage entrypoints as project skill guidance. Shared architectural rules and tool mechanics remain common; the full lifecycle comparison is an administration reference for comparing or changing maturity. Changing `--stage` and applying setup or upgrade switches the entrypoint; a dry run previews it first. Shared principles cover minimum effective testing, useful CLI failure diagnostics, and verification boundaries without prescribing another maturity's coverage.

Source-code setup materializes configuration-dependent guidance for project kind, authority, tool adoption, installed language checks, Go/TypeScript rollout, and Octo merging and notification instructions. Agents receive the selected policy and commands without reading configuration or choosing among variants. Unselected policy fragments are omitted. Linked installations assemble configured packages locally and link shared canonical files; copied installations contain portable files. Configuration-independent packages retain their existing shared links. Setup or upgrade refreshes selected guidance after configuration changes, including authored Octo settings, while preserving those settings. Current per-PR overrides and notification states remain runtime evidence; they do not require reinterpreting repository configuration. Comment depth uses the selected lifecycle entrypoint, with the library caller perspective scoped to library public APIs.

## Ship a scoped change safely

Invoke `/ship [PR URL, issue, or task focus]` to commit and push the scoped change, create a draft PR through the required publisher, obtain independent review, remediate findings, and repeat review and applicable checks until ready. It then marks the PR ready, rechecks the current base and exact head, merges with an expected-head guard, and verifies the remote result. Existing PRs are reused. Missing required approvals or unavailable capabilities remain explicit blockers; creating this command does not run it.

PR labels show review, remediation, blocked, ready, and queued status, following the repository’s existing label conventions. The fallback names are `ship:review`, `ship:fixing`, `ship:blocked`, `ship:ready`, and `ship:queued`. Labels supplement the observed checks and GitHub state; they do not authorize a merge. Issue labels remain unchanged unless explicitly requested or required by the project.

The `pull-request` skill owns PR writing and publication. It uses Octo when repository policy requires it or the workflow selects it, and the native review-platform workflow otherwise; an installed Octo command alone does not select it.

The Git guidance includes the `ship` skill in new project setups. Existing installations can preview `source-code upgrade --dry-run`, then upgrade to link it locally; visibility and storage selections are retained. Codex and Claude use the project skill as `/ship`; the dotfiles Claude command is a thin adapter to the same canonical procedure. Native skill discovery may require a new session or catalog reload. Copied installations retain a portable copy of the same workflow and its selected dependencies.

## Canonical skill storage

`--skill-storage linked` is the default for new installations. Skills without per-project configuration use directory symlinks under `.agents/skills/`. Configuration-dependent packages use real directories containing selected canonical file links and generated or adapted files. Claude aliases reach those same packages. Keep the source checkout at a stable location. Repositories linked to different source checkouts follow those checkouts independently; updating one source does not update another.

Linked canonical files and their release versions follow the source immediately. Rerun setup or upgrade to refresh package selection and generated or adapted files after source or configuration changes. `validate` and `explain` resolve current versions from the linked registry rather than treating setup-time observations as pins. The override lists selected skills without freezing their versions. Project stage, policy version, generated checks, and check dependencies remain project configuration: review and apply their changes with setup or upgrade. A canonical policy-version change requires reconciliation with each project's installed runtime; live skill links do not silently migrate generated checks.

Compatibility selectors keep older directory-linked packages readable until setup or upgrade replaces them with the selected project guidance.

Existing copied installations retain copied storage. Configuration updates can remove unchanged managed policy fragments, including tracked copied references, while preserving customized or unmanaged content. Preview `source-code setup --authority AUTHORITY --adoption ADOPTION --skill-storage linked --dry-run` to migrate storage explicitly. Migration to linked storage rejects tracked artifacts that would be hidden or replaced with local links; remove them from the index separately if intended. The command never untracks files. The reverse `--skill-storage copied` materializes portable packages without writing through the links. CLI overrides do not rewrite authored TOML; set `skill_storage = "copied"` there to retain that selection.

## CLI construction

The project-only `cli` skill is part of the core engineering profile and applies when building or reviewing command-line interfaces. It routes to the canonical language tool catalog and requires a compact Markdown `TOOL skill` entrypoint with task guidance available through `TOOL skill --topic NAME`. Discovery reads bundled resources without loading project configuration, resolving credentials, contacting services, or running application setup. Authority, adoption, established command meanings, and migration scope remain binding. This is implementation/review guidance; an automated application-compliance gate remains separate follow-up work.

## Policy inspection and agent discovery

`source-code skill` prints the exact management `SKILL.md` as Markdown, including frontmatter, with no extra stdout text. Use `source-code skill --topic inspection`, `--topic setup`, or `--topic validation` to read the matching progressive-disclosure reference without locating its package directory. It works outside Git, ignores project TOML, and exits nonzero with a diagnostic on stderr if the packaged skill is unavailable. It does not install skills into the target or select engineering policy.

Use `source-code explain --repo PATH` for a human-readable desired-versus-recorded policy comparison, or add `--json` for one machine-readable object. It accepts the setup policy-selection options, including `--config`, `--kind`, `--authority`, `--adoption`, `--stage`, `--skills`, and language flags, but not `--init`, `--conflict`, or `--dry-run`. It uses setup resolution and supports an existing directory before Git initialization. It does not initialize Git, modify project/Git files, provision dependencies, or run project commands.

The JSON contract has `schema_version = 1`, `repository`, `configuration` (path or null), `desired`, `installed` (recorded metadata or null), `selection`, `origins`, `differences`, and `warnings`. Desired/installed views include stage, optional kind, authority/adoption, mode, skill storage and canonical source, skills and resolved versions, agent/template choices, detection choice, and check profiles. `selection` separates packages selected for update from retained packages. Origins distinguish CLI, applied TOML, saved state, defaults, detection, dependencies, and source release metadata; skills have individual origins. Differences identify dotted field names with desired and recorded values. Unversioned legacy skills remain visible with null pins.

For each check profile, `enabled` means it would be present after setup, `selected` means this invocation selects it for installation/update, and `action` is `install`, `update`, `retain`, or `absent`. Thus `--no-go` on an existing Go installation reports a retained profile rather than implying removal. JSON output contains no progress text; failures report to stderr and exit nonzero. Invalid TOML or malformed recorded metadata is an error rather than an empty successful result.

Inspection reports choices and recorded installation, not integrity or readiness. It does not parse or merge legacy Go YAML, validate install conflicts, or execute the selected gates. Follow inspection with `setup --dry-run` for installation planning and `validate` plus the project's checks for their respective evidence. Upgrade-specific compatibility checks remain in `upgrade --dry-run`.

## TOML configuration

Author `source-code.toml` at the target repository root to make desired policy reviewable. Linked setups create it when absent; copied installations can use CLI and saved-state selections without it. Setup, validation, and upgrades discover the same file. Generated `.source-code.json` records installed policy; do not replace it with authored configuration.

```toml
schema_version = 1
authority = "owned"
adoption = "new"
stage = "alpha"
kind = "library"
mode = "shadow"
skill_storage = "linked"
skills = ["builder", "architecture", "pull-request"]
agents = "both"
pr_template = "none"
detect_languages = true
# policy_version = "1.1.0" # Optional constraint on the installed source release.

[checks.go]
enabled = false

[checks.typescript]
enabled = false
# To adopt TypeScript checks instead:
# enabled = true
# rollout = "ratchet"
# projects = ["tsconfig.json"]
```

The supported top-level keys are `schema_version` (required, currently `1`), `stage`, `kind`, `authority`, `adoption`, `mode`, `skills`, `agents`, `pr_template`, `detect_languages`, `policy_version`, and `checks`. `[checks.protobuf]` accepts only `enabled`. `[checks.python]` accepts `enabled` and a nonempty `paths` array; `--python-path` overrides that array. Skills are a nonempty array of unique curated names. `[checks.go]` accepts `enabled` and `rollout`; `[checks.typescript]` additionally accepts `projects`, a nonempty array of unique repository-relative leaf tsconfig paths. Rollout is `strict` or `ratchet`. Omitted fields preserve saved choices or existing defaults; false is an explicit choice. A disabled check cannot also select its rollout or projects. Existing check profiles are retained under the CLI's `--no-go` / `--no-typescript` semantics rather than silently removed.

Optional `kind = "service" | "library" | "tool"` selects how the software is consumed. It is independent of lifecycle stage and language, never inferred, and retained when omitted on subsequent runs. `--kind KIND` overrides TOML. Service guidance focuses on integrations and operations, library guidance on public caller contracts and compatibility, and tool guidance on invocation, diagnostics, exit outcomes, and installation. Library kind also selects the library comment skill. Kind appears in generated policy and agent guidance; it does not change generated test commands or prescribe architecture. Repeating an unchanged kind or stage does not broaden a requested skill-subset upgrade or refresh retained package pins. Directory-specific kinds remain future work.

`skill_storage = "linked" | "copied"` selects canonical links or portable packages independently of `mode`. Explicit CLI options override TOML values, which override saved installation selections, which override defaults. A CLI `--no-go` or `--no-typescript` suppresses lower-priority rollout/projects settings from TOML for that invocation. Setup and upgrade print the configuration source, supplied intent, and resolved configuration before applying changes; `--dry-run` prints the same plan without writes. Ordinary setup and upgrade leave authored TOML, comments, and formatting byte-for-byte intact.

Use `--config PATH` on setup, validation, or upgrade for an alternate or private file. Explicit relative paths resolve from the invocation directory, not `--repo`. Missing explicit files, malformed TOML, unknown keys, unsupported versions, invalid types, and incompatible settings fail before installation writes. An alternate path is not persisted in shared state: supply it again on later commands; otherwise root `source-code.toml` discovery applies.

Shadow mode adds a local exclusion for the selected authored file only when it is inside the target repository and untracked. It never hides tracked configuration or adds outside files to managed artifacts. Tracked authored configuration remains visible even when its generated installation is private. Configuration sources are not included in generated content fingerprints or silently overwritten by upgrades.

`source-code validate` checks TOML and installed packages without writes. With an authored file but no installation, it explicitly reports configuration-only validation. With an installation, declared choices that differ from installed state produce drift warnings (`--strict` fails on them); run setup or upgrade to reconcile. `--skills-dir` remains package-only validation and cannot be combined with an explicit `--config`.

## Strict Python checks

Opt in with `source-code setup --python --authority owned --adoption new`; Python detection remains guidance-only. Select scope with repeatable `--python-path PATH` or authored TOML:

```toml
[checks.python]
enabled = true
paths = ["src", "tests"]
```

Python adoption is strict immediately, without a ratchet baseline. Generated `.python-quality.json` records paths and explicit test/legacy argv; root project configuration and dependency files are preserved. The isolated `.python-quality/` tool project pins Ruff, ty, and pip-audit with a committed uv lock. Run `python3 scripts/check-python.py tools` explicitly, then `python3 scripts/check-source-code.py python`. Checks verify both the lock and installed tools before running, and never format source in place.

Research runs strict typing and inherited gates. Alpha adds format checking, safety/lint checks, and tests; beta/production add locked dependency auditing. Unsupported or unlocked runtime dependency declarations fail the audit without execution. Configure `commands.test` and `commands.legacy` in `.python-quality.json` to retain the application's real gates; the default test is `uv run --locked pytest`. `--no-python` retains an existing profile rather than uninstalling it.

The source-code implementation itself uses this profile: `make source-code-python-tools` provisions pinned tools and `make source-code-python-check` runs the full gate, including real installer acceptance and profile failure cases. The committed scope includes the CLI, detector, canonical Python/lifecycle runners, and Python profile acceptance detector, rather than unrelated dotfiles Python. CI runs the same committed runner as the Make entrypoint. The tracked `.python-quality.json` declares this scope, and Make and CI run its `all` gate. Root `source-code.toml` selects shadow-linked guidance and disables installer-managed check profiles so setup does not adopt or hide those standalone checks.

## Workstation installation and language detection

The user-level `source-code` skill explains installation, detection, validation, and upgrades without loading project engineering policy. Agents can retrieve the exact skill with `source-code skill`, including outside a Git repository; the command prints only Markdown and never reads project configuration. Coding skills remain project-only.

The `workstation` set selects `tools.source-code`, whose setup target links `source-code` and the `repo-bootstrap` compatibility command. Basic shell/terminal setup does not install those commands. Select `[tools] source-code = true` independently or use `false` to opt out. The Octo executable remains a separately selected tool; linking source-code does not install it or start its daemon. Repository profiles select publication guidance independently. Configuration only links commands. Project policies are selected explicitly.

```sh
source-code detect --repo ~/src/project --json
source-code setup --repo ~/src/project --authority owned --adoption new --stage alpha --mode shadow
source-code setup --repo ~/src/project --authority owned --adoption new --no-detect-languages
```

Basic detection uses manifests and source-file extensions for Go, TypeScript, JavaScript, Python, Rust, and Protobuf, including nested projects. Git supplies tracked and unignored files; pre-Git directories use a pruned directory walk that skips dependency/build directories. Installed managed files do not classify their own implementation language as application code. Results include a small set of evidence paths and are read-only. Detection is heuristic, not an exhaustive language census; select additional skills explicitly when needed.

Detection chooses language skills and records evidence in the policy's `detection` field. Detected Protobuf sources and Buf workspaces also select the Protobuf check profile by default, unless explicitly disabled. TypeScript/Python checks and Rust tooling remain explicit project choices. `languages` separately records installed generated Go/TypeScript/Python/Protobuf check profiles. The detection opt-out persists across upgrades. Removing a language file can update detection evidence without uninstalling existing skills or checks.

## Optional project capabilities

Select `data-pipeline` for warehouse layers, declarative schemas, and ETL guidance, or `ui-acceptance` for rendered UI evidence, interaction coverage, and project-scoped visual rules. They include the core architecture, testing, and lifecycle dependencies needed to interpret that guidance. Neither is selected automatically from language detection, installed workstation tools, or a project's apparent maturity. Research still permits a disposable experiment; retained behavior and existing repository gates govern durable protection.

```sh
source-code setup --repo ~/src/project --authority owned --adoption new --skills data-pipeline,ui-acceptance --dry-run
# Review the selection before applying the same command without --dry-run.
```

The project-only `ui-review` skill supplies Viewrule commands and explicit user-feedback handling for frontend projects, and selects `ui-acceptance` as a dependency. It does not authorize unrelated design changes or new CI gates. Project `ui-acceptance` works with the project's selected capture tools; Viewrule is optional. The `data-pipeline` skill is project-only and is removed from managed user catalogs on workstation skill sync, while unrelated local entries and aliases are preserved.

The installed Git profile owns [review and merge assessment](../ai/skills/git/references/review.md); PR writing conventions stay in the project's PR guidance. Global operating procedures retain authorization and truthful outcome reporting, without choosing reviewers or a publication tool for every repository. Installing a profile grants no push, PR, merge, or messaging authority.

## Authority and tool adoption

Every `source-code setup` invocation requires `--authority owned|shared|upstream` and `--adoption hold|new|backfill`, including `--dry-run` and repeated setup when authored TOML or saved state contains these choices. Missing flags produce a usage error before configuration loading or installation. Upgrade resolves these choices from CLI → TOML → saved state and requires explicit flags when neither configured nor saved values exist. These selections are independent of lifecycle stage and project kind; explain can show unset values without writes. Existing installations remain usable, and validation reports missing legacy selections. Public/open-source visibility does not establish authority.

Owned projects choose their stack; shared projects require project agreement, and upstream contributions follow maintainer conventions. Hold preserves the existing stack. New applies the required catalog to new independent surfaces while retaining established implementations. Backfill also records migration direction, but migration execution requires an explicitly agreed task scope. Shared/upstream adoption settings do not themselves grant authority; record the relevant project agreement before changing conventions. Shadow installation does not count as agreement.

Read the [application tool catalog](../ai/skills/source-code-lifecycle/references/tool-catalog.md) for tool choices, boundary rules, and the exception format. It requires Commander for TypeScript/JavaScript CLIs, Cobra plus lanej/charmed for Go command structure and terminal UI, and Connect for new application APIs we control when adoption selects the catalog. External integrations use the provider's protocol; protocol-specific edges retain the protocol appropriate to their contract. The catalog also covers Python/Rust CLIs, web UI, validation, logging, configuration, and tests. Install only tools the capability needs.

The lifecycle package installs the catalog when adoption is `new` or `backfill`; `hold` omits it. Relevant language, architecture, and construction skills route through the selected authority and adoption guidance. This release imposes binding agent implementation/review guidance; validation checks policy structure, not application dependency compliance. An [automated tool-choice gate](https://github.com/lanej/dotfiles/issues/323) is a separate follow-up.

## Lifecycle stages

Source-code engineering skills are project-only; the `source-code` management skill remains user-level. Project packages are absent from the default user-level Claude, Codex, and Pi catalogs. `ai/skills/project-only.json` defines that boundary, including Git, GitHub Actions, PR stacks, PR writing, data pipelines, and UI acceptance. Coding lessons formerly bundled into user-level `operating-lessons` now ship with the relevant project Git, testing, architecture, Python, and JavaScript skills; `agent-coordination`, `verify-claims`, `tool-operation`, and `document-consistency` provide focused user-level guidance with conditional references. Zellij and source-code management also remain user-level across supported agents. Install them explicitly, then reload the client's skill catalog if necessary. Normal workstation setup retires the managed global Builder rule and guidance, preserves personal skills and aliases, and keeps explicit legacy package references readable.

```sh
source-code setup --repo ~/src/experiment --authority owned --adoption new --go --stage research --mode shadow --pr-template none
source-code setup --repo ~/src/experiment --authority owned --adoption new --stage alpha --dry-run
source-code setup --repo ~/src/experiment --authority owned --adoption new --stage alpha
python3 scripts/check-source-code.py go
```

| Stage | Generated checks | Additional evidence |
| --- | --- | --- |
| research (including POCs) | Go compile or TypeScript typecheck; inherited gates stay binding. | Exercise the experiment and record findings and limits. |
| alpha | Lint, compile/typecheck, and tests; added race/vulnerability/audit passes are deferred. | Protect retained behavior and consequential failures. |
| beta | Full language profile. | Affected integrations, compatibility/migrations, and caller contracts. |
| production | Full language profile. | Independent review and applicable recovery, rollout, and operational evidence. |

`.source-code.json` separates schema version `1`, policy version `1.1.0`, and the selected stage. The install manifest retains the source revision and content fingerprints. Unknown versions or stages fail before commands run. Policy version changes describe changed rules; stage changes describe the project's chosen assurance level. Neither asserts readiness or measured service reliability.

Beta is the default and preserves the former full generated checks. Reruns retain the selected stage. A stage-change preview shows old and new command plans; application uses the existing conflict and backup safeguards. A modified lifecycle policy cannot be silently skipped while other files adopt a different stage. Early-stage transitions reject incompatible older language runners retained by `--no-go` or `--no-typescript`; update that runner or keep full checks. Stage selection and strict-versus-ratchet adoption remain independent.

The stage selects both agent guidance and the generated CI gate. It does not waive other required repository checks, secrets handling, or protections against irreversible effects. Production's additional evidence is reviewed separately; the generic runner cannot certify it. See the [lifecycle contract](../ai/skills/source-code-lifecycle/references/lifecycle.md) for the complete stage expectations.

## Comment policies

The shared comment policy is the default inside a selected project profile. Select `code-comments` to install it in a project, or `library-code-comments` to include both the shared policy and the library caller perspective. Selecting the Go or TypeScript skill also bundles both comment skills, including through `--go` and `--typescript`, in strict and ratchet modes. The library perspective applies to public library APIs; services retain the shared default. Existing project instructions remain authoritative.

```sh
# Use library guidance privately in another repository, without a PR template.
source-code setup --repo ~/src/library --authority upstream --adoption hold --skills library-code-comments --mode shadow --pr-template none
```

Local mode excludes the installed files through Git's `info/exclude`, retaining shared instructions and `.gitignore`. Reload the client's skill catalog if necessary, then explicitly request `library-code-comments` for the library work. Installation makes the skill available; it does not rewrite project policy or guarantee that every client selects it automatically. To share the policy with a team, use `--mode tracked` and review and commit the files.

For a mixed repository, project instructions may select `library-code-comments` for a library directory and leave services on the default policy. For private use, state that directory scope in the task rather than editing shared instructions.

The source-code setup check validates source skill metadata and resource links, then validates portable installed comment skills after cloning. It also verifies that shadow installation stays out of normal Git status. These checks run in CI; they validate package structure and installation, not model behavior.

## PR templates

GitHub only discovers committed templates on the repository's default branch. A local drafting template is not a GitHub default. The supplied template contains removable drafting prompts, without mandatory headings or checklists. Fill it with the change's outcome and motivation, then remove the comments before publishing.

When installing a GitHub template, alternate templates in the repository root, `docs`, or `.github` cause an explicit conflict, including multiple-template directories. Choose `--pr-template none` or `local` to retain the existing selection. An existing `.github/pull_request_template.md` uses the same conflict policy as other files.

## Go correctness profile

A root `go.mod` opts into Go guidance, checks, and a portable CI workflow. New repositories use whole-project strictness:

```sh
source-code setup --repo ~/src/new-go-project --authority owned --adoption new --init --go
```

Existing configs or tracked Go source default to a ratchet, so adopting stronger rules does not require rewriting the project. To retrofit explicitly, start with committed Go source:

```sh
source-code setup --repo ~/src/service --authority shared --adoption hold --go-retrofit --pr-template none
cd ~/src/service
bash scripts/check-go.sh baseline
bash scripts/check-go.sh
```

The installer preserves existing YAML/JSON v2 config bytes and comments. It combines project settings, extra checks, and build context with the defaults in `.golangci.strict.json`; `.go-quality.json` selects that layer and records its original input. The original lint gate still runs unchanged, with autofixing disabled. The added layer owns its checker settings and defaults, full-tree reporting, and its own exclusions; custom settings for additional project checks are retained. Config changes require rerunning bootstrap to refresh the merge. Multiple configs, duplicate YAML keys, unsupported versions, and unsafe linked paths fail before target writes. V1 configs need migration; TOML needs conversion. Go YAML merging uses installed PyYAML, or caches PyYAML 6.0.3 through uv when absent.

Baseline creation records existing lint/style findings against committed Go code and never rewrites it. New file paths have no allowance. New signatures in existing files fail too, including untouched consumers invalidated by a new enum value. After fixing old findings, `bash scripts/check-go.sh ratchet` removes their allowances and refuses to grow the baseline. Normal lint requires resolved allowances to be removed. See [the Go style guide](go-style.md) for the signature-budget limitation, policy choices, and examples. Compilation, the original lint gate, module tidiness, race tests, and vulnerability analysis are not grandfathered.

Use `--go-rollout strict` for whole-project enforcement. Use `--no-go` to retain existing checks without updating the added profile; `--skills go --no-go` installs guidance alone. Existing workflow paths and other managed-file edits retain normal conflict protection. Reruns remember the rollout. As elsewhere, opt-outs do not uninstall previously copied files.

Run `bash scripts/check-go.sh lint` while editing, `fmt path/to/file.go` for formatting, and the full command before delivery. `fix ./path/to/package` applies available cuddling fixes in that package; inspect its diff. A ratchet requires explicit formatting paths to avoid a broad cleanup. Go and Python 3.11+ are required; initial pinned tool setup needs network access, and race tests require cgo and a C compiler.

Local mode hides copied files and the baseline without changing the original config's visibility. Shared CI requires committing a tracked installation, including its required original config. Make the `Go quality` job required in branch rules for a merge gate; bootstrap does not change GitHub settings. The default runner covers one root module on its host platform. Add other modules, build tags, platform variants, native dependencies, and required integration tests explicitly.

## Update without losing repository edits

After updating dotfiles, use the upgrade command from that checkout:

```sh
source-code upgrade --repo ~/src/app --dry-run
source-code upgrade --repo ~/src/app
```

Reruns reuse the saved mode unless `--mode` is supplied. Unchanged managed files update automatically; files matching the new content are left alone. Any changed existing content fails the whole preflight by default, before installed files are written. No repository pulls or branch changes are implicit. A first YAML configuration merge may cache its pinned parser dependency; the installer does not install project Go tools.

`upgrade` requires an existing installation and preserves its stage, skill selection, language profiles, agent aliases, template choice, and tracked/shadow mode. It validates the selected source skill packages before updating. It updates to the releases shipped by the installed `source-code` checkout, not an implicit remote registry. `--policy-version VERSION` requires that available version; unavailable versions fail before project writes. Lower available skill or policy versions are rejected by `upgrade`. Use a newer checkout, rather than silently downgrading pinned releases.

The canonical `ai/skills/source-code-versions.json` owns skill-release versions. In copied installations, `.source-code.json` pins the installed versions; the installed registry and generated override agree with those pins. Skill versions, lifecycle stage, policy version, source revision, and file fingerprints remain distinct. Updating a subset preserves the pins of retained skills. A version-changing update cannot skip locally customized skill content and still claim the newer release.

`setup` remains the installation and reconfiguration command; it can also update installed files. Older installations can use `upgrade` to add pins and generated guidance. Existing `AGENTS.override.md` files require reconciliation or explicit `--conflict replace`, which saves the original in the installer's backup directory. Shadow mode excludes the router, generated policy, registry, and Claude rule along with all other managed artifacts.

## Validate skill packages

```sh
source-code validate --repo ~/src/app
source-code validate --repo ~/src/app --strict
source-code validate --skills-dir ai/skills/testing --strict
```

Validation checks safe YAML frontmatter, duplicate keys, names, selection descriptions, nonempty instructions, local resource links, entrypoint size guidance, and supporting-resource layout. Installed-project validation also checks recorded paths, release pins, policy/manifest consistency, and generated guidance. Linked installations additionally verify owned link targets and report live canonical skill versions. It reads project files without executing their scripts or changing them. PyYAML or uv is required; uv may populate its parser cache outside the target project.

Structural defects, missing files, unexpected links, and inconsistent pins or guidance fail validation. Best-practice warnings and local content customizations are reported; `--strict` makes them blocking. These checks do not establish prose quality, model adherence, or software correctness. Use the lifecycle gate and relevant behavioral evidence separately. `upgrade --strict` likewise rejects best-practice warnings in its source packages.

- `--conflict skip` updates independent files and reports preserved local edits. Skipped files are not marked as successfully updated.
- `--conflict replace` explicitly replaces conflicting regular files after saving their original contents under Git's `repo-bootstrap/backups/replace-*` directory. The command prints the backup location. It never replaces symlinks or directories; reconcile those manually.
- Selected skills and templates are **additive**. Selecting fewer skills, `--agents codex`, or `--pr-template none` does not uninstall earlier packages. Configuration-dependent packages remove obsolete managed policy fragments only when unchanged; other files removed from an upstream package are retained. Remove unwanted files deliberately after reviewing repository dependencies.

To make a local install shareable, use `--mode tracked` and review the new Git status. Linked skills and local ownership metadata remain excluded. For copied installations, the installer’s exclusion block is removed; unrelated ignore rules are preserved and still checked. Changing tracked content to local mode requires first deciding, separately, whether it should be removed from the Git index. No automatic untracking occurs.

The manifest records content hashes, not proof of origin or security. Keep it with the files it describes. Malformed manifests, linked destination directories, missing source resources, and conflicting templates fail closed. Dry runs create no repository files or Git metadata. Run one installer at a time while the destination is otherwise idle: preflight catches observed changes, but this is not a transaction against concurrent editors or processes. Files are replaced atomically one at a time; an I/O interruption can leave a partial install, which is reported as failure rather than completion.

## Verification

```sh
make test-repo-bootstrap
make test-go-quality  # real analyzers, downloads pinned tools on first run
```

The single acceptance workflow exercises the real command: bootstrap and clone a tracked installation, resolve its local Markdown resources, run Builder's bundled examples, retrofit a linked worktree, preserve project policy, update unchanged resources, protect and explicitly replace local edits with backups, and verify effective Git exclusion and tracking behavior. It does not invoke an agent model or establish that every client version discovers or follows the instructions.

## Protobuf correctness profile

Setup and upgrades automatically select the Protobuf profile for detected project `.proto` files or Buf workspace files, including nested directories. Explicitly select it with `source-code setup --authority owned --adoption new --protobuf` or `[checks.protobuf] enabled = true`; save an opt-out with `--no-protobuf` or `enabled = false`. Disabling language detection prevents automatic selection. The portable [profile guide](../ai/skills/protobuf/references/correctness.md) describes the pinned Buf tools, strict lint, check-only formatting, explicit compatibility baseline, and a native Buf check plugin rejecting `string *_json` fields. Project Buf workspace, dependency, and code-generation configuration is preserved.

Run `python3 scripts/check-protobuf.py tools` explicitly, then `python3 scripts/check-source-code.py protobuf`. Configure a real compatibility baseline through `PROTOBUF_AGAINST` or `.protobuf-quality.json` for beta/production; alpha adds lint/format to research's compile and JSON string field checks. The generated CI uses the official Buf Action for CLI setup and the PR base or previous push SHA for compatibility. Go builds the small native plugin from its pinned SDK module. The custom rule checks only `string` fields ending in `_json`; it does not ban generic payload names or dynamic types, and cannot prove arbitrary application code never serializes JSON into an innocently named string. `--no-protobuf` retains installed checks. Setup previews, validation, upgrades, tracked installs, and shadow installs use the same profile contract as the other languages.

TypeScript setup honors an exact `packageManager = "bun@VERSION"` in `package.json`: generated CI installs that Bun version and preserves the application’s Bun lockfile, while isolated quality tools continue using their own npm lockfile. A root Go module also selects its declared Go version for mixed-language tests. The Go workflow likewise installs the pinned Bun runtime and application dependencies when the project declares Bun, so Go-to-Bun integration tests can run. Existing command policies are retained. The isolated TypeScript CI job uses a 4 GiB Node heap budget for whole-project typed analysis.
