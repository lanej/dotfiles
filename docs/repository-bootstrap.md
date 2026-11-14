# Source-code setup

Use `source-code setup` to bring the shared Builder, architecture, and PR-writing guidance into a new or existing Git repository. It copies portable files rather than linking to a particular machine's dotfiles checkout. It preserves existing shared instructions and installs a project override that routes to the selected policy. It does not install software, modify global agent settings, stage files, or publish changes.

The command needs Python 3.9+ and Git 2.31+ on macOS or Linux. Run `~/.files/bin/source-code setup` directly, or use `source-code setup` after `make source-code-config` has linked the commands into `~/.local/bin`.

`repo-bootstrap` remains a compatibility alias for `source-code setup`, accepting its existing flags. Existing `.agents/repo-bootstrap.json` manifests, exclusion markers, and backup paths retain their names so either command can safely update an existing installation.

## Bootstrap a new repository

```sh
~/.files/bin/source-code setup --repo ~/src/new-project --init --dry-run
~/.files/bin/source-code setup --repo ~/src/new-project --init
```

`--init` creates the directory and initializes Git only if the target is not already a working tree. It refuses a nested initialization inside another repository. Without `--init`, the target must be an existing Git working tree; a subdirectory resolves to that working tree's root.

The default is **tracked mode**: files are available for normal review and commit, but the command does not stage them. Review `git status` and the contents, then add the desired files. Include `.agents/repo-bootstrap.json` alongside the installed skills so other checkouts retain safe-upgrade information.

## Retrofit an existing repository

```sh
~/.files/bin/source-code setup --repo ~/src/existing-project --mode local --dry-run
~/.files/bin/source-code setup --repo ~/src/existing-project --mode local
```

**Local mode** puts precise file exclusions in a marked block of Git's `info/exclude`; it leaves `.gitignore` unchanged. Installed skills remain usable on this machine, without appearing in normal `git status` or `git add .`. Existing tracked files cannot be hidden this way, so local mode refuses to manage paths already in the index. Higher-priority `.gitignore` negations that defeat an exclusion are reported before installation. Exclusion is not encryption or access control, and `git add -f` can still add these files.

`--mode shadow` is an alias for local mode. The manifest records `local`, so subsequent installs retain the same exclusions without needing the flag again. Canonical skill sources remain versioned in dotfiles; shadow mode hides only the installed copies in the target repository. The manifest retains file fingerprints for safe updates and detects local modifications.

Linked worktrees are supported. Git shares `info/exclude` between worktrees: the same exact paths are excluded in sibling worktrees too. The installer does not untrack anything or change Git configuration. Worktrees requiring different tracking policies should not mix local and tracked installations at the same paths.

Existing `AGENTS.md`, `CLAUDE.md`, `.gitignore`, unrelated skills, and project PR templates are retained. The generated `AGENTS.override.md` records the chosen stage and pinned versions and directs the agent to read the existing `AGENTS.md` first. Codex loads the override instead of the same-directory `AGENTS.md`; this first-read instruction preserves the shared context. Claude installations add `.claude/rules/source-code.md` to route to the same override. Existing overrides and rules retain normal conflict protection. Start a new session or reload the client's skill catalog after installation.

## Installed content

| Path | Purpose |
| --- | --- |
| `.agents/skills/builder/` | Existing Builder skill, architecture/construction references, and runnable examples |
| `.agents/skills/architecture/` | Architecture design/review entrypoint using Builder's canonical standard |
| `.agents/skills/pr-writer/` | PR drafting entrypoint, shared/GitHub writer instructions, and their writing references |
| `.agents/skills/testing/` | Stage-specific verification and retained-behavior guidance |
| `.agents/skills/source-code-lifecycle/` | Versioned lifecycle contract and command plans |
| `.source-code.json` | Schema version, policy version, stage, and installed languages |
| `AGENTS.override.md` | Generated project instructions and readable skill-version summary |
| `.agents/source-code-versions.json` | Installed skill-release registry matching the project pins |
| `.claude/rules/source-code.md` | Claude's project-local route to the generated guidance, when selected |
| `scripts/check-source-code.py` | Selected lifecycle gate, shared by local execution and generated CI |
| `.claude/skills/<name>` | Relative links to the same skill packages for Claude Code |
| `.agents/repo-bootstrap.json` | Installed-file fingerprints and mode for safe updates |
| `.github/pull_request_template.md` | GitHub template, the default in tracked mode |
| `.agents/templates/pull_request_template.md` | Local drafting template, the default in local mode |

