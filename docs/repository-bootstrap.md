# Repository skills and PR templates

Use `repo-bootstrap` to bring the shared Builder, architecture, and PR-writing guidance into a new or existing Git repository. It copies portable files rather than linking to a particular machine's dotfiles checkout. It does not install software, modify global agent settings, change repository instructions, stage files, or publish changes.

The command needs Python 3.9+ and Git 2.31+ on macOS or Linux. Run `~/.files/bin/repo-bootstrap` directly, or use `repo-bootstrap` after `make shell` has linked the dotfiles commands into `~/.local/bin`.

## Bootstrap a new repository

```sh
~/.files/bin/repo-bootstrap --repo ~/src/new-project --init --dry-run
~/.files/bin/repo-bootstrap --repo ~/src/new-project --init
```

`--init` creates the directory and initializes Git only if the target is not already a working tree. It refuses a nested initialization inside another repository. Without `--init`, the target must be an existing Git working tree; a subdirectory resolves to that working tree's root.

The default is **tracked mode**: files are available for normal review and commit, but the command does not stage them. Review `git status` and the contents, then add the desired files. Include `.agents/repo-bootstrap.json` alongside the installed skills so other checkouts retain safe-upgrade information.

## Retrofit an existing repository

```sh
~/.files/bin/repo-bootstrap --repo ~/src/existing-project --mode local --dry-run
~/.files/bin/repo-bootstrap --repo ~/src/existing-project --mode local
```

**Local mode** puts precise file exclusions in a marked block of Git's `info/exclude`; it leaves `.gitignore` unchanged. Installed skills remain usable on this machine, without appearing in normal `git status` or `git add .`. Existing tracked files cannot be hidden this way, so local mode refuses to manage paths already in the index. Higher-priority `.gitignore` negations that defeat an exclusion are reported before installation. Exclusion is not encryption or access control, and `git add -f` can still add these files.

Linked worktrees are supported. Git shares `info/exclude` between worktrees: the same exact paths are excluded in sibling worktrees too. The installer does not untrack anything or change Git configuration. Worktrees requiring different tracking policies should not mix local and tracked installations at the same paths.

Existing `AGENTS.md`, `CLAUDE.md`, `.gitignore`, unrelated skills, and project PR templates are retained. No always-loaded instructions are injected. Skills are discoverable by clients that support the installed paths; start a new session or reload the client's skill catalog if necessary.

## Installed content

| Path | Purpose |
| --- | --- |
| `.agents/skills/builder/` | Existing Builder skill, architecture/construction references, and runnable examples |
| `.agents/skills/architecture/` | Architecture design/review entrypoint using Builder's canonical standard |
| `.agents/skills/pr-writer/` | PR drafting entrypoint, shared/GitHub writer instructions, and their writing references |
| `.claude/skills/<name>` | Relative links to the same skill packages for Claude Code |
| `.agents/repo-bootstrap.json` | Installed-file fingerprints and mode for safe updates |
| `.github/pull_request_template.md` | GitHub template, the default in tracked mode |
| `.agents/templates/pull_request_template.md` | Local drafting template, the default in local mode |

Codex uses `.agents/skills`. Claude Code uses the individual `.claude/skills` links; existing directories and unrelated entries are preserved. Pass `--agents codex` to omit new Claude links. Other agents can read these Markdown packages explicitly, but the installer does not claim to configure their native discovery or tool permissions.

The architecture skill automatically includes Builder because it shares the standard. PR writer retains the existing draft-only boundary: installation does not authorize creating, updating, or merging a PR. It respects the target repository's required title and template fields.

Choose a subset or template independently:

```sh
# Architecture includes its Builder dependency; omit new Claude aliases.
repo-bootstrap --repo ~/src/app --skills architecture --agents codex --pr-template none

# Keep an existing team PR template while sharing the skills.
repo-bootstrap --repo ~/src/app --mode tracked --pr-template none

# Keep a private drafting template alongside an existing GitHub template.
repo-bootstrap --repo ~/src/app --mode tracked --pr-template local
```

`--skills` accepts `builder`, `architecture`, and `pr-writer`, comma-separated. These are curated portable packages, not an automatic copy of every workstation-specific skill. The default selects all three. The source entrypoints live under `ai/skills`; installation bundles the existing writer roles and documentation without maintaining another copy of their policy in dotfiles.

GitHub only discovers committed templates on the repository's default branch. A local drafting template is not a GitHub default. The supplied template contains removable drafting prompts, without mandatory headings or checklists. Fill it with the change's outcome and motivation, then remove the comments before publishing.

When installing a GitHub template, alternate templates in the repository root, `docs`, or `.github` cause an explicit conflict, including multiple-template directories. Choose `--pr-template none` or `local` to retain the existing selection. An existing `.github/pull_request_template.md` uses the same conflict policy as other files.

## Update without losing repository edits

After updating dotfiles, rerun the command from that checkout:

```sh
repo-bootstrap --repo ~/src/app --dry-run
repo-bootstrap --repo ~/src/app
```

Reruns reuse the saved mode unless `--mode` is supplied. Unchanged managed files update automatically; files matching the new content are left alone. Any changed existing content fails the whole preflight by default, before installed files are written. No repository pulls, source downloads, or branch changes are implicit.

- `--conflict skip` updates independent files and reports preserved local edits. Skipped files are not marked as successfully updated.
- `--conflict replace` explicitly replaces conflicting regular files after saving their original contents under Git's `repo-bootstrap/backups/replace-*` directory. The command prints the backup location. It never replaces symlinks or directories; reconcile those manually.
- Selected skills and templates are **additive**. Selecting fewer skills, `--agents codex`, or `--pr-template none` does not uninstall earlier files. Files removed from an upstream package are also retained. Remove unwanted files deliberately after reviewing repository dependencies.

To make a local install shareable, use `--mode tracked` and review the new Git status. Only the installer's exclusion block is removed; unrelated ignore rules are preserved and still checked. Changing tracked content to local mode requires first deciding, separately, whether it should be removed from the Git index. No automatic untracking occurs.

The manifest records content hashes, not proof of origin or security. Keep it with the files it describes. Malformed manifests, linked destination directories, missing source resources, and conflicting templates fail closed. Dry runs create no repository files or Git metadata. Run one installer at a time while the destination is otherwise idle: preflight catches observed changes, but this is not a transaction against concurrent editors or processes. Files are replaced atomically one at a time; an I/O interruption can leave a partial install, which is reported as failure rather than completion.

## Verification

```sh
make test-repo-bootstrap
```

The single acceptance workflow exercises the real command: bootstrap and clone a tracked installation, resolve its local Markdown resources, run Builder's bundled examples, retrofit a linked worktree, preserve project policy, update unchanged resources, protect and explicitly replace local edits with backups, and verify effective Git exclusion and tracking behavior. It does not invoke an agent model or establish that every client version discovers or follows the instructions.
