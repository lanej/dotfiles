# Commands

Invoked with `/command-name` or `/subdir/command-name`.

## Core Primitives

| Command | Description |
|---------|-------------|
| `/continue` | Execute autonomously without prompting — make decisions, install deps, fix issues, run tests |
| `/delegate` | Route work to specialized sub-agents to protect context window |
| `/team-leader` | Decompose a task into parallel sub-problems, orchestrate agents, synthesize output |
| `/think` | Deep epistemological analysis using Quarto for structured reasoning |
| `/think-harder` | Multi-dimensional deep analysis: decomposition, causal mapping, trade-off synthesis |
| `/think-ultra` | Ultra-comprehensive 7-phase analysis for the most complex problems |
| `/verify` | Validate execution results against a Socrates validation contract |
| `/regression` | Add regression protection by writing tests for current functionality |
| `/pr-prep` | Review implementation, restructure commits into narrative, generate PR description |
| `/write-minimal` | Radical brevity — extract the core message and cut 50% |
| `/compose` | Full document lifecycle: Socratic interrogation → research → draft → critique → revision |
| `/name` | Generate and register a short descriptive name for the current session |
| `/prep` | Pull today's calendar and create a comprehensive meeting prep document |

## spec/ — Specification & Planning Pipeline

Run in sequence for any non-trivial task: `socrates` → `specify` → `critique` → `shape`.

| Command | Description |
|---------|-------------|
| `/spec/bootstrap` | Complete project setup: install speckit, create constitution from universal best practices |
| `/spec/socrates` | Interrogate a task via Socratic dialogue to produce a validated, execution-ready spec |
| `/spec/specify` | Compile ambiguous intent into a validated execution-ready specification |
| `/spec/critique` | Run adversarial critique passes against a specification to surface gaps and risks |
| `/spec/shape` | Full pipeline: Specify → Critique → Reconcile → Freeze → Plan → Verify |

## memory/ — Knowledge & Learning Capture

| Command | Description |
|---------|-------------|
| `/memory/remember` | Persist user preferences, patterns, and project conventions to session memory |
| `/memory/reflection` | Analyze session behavior against CLAUDE.md and apply improvements (also runs auto on plan mode entry) |
| `/memory/reflection-harder` | Comprehensive session analysis and learning capture across 8 categories |
| `/memory/eureka` | Document technical breakthroughs, performance wins, and insights as reusable knowledge assets |
| `/memory/stahp` | Capture dead-ends and failed approaches to prevent repeating mistakes |

## Domain-Specific

| Command | Description |
|---------|-------------|
| `/dotfiles/sync` | Sync dotfiles to home directory |
| `/gcp/privacy-check` | Run a fresh Vertex AI privacy check, bypassing cache |
| `/gh/fix-issue` | Fix a GitHub issue end-to-end |
| `/gh/fix-all-issues` | Fix all open GitHub issues on the current repo |
| `/gh/review-pr` | Review a pull request |
| `/git/commit` | Stage and commit with a generated Commitizen-format message |
| `/git/review-commit` | Review staged changes before committing |
| `/git/worktree` | Manage git worktrees for parallel development |
| `/package-mgmt/uv` | Python package management workflows using uv |
| `/testing/pytest-shell` | Pytest integration for shell command testing |

## speckit/ — Speckit Framework

Speckit commands operate on `.specify/` artifacts (spec.md, plan.md, tasks.md) in the current repo.

| Command | Description |
|---------|-------------|
| `/speckit/specify` | Create or update feature spec from a natural language description |
| `/speckit/clarify` | Ask targeted clarification questions to resolve underspecified areas |
| `/speckit/plan` | Generate implementation plan design artifacts |
| `/speckit/tasks` | Generate dependency-ordered tasks.md from design artifacts |
| `/speckit/analyze` | Cross-artifact consistency check — read-only, surfaces gaps before implementation |
| `/speckit/checklist` | Generate a custom verification checklist for the current feature |
| `/speckit/implement` | Execute the implementation plan by processing tasks.md |
| `/speckit/autoimplement` | Fully autonomous implementation — no prompts between phases |
| `/speckit/continue` | Resume a paused speckit implementation |
| `/speckit/constitution` | Create or update the project constitution |