Codex uses `.agents/skills`. Claude Code uses the individual `.claude/skills` links; existing directories and unrelated entries are preserved. Pass `--agents codex` to omit new Claude links. Other agents can read these Markdown packages explicitly, but the installer does not claim to configure their native discovery or tool permissions.

The architecture skill automatically includes Builder because it shares the standard. PR writer retains the existing draft-only boundary: installation does not authorize creating, updating, or merging a PR. It respects the target repository's required title and template fields.

Choose a subset or template independently:

```sh
# Architecture includes its Builder dependency; omit new Claude aliases.
source-code setup --repo ~/src/app --skills architecture --agents codex --pr-template none

# Keep an existing team PR template while sharing the skills.
source-code setup --repo ~/src/app --mode tracked --pr-template none

# Keep a private drafting template alongside an existing GitHub template.
source-code setup --repo ~/src/app --mode tracked --pr-template local
```

`--skills` accepts the names listed by `source-code setup --help`, comma-separated. The core includes Builder, architecture, data/interface planning, Git/PR workflow, testing, lifecycle, and shared comments. Language guidance covers Go, TypeScript, JavaScript, Python, and Rust; `gh-pr-stack`, `github-actions`, and `just` are available explicitly. These are curated portable packages, not an automatic copy of workstation skills. Language detection selects matching guidance; root Go modules retain their existing automatic check-profile behavior.

## Workstation installation and language detection

The `workstation` set selects `tools.source-code`, whose setup target links `source-code` and the `repo-bootstrap` compatibility command. Basic shell/terminal setup does not install those commands. Select `[tools] source-code = true` independently or use `false` to opt out. This installs commands only; project policies are still selected explicitly.

```sh
source-code detect --repo ~/src/project --json
source-code setup --repo ~/src/project --stage alpha --mode shadow
source-code setup --repo ~/src/project --no-detect-languages
```

Basic detection uses manifests and source-file extensions for Go, TypeScript, JavaScript, Python, and Rust, including nested projects. Git supplies tracked and unignored files; pre-Git directories use a pruned directory walk that skips dependency/build directories. Installed managed files do not classify their own implementation language as application code. Results include a small set of evidence paths and are read-only. Detection is heuristic, not an exhaustive language census; select additional skills explicitly when needed.

Detection chooses language skills and records evidence in the policy's `detection` field. It does not introduce TypeScript checks, Python/Rust tooling, or CI; those remain explicit project choices. `languages` separately records installed generated Go/TypeScript check profiles. The detection opt-out persists across upgrades. Removing a language file can update detection evidence without uninstalling existing skills or checks.

## Lifecycle stages

Source-code skills are project-only: they are absent from the default user-level Claude, Codex, and Pi catalogs. `ai/skills/project-only.json` defines that boundary. Install them explicitly, then reload the client's skill catalog if necessary. Normal workstation setup retires the managed global Builder rule and guidance, preserves personal skills and aliases, and keeps explicit legacy package references readable.

```sh
source-code setup --repo ~/src/experiment --go --stage research --mode shadow --pr-template none
source-code setup --repo ~/src/experiment --stage alpha --dry-run
source-code setup --repo ~/src/experiment --stage alpha
python3 scripts/check-source-code.py go
```

| Stage | Generated checks | Additional evidence |
| --- | --- | --- |
| research | Go compile or TypeScript typecheck; inherited gates stay binding. | Exercise the experiment and record findings and limits. |
| alpha | Lint, compile/typecheck, and tests; added race/vulnerability/audit passes are deferred. | Protect retained behavior and consequential failures. |
| beta | Full language profile. | Affected integrations, compatibility/migrations, and caller contracts. |
| production | Full language profile. | Independent review and applicable recovery, rollout, and operational evidence. |

