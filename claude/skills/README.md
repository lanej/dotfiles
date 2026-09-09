# Claude Code Skills

Modular instruction sets that extend Claude with domain-specific expertise. Each skill is a directory containing `SKILL.md` — YAML frontmatter (`name`, `description`) plus the instruction body — and optionally `references/`, `scripts/`, and `assets/`.

The `description` field is the triggering mechanism: Claude loads a skill when the request matches it, so all "when to use" information belongs there rather than in the body.

## Languages

| Skill | What it covers |
|-------|---------------|
| **go/** | gotestsum for tests, standard tooling, idiomatic patterns |
| **javascript/** | Node.js patterns, gotchas, library compatibility notes |
| **python/** | uv for project management, script execution, dependency handling |
| **rust/** | cargo check-first workflow, clippy, test patterns |

## Data & Analytics

| Skill | What it covers |
|-------|---------------|
| **data-pipeline/** | Medallion/three-layer architecture and pipeline design patterns |
| **duckdb/** | Local SQL analytics over CSV/JSON/Parquet, Python API, `.duckdb` files |
| **jq/** | JSON filtering, transformation, aggregation — preferred for all JSON work |
| **matplotlib/** | Figure engineering, gotchas, reusable helpers |
| **xlsx/** | `xlsx` binary — viewing, SQL-like filtering, cell editing |
| **xlsx-python/** | openpyxl/xlsxwriter for formulas, formatting, generated workbooks |
| **xsv/** | Fast CSV — select, filter, join, sort, statistics |

## Documents & Presentations

| Skill | What it covers |
|-------|---------------|
| **docx/** | Word documents — creation, editing, tracked changes, comments |
| **pdf/** | Extraction, merging, splitting, forms, OCR |
| **pptx/** | PowerPoint creation, editing, and analysis |
| **presenterm/** | Terminal presentations from markdown, with themes and code execution |
| **qmd-math/** | Math notation for Quarto/EPQ documents rendered via lualatex |
| **quarto/** | Computational documents → markdown (default), PDF, HTML, Word, slides |

## Design & Frontend

| Skill | What it covers |
|-------|---------------|
| **algorithmic-art/** | p5.js generative art with seeded randomness, parameter exploration |
| **brand-guidelines/** | Anthropic brand colors and typography |
| **canvas-design/** | Visual art in PNG/PDF using design philosophy |
| **frontend-design/** | Distinctive, production-grade interfaces |
| **theme-factory/** | Theming for slides, docs, reports, HTML artifacts |
| **web-artifacts-builder/** | Multi-component claude.ai HTML artifacts |

## Cloud & Infrastructure

| Skill | What it covers |
|-------|---------------|
| **az/** | Azure CLI — resources, DevOps, VMs, storage, networking |
| **gcp/** | GCP infra — IAM roles, Cloud Run deploys, Vertex AI quirks |
| **github-actions/** | Deploying to GCP — Workload Identity Federation, keyless OIDC |

## Communication & Writing

| Skill | What it covers |
|-------|---------------|
| **distill/** | Reduce a document to its minimum effective dose |
| **doc-coauthoring/** | Structured workflow for co-authoring documentation |
| **internal-comms/** | Internal communications in Josh's established formats |
| **josh-email-voice/** | Email drafting as Josh Lane (CTO, EasyPost) |
| **org-announce/** | Org-wide announcements — reporting changes, promotions, departures |
| **slack-gif-creator/** | Animated GIFs within Slack's constraints |
| **trim/** | Cut redundancy from prose — READMEs, design docs, notes |

## Claude, AI & Tooling

| Skill | What it covers |
|-------|---------------|
| **claude-cli/** | `claude` CLI — interactive sessions, print mode, MCP server management |
| **claude-tail/** | Session log viewing with colors, filtering, live following |
| **mcp-builder/** | Building high-quality MCP servers |
| **research/** | Delegating research to a sub-agent to protect the primary context |
| **skill-creator/** | Creating, iterating on, and validating skills |

## Workflow & Process

| Skill | What it covers |
|-------|---------------|
| **bugfix-dispatcher/** | Operating protocol for a bug/feature-fix dispatcher session |
| **git/** | Commits, branches, pull requests, code review workflows |
| **just/** | Justfile recipes for task automation — preferred over Make |
| **methodology/** | Phased execution and visual communication standards |
| **operating-lessons/** | Sub-agent output trust, verification, delegation discipline |
| **project-bootstrap/** | New-project setup — git, constitution, pre-commit hooks, codegen |
| **report-tool-work/** | Filing bugs/features against Josh's easypost-sandbox tool repos |
| **webapp-testing/** | Playwright-driven testing of local web apps |

## Adding a Skill

Use the `skill-creator` skill — it scaffolds the directory, enforces frontmatter conventions, and validates the result:

```bash
claude/skills/skill-creator/scripts/init_skill.py <name> --path claude/skills/
claude/skills/skill-creator/scripts/quick_validate.py claude/skills/<name>
```

Then add a row to the table above and force-add the files — `claude/skills/*` is gitignored by default so that machine-specific symlinked skills stay out of version control:

```bash
git add -f claude/skills/<name>
```

Packaging (`package_skill.py`) is only for distributing a skill to other people; skills used locally live as directories and need no `.skill` archive.

## Machine-Local Skills

`problem-definition-contract/SKILL.md` is a symlink to a path outside this repo and resolves only on Josh's machine, so it is deliberately absent from the index above. EP-specific skills live in `~/src/ep-dotfiles` — run `make link-skills` there to symlink them into `~/.files/claude/skills/`.
