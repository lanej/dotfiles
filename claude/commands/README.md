# Claude Commands

Slash commands available in Claude Code. Top-level commands are invoked as `/name`; grouped ones as `/group/name`.

## Top-Level Primitives

The commands reached for often enough that a group prefix would only add friction.

| Command | Purpose |
|---------|---------|
| `/compose` | Orchestrate the full document lifecycle — interrogation → draft → review |
| `/continue` | Execute autonomously without prompting; make decisions and keep going |
| `/delegate` | Routing reference for shedding a sub-task while you keep driving |
| `/goal-prep` | Draft a tight, verifiable condition string for the built-in `/goal` |
| `/handoff` | Hand the remaining work of a spent session to a fresh sub-agent |
| `/name` | Generate and register a short descriptive name for this session |
| `/pick-model` | Pre-flight model recommendation for a described task |
| `/pr-prep` | Prepare a branch for PR — review implementation, verify requirements |
| `/prep` | Daily meeting prep |
| `/regression` | Add regression protection by writing tests for current behavior |
| `/think` | Deep epistemological analysis using Quarto for structured reasoning |
| `/think-harder` | Structured decomposition for complex problems |
| `/think-ultra` | Ultra-comprehensive analysis for the hardest problems |
| `/verify` | Verify execution results against a validation contract |
| `/write-minimal` | Write with radical brevity |

## `/spec/` — Specification & Critique

Turning ambiguous intent into something executable, and attacking it before it ships.

| Command | Purpose |
|---------|---------|
| `/spec/critique` | Run adversarial critique passes against a specification |
| `/spec/shape` | Semantic alignment workflow from specification through validation |
| `/spec/socrates` | Interrogate a task through Socratic dialogue to produce a validated spec |
| `/spec/specify` | Compile ambiguous intent into an execution-ready specification |

## `/memory/` — Session Knowledge

Capturing what a session learned so the next one doesn't relearn it.

| Command | Purpose |
|---------|---------|
| `/memory/eureka` | Document breakthroughs, performance wins, debugging insights |
| `/memory/reflection` | Analyze session behavior against CLAUDE.md and apply improvements |
| `/memory/reflection-harder` | Comprehensive session analysis and learning capture |
| `/memory/remember` | Persist user preferences, patterns, and project conventions |
| `/memory/stahp` | Capture dead-ends and failed approaches to prevent repeats |

## `/git/` — Version Control

| Command | Purpose |
|---------|---------|
| `/git/commit` | Create a commit using the commit-message-generator agent |
| `/git/review-commit` | Review staged changes for quality before committing |
| `/git/worktree` | Create a git worktree with automatic naming |

## `/gh/` — GitHub

| Command | Purpose |
|---------|---------|
| `/gh/fix-all-issues` | Work through all open issues |
| `/gh/fix-issue` | Fix a single issue (lists issues if no number given) |
| `/gh/review-pr` | Comprehensive PR review with quality analysis |

## `/gcp/` — Google Cloud

| Command | Purpose |
|---------|---------|
| `/gcp/privacy-check` | Scan for PII or sensitive data before upload |

## `/dotfiles/` — This Repo

| Command | Purpose |
|---------|---------|
| `/dotfiles/sync` | Update dotfile configurations and sync across systems |

## `/package-mgmt/` — Dependencies

| Command | Purpose |
|---------|---------|
| `/package-mgmt/uv` | Manage Python dependencies with uv |

## `/testing/` — Test Authoring

| Command | Purpose |
|---------|---------|
| `/testing/pytest-shell` | Generate pytest tests for shell scripts with dependency injection |

## Versioning

`claude/commands/` is selectively versioned — see the repo root `CLAUDE.md`. Experiment freely in `~/.claude/commands/` (symlinked here, gitignored), then force-add a command once it earns its keep:

```bash
git add -f claude/commands/path/to/command.md
```