`.source-code.json` separates schema version `1`, policy version `1.0.0`, and the selected stage. The install manifest retains the source revision and content fingerprints. Unknown versions or stages fail before commands run. Policy version changes describe changed rules; stage changes describe the project's chosen assurance level. Neither asserts readiness or measured service reliability.

Beta is the default and preserves the former full generated checks. Reruns retain the selected stage. A stage-change preview shows old and new command plans; application uses the existing conflict and backup safeguards. A modified lifecycle policy cannot be silently skipped while other files adopt a different stage. Early-stage transitions reject incompatible older language runners retained by `--no-go` or `--no-typescript`; update that runner or keep full checks. Stage selection and strict-versus-ratchet adoption remain independent.

The stage selects both agent guidance and the generated CI gate. It does not waive other required repository checks, secrets handling, or protections against irreversible effects. Production's additional evidence is reviewed separately; the generic runner cannot certify it. See the [lifecycle contract](../ai/skills/source-code-lifecycle/references/lifecycle.md) for the complete stage expectations.

## Comment policies

The shared comment policy is the default inside a selected project profile. Select `code-comments` to install it in a project, or `library-code-comments` to include both the shared policy and the library caller perspective. Selecting the Go or TypeScript skill also bundles both comment skills, including through `--go` and `--typescript`, in strict and ratchet modes. The library perspective applies to public library APIs; services retain the shared default. Existing project instructions remain authoritative.

```sh
# Use library guidance privately in another repository, without a PR template.
source-code setup --repo ~/src/library --skills library-code-comments --mode shadow --pr-template none
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
source-code setup --repo ~/src/new-go-project --init --go
```

Existing configs or tracked Go source default to a ratchet, so adopting stronger rules does not require rewriting the project. To retrofit explicitly, start with committed Go source:

```sh
source-code setup --repo ~/src/service --go-retrofit --pr-template none
cd ~/src/service
bash scripts/check-go.sh baseline
bash scripts/check-go.sh
```

The installer preserves existing YAML/JSON v2 config bytes and comments. It combines project settings, extra checks, and build context with the defaults in `.golangci.strict.json`; `.go-quality.json` selects that layer and records its original input. The original lint gate still runs unchanged, with autofixing disabled. The added layer owns its checker settings and defaults, full-tree reporting, and its own exclusions; custom settings for additional project checks are retained. Config changes require rerunning bootstrap to refresh the merge. Multiple configs, duplicate YAML keys, unsupported versions, and unsafe linked paths fail before target writes. V1 configs need migration; TOML needs conversion. Go YAML merging uses installed PyYAML, or caches PyYAML 6.0.3 through uv when absent.

Baseline creation records existing lint/style findings against committed Go code and never rewrites it. New file paths have no allowance. New signatures in existing files fail too, including untouched consumers invalidated by a new enum value. After fixing old findings, `bash scripts/check-go.sh ratchet` removes their allowances and refuses to grow the baseline. Normal lint requires resolved allowances to be removed. See [the Go style guide](go-style.md) for the signature-budget limitation, policy choices, and examples. Compilation, the original lint gate, module tidiness, race tests, and vulnerability analysis are not grandfathered.

Use `--go-rollout strict` for whole-project enforcement. Use `--no-go` to retain existing checks without updating the added profile; `--skills go --no-go` installs guidance alone. Existing workflow paths and other managed-file edits retain normal conflict protection. Reruns remember the rollout. As elsewhere, opt-outs do not uninstall previously copied files.

Run `bash scripts/check-go.sh lint` while editing, `fmt path/to/file.go` for formatting, and the full command before delivery. `fix ./path/to/package` applies available cuddling fixes in that package; inspect its diff. A ratchet requires explicit formatting paths to avoid a broad cleanup. Go and Python 3.9+ are required; initial pinned tool setup needs network access, and race tests require cgo and a C compiler.

Local mode hides copied files and the baseline without changing the original config's visibility. Shared CI requires committing a tracked installation, including its required original config. Make the `Go quality` job required in branch rules for a merge gate; bootstrap does not change GitHub settings. The default runner covers one root module on its host platform. Add other modules, build tags, platform variants, native dependencies, and required integration tests explicitly.

## Update without losing repository edits

After updating dotfiles, use the upgrade command from that checkout:

