---
name: project-bootstrap
description: "Set up a new project from scratch — git initialization, a project constitution capturing its non-negotiable principles, language-specific pre-commit hooks, justfile automation, and quality gates. Also covers generating typed API clients from a spec (TypeSpec/OpenAPI → Progenitor for Rust, Ogen for Go). Use when: (1) starting a new repo ('bootstrap this project', 'set up a new Rust/Go/TypeScript/Python project', 'scaffold a new service'); (2) adding pre-commit hooks or quality gates to an existing repo ('add pre-commit hooks', 'set up format/lint/test gates'); (3) writing a project constitution or set of engineering principles ('write a constitution for this project', 'what principles should this project follow'); (4) generating a client from an API contract ('generate a Rust client from this OpenAPI spec', 'contract-driven codegen', 'TypeSpec')."
---

# Project Bootstrap

Complete setup for a new project: git, constitution, pre-commit hooks, and automation. Work through the steps in order; skip any that already apply to the repo.

## Step 1: Initialize Git

Check first — `git rev-parse --git-dir 2>/dev/null`. If it fails, run `git init` and create a language-appropriate `.gitignore`.

## Step 2: Gather Project Context

Ask the user these before writing anything. The answers determine which principles, hooks, and gates apply.

1. **Project type** — library, CLI tool, server (API/MCP/web), data pipeline, or infrastructure.
2. **Language** — Rust, Go, TypeScript, Python, etc.
3. **API integration** — does it call external APIs? Are OpenAPI specs or protobuf definitions available? Can auth be delegated to a trusted system (gcloud, OAuth providers)?
4. **Criticality** — correctness-critical (financial, medical, legal), performance-critical (real-time, high-throughput), or standard.
5. **Interface model** — single (library, CLI, server) or multiple (CLI + MCP, CLI + library).
6. **Security** — handles sensitive data? requires audit logging?

Don't ask all six as one wall of questions. Lead with project type and language; follow up as the answers narrow things.

## Step 3: Write the Constitution

Synthesize a constitution from the context answers: select 4–6 universal principles plus 1–3 domain-specific ones, then fill in the structure template. Write it to `CONSTITUTION.md` at the repo root (or `docs/CONSTITUTION.md` if the repo keeps docs separate).

See [references/constitution.md](references/constitution.md) for the principle catalog, domain-specific additions, anti-patterns, the full structure template, and the governance/amendment sections.

A constitution earns its place only if it constrains real decisions. Prefer 4 principles the project will actually enforce over 10 aspirational ones.

## Step 4: Install Pre-Commit Hooks

Write `.git/hooks/pre-commit` and `chmod +x` it. Hooks must stay fast — format, lint, and unit tests only, under ~5 seconds total. Integration tests belong in CI, not in a commit hook.

See [references/precommit-hooks.md](references/precommit-hooks.md) for ready-to-use hook scripts for Rust, Go, TypeScript, and Python.

## Step 5: Set Up Justfile Automation

```justfile
test:
    [test-command]        # cargo test, go test ./..., npm test, pytest

fmt:
    [format-command]      # cargo fmt, gofmt -w ., prettier --write ., ruff format .

lint:
    [lint-command]        # cargo clippy -- -D warnings, go vet ./..., eslint ., ruff check .

build:
    [build-command]       # cargo build --release, go build ./..., npm run build

check-deps:
    [deps-command]        # cargo outdated, go list -m -u all, npm outdated

generate:
    [generate-command]    # if the project does codegen — see references/contract-codegen.md

pre-commit:
    just fmt && just lint && just test
```

## Step 6: Define Quality Gates

**Pre-commit**: format passes, lint passes with zero warnings, fast unit tests pass, build succeeds without warnings.

**Pre-release**: all pre-commit gates, plus full test suite (unit + integration), benchmark validation if performance-critical, updated README/CHANGELOG, and a clean security audit.

## Contract-Driven Projects

If the project integrates with an external API that publishes a spec, generate the client rather than hand-writing it — the generated client stays correct as the upstream spec moves. See [references/contract-codegen.md](references/contract-codegen.md) for the TypeSpec → OpenAPI → Progenitor/Ogen pipeline, spec overlay merging, and post-processing.
