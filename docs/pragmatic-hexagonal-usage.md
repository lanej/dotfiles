# Using Pragmatic Hexagonal Architecture

Install one shared standard for Claude, Codex, and other software assistants.
It governs software properties; installation checks establish different facts.

## Install and activate

Run from this checkout:

```sh
make software-standard
```

Default `make`, Claude setup, and Codex setup include this installation.
Setup remains separate from linting, architecture review, and example verification.
Start fresh assistant sessions after installation.

The installer copies the complete package to
`~/.local/share/software-standards/pragmatic-hexagonal`.
It remains readable after temporary checkouts disappear.
Any assistant can read its `SKILL.md` and `references/standard.md` directly.

Claude loads the shared instructions through
`~/.claude/rules/pragmatic-hexagonal.md`.
Codex global `~/.codex/AGENTS.md` directs loading of those same instructions.
Skill links expose the package at `~/.claude/skills/pragmatic-hexagonal` and
`~/.agents/skills/dotfiles/pragmatic-hexagonal`.
Other assistants need their own instruction entrypoint to load the shared files.
Readable files alone do not establish automatic discovery.

The standalone installer preserves unrelated global guidance.
The existing full `codex-config` target still regenerates its managed global file
from repository sources and `codex/AGENTS.local.md`.
Linked Claude skills or rules directories must be migrated before standalone installation.
It targets default home locations; custom configuration homes require explicit integration.
Changing `CODEX_HOME` does not redirect this installer.

The canonical source is `ai/skills/pragmatic-hexagonal/references/standard.md`.
[The documentation entrypoint](pragmatic-hexagonal-architecture.md) symlinks to that source.
Copy the complete package when installing elsewhere; `SKILL.md` alone is insufficient.

## Apply and review

Identify consequential claims, conditions, contradictory evidence, and interpretation limits.
Use existing software artifacts and the smallest supporting architecture.
Reviews identify requirement violations, affected behavior, and supporting evidence.
Separate established facts, assumptions, and verification gaps.
Trivial changes require no architecture report.

Follow each host's documented instruction precedence and applicable project constraints.
Record material deviations using the standard's exception format.
Codex global `AGENTS.override.md` replaces global `AGENTS.md`; project instructions can override global defaults.
Shared defaults do not technically override every repository instruction.

## Verify distinct concerns

```sh
make test-pragmatic-hexagonal  # Reference behavior and isolated controlled defects
make test-setup                # Installation workflow and partial-progress behavior
make lint                      # Explicit instruction and skill checks
```

Example checks establish exercised claims and detector sensitivity.
The simulated provider cannot establish real provider behavior or future software compliance.
Installation checks establish placement and readable references, not assistant adherence.

For Codex discovery, run from an unrelated directory:

```sh
codex debug prompt-input 'Describe the default software architecture guidance.'
```

Inspect the rendered prompt for global guidance and skill metadata.
A bounded read-only task can establish actual package loading through its tool activity.
Check reads of the shared instructions, `SKILL.md`, and `references/standard.md`.
For Claude, inspect loaded rules using `/memory`, then request read-only loading.
These checks establish discovery or loading within that session, not future adherence.

### Observed shared installation

The shared installer completed twice in the live home.
Both assistants' skill links resolve to the same installed copy.
Claude's global rule and Codex's global guidance reference that package.
The package contains no symlinks back to the checkout.
Installed versions are Codex 0.163.0 and Claude 2.1.295.
Codex rendered global guidance and exactly one skill entry outside dotfiles.
A separate read-only task loaded shared instructions, skill, and the complete standard.
Its successful command outputs confirmed those reads; it correctly identified PHA-P03.

Claude's initialization catalog included `pragmatic-hexagonal`.
The session then reported “Not logged in” before model or tool reads.
Claude metadata discovery passed; full loading remains unverified.
Authentication remained unchanged. These checks do not establish future adherence.

### Previous Codex 0.163.0 smoke check

On 2026-10-18, the earlier Codex-only installation passed a temporary-home discovery check.
A bounded read-only task loaded its skill and complete standard outside dotfiles.
It identified PHA-P03 in the timeout scenario.
That result does not establish discovery through the new shared installation.
The installed Anthropic authoring workflow was unavailable during that earlier validation.

## Official integration references

- [Codex instruction discovery and precedence](https://developers.openai.com/codex/guides/agents-md)
- [Codex skill discovery and loading](https://developers.openai.com/codex/skills)
- [Codex configuration basics](https://developers.openai.com/codex/config-basic)
- [Claude memory and global rules](https://code.claude.com/docs/en/memory)