```sh
source-code upgrade --repo ~/src/app --dry-run
source-code upgrade --repo ~/src/app
```

Reruns reuse the saved mode unless `--mode` is supplied. Unchanged managed files update automatically; files matching the new content are left alone. Any changed existing content fails the whole preflight by default, before installed files are written. No repository pulls or branch changes are implicit. A first YAML configuration merge may cache its pinned parser dependency; the installer does not install project Go tools.

`upgrade` requires an existing installation and preserves its stage, skill selection, language profiles, agent aliases, template choice, and tracked/shadow mode. It validates the selected source skill packages before updating. It updates to the releases shipped by the installed `source-code` checkout, not an implicit remote registry. `--policy-version VERSION` requires that available version; unavailable versions fail before project writes. Lower available skill or policy versions are rejected by `upgrade`. Use a newer checkout, rather than silently downgrading pinned releases.

The canonical `ai/skills/source-code-versions.json` owns skill-release versions. `.source-code.json` pins the installed versions; the installed registry and generated override agree with those pins. Skill versions, lifecycle stage, policy version, source revision, and file fingerprints remain distinct. Updating a subset preserves the pins of retained skills. A version-changing update cannot skip locally customized skill content and still claim the newer release.

`setup` remains the installation and reconfiguration command; it can also update installed files. Older installations can use `upgrade` to add pins and generated guidance. Existing `AGENTS.override.md` files require reconciliation or explicit `--conflict replace`, which saves the original in the installer's backup directory. Shadow mode excludes the override, registry, and Claude rule along with all other managed artifacts.

## Validate skill packages

```sh
source-code validate --repo ~/src/app
source-code validate --repo ~/src/app --strict
source-code validate --skills-dir ai/skills/testing --strict
```

Validation checks safe YAML frontmatter, duplicate keys, names, selection descriptions, nonempty instructions, local resource links, entrypoint size guidance, and supporting-resource layout. Installed-project validation also checks recorded paths, release pins, policy/manifest consistency, and generated guidance. It reads project files without executing their scripts or changing them. PyYAML or uv is required; uv may populate its parser cache outside the target project.

Structural defects, missing files, unexpected links, and inconsistent pins or guidance fail validation. Best-practice warnings and local content customizations are reported; `--strict` makes them blocking. These checks do not establish prose quality, model adherence, or software correctness. Use the lifecycle gate and relevant behavioral evidence separately. `upgrade --strict` likewise rejects best-practice warnings in its source packages.

- `--conflict skip` updates independent files and reports preserved local edits. Skipped files are not marked as successfully updated.
- `--conflict replace` explicitly replaces conflicting regular files after saving their original contents under Git's `repo-bootstrap/backups/replace-*` directory. The command prints the backup location. It never replaces symlinks or directories; reconcile those manually.
- Selected skills and templates are **additive**. Selecting fewer skills, `--agents codex`, or `--pr-template none` does not uninstall earlier files. Files removed from an upstream package are also retained. Remove unwanted files deliberately after reviewing repository dependencies.

To make a local install shareable, use `--mode tracked` and review the new Git status. Only the installer's exclusion block is removed; unrelated ignore rules are preserved and still checked. Changing tracked content to local mode requires first deciding, separately, whether it should be removed from the Git index. No automatic untracking occurs.

The manifest records content hashes, not proof of origin or security. Keep it with the files it describes. Malformed manifests, linked destination directories, missing source resources, and conflicting templates fail closed. Dry runs create no repository files or Git metadata. Run one installer at a time while the destination is otherwise idle: preflight catches observed changes, but this is not a transaction against concurrent editors or processes. Files are replaced atomically one at a time; an I/O interruption can leave a partial install, which is reported as failure rather than completion.

## Verification

```sh
make test-repo-bootstrap
make test-go-quality  # real analyzers, downloads pinned tools on first run
```

The single acceptance workflow exercises the real command: bootstrap and clone a tracked installation, resolve its local Markdown resources, run Builder's bundled examples, retrofit a linked worktree, preserve project policy, update unchanged resources, protect and explicitly replace local edits with backups, and verify effective Git exclusion and tracking behavior. It does not invoke an agent model or establish that every client version discovers or follows the instructions.
