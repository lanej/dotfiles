# Using Builder

Builder is the shared software skill for Claude, Codex, and other assistants.
It loads two distinct documents: [Pragmatic Hexagonal Architecture](pragmatic-hexagonal-architecture.md)
defines properties of the resulting software; [Software construction](software-construction.md)
defines the working-and-verifying approach. Neither installation checks nor a
particular development sequence establishes architecture compliance.

## Install and activate

Run from this checkout:

```sh
make software-standard
```

Default `make`, Claude setup, and Codex setup include this installation.
Setup remains separate from linting, architecture review, and example verification.
Start fresh assistant sessions after installation.

The installer copies the complete package to
`~/.local/share/software-standards/builder`.
It remains readable after temporary checkouts disappear.
Any assistant can read its `SKILL.md`, `references/standard.md`, and
`references/construction.md` directly.

Claude loads the shared instructions through `~/.claude/rules/builder.md`.
Codex global `~/.codex/AGENTS.md` explicitly directs loading of those same
instructions; activation does not depend only on optional skill selection.
Skill links expose the package at `~/.claude/skills/builder` and
`~/.agents/skills/dotfiles/builder`.
Other assistants need their own instruction entrypoint to load the shared files.
Readable files alone do not establish automatic discovery.

The standalone installer preserves unrelated global guidance. It migrates the
previous managed `pragmatic-hexagonal` instruction block, skill links, rule, and
package to Builder. Unrelated local entries are preserved and reported rather
than deleted. Conflicting or malformed managed blocks are rejected before
installation. All required references, including `construction.md`, must be
present before the installed package is replaced. Missing package source is a
failure, not a successful skip. Ordinary setup reports Builder as incomplete and
continues independent tasks; restore the source and rerun setup to finish.

The former package address remains as a relative link to `builder`, so custom
aliases to that package or its reference files follow the current installation,
including aliases inside external skill trees. Canonical old skill/rule entries
are removed; no second copy of the standard is retained. If a legacy resource
cannot be forwarded without disappearing or changing kind, installation stops
before changing existing files and identifies the resource for manual review.
Runtime Python caches are excluded from this compatibility check.

The existing full `codex-config` target still regenerates its managed global file
from repository sources and `codex/AGENTS.local.md`.
Recognized `~/.claude/skills` directory links to this checkout's `ai/skills`
or `claude/skills` are migrated to individual links before installation.
Source entries and external skill targets are left intact. Unrelated skill
trees and linked rules directories remain protected and require explicit migration.
The installer targets default home locations; custom configuration homes require
explicit integration. Changing `CODEX_HOME` does not redirect this installer.

The canonical package source is `ai/skills/builder/`. Documentation entrypoints
symlink to its architecture and construction references; they are not duplicate
standards. Copy the complete package when installing elsewhere; `SKILL.md` alone
is insufficient.

## Apply and review

First make the smallest meaningful behavior work, not the whole system.
TDD is optional; verification is not. Choose an early test for clear requirements
or a credible experiment for uncertain feasibility. Once meaningful behavior
will be retained, protect it before expanding or materially restructuring it.
Plan working-and-verifying increments rather than separate implementation and
testing phases. This does not waive delivery gates or explicit project mandates.
Implementation-agent briefs direct loading of Builder and its two references,
not a blanket test-first sequence. Explicit user or project test-first
requirements still govern that work.

Apply the architecture standard to consequential claims, conditions,
contradictory evidence, and interpretation limits. Use existing software
artifacts and the smallest supporting architecture. Reviews identify requirement
violations, affected behavior, supporting evidence, and gaps. Assess protection
of retained behavior, not whether tests were authored first, except where the
project explicitly requires test-first development.

Follow each host's documented instruction precedence and applicable project constraints.
Record material architecture deviations using the standard's exception format.
Codex global `AGENTS.override.md` replaces global `AGENTS.md`; project instructions
can override global defaults. Shared defaults do not technically override every
repository instruction. Trivial changes require no architecture report.

## Verify distinct concerns

```sh
make test-pragmatic-hexagonal  # Reference behavior and isolated controlled defects
python3 -m pytest -q bin/codex-skills-sync_test.py  # Package install and migration
make test-setup               # Default setup and partial-progress behavior
make lint                    # Explicit instruction and skill checks
```

Example checks establish exercised claims and detector sensitivity.
The simulated provider cannot establish real provider behavior or future software compliance.
Installation checks establish placement, migration, and readable references, not
assistant adherence. The migration fixture represents the previous filesystem
layout; it is not a live assistant session.

For a loading check, start a fresh session from a directory outside dotfiles and
ask the assistant to load Builder's skill, architecture standard, and construction
policy. Inspect actual tool reads of all three files and the shared instructions.
Check that the assistant distinguishes solution properties from construction
procedure and describes when retained behavior gains repeatable protection.
A read-only response can demonstrate loading in that session, not reliable
adherence in future implementation work.

### Historical loading evidence — before the Builder rename

On 2026-10-18, Codex 0.163.0 discovered and loaded the earlier
`pragmatic-hexagonal` skill and architecture standard outside dotfiles.
The shared installer also completed repeatedly in the live home; both assistants'
links resolved to the same installed copy. Claude 2.1.295 discovered the earlier
skill metadata, then reported “Not logged in” before model or tool reads.
Authentication remained unchanged.

Those observations predate Builder and `construction.md`. They do not establish
loading of the renamed skill or the new construction policy. A fresh live
Codex/Claude loading check is still required; this update's execution environment
has neither runtime. The Anthropic skill-creator workflow and independent
PR-writer/reviewer delegation are also unavailable in that environment.

## Official integration references

- [Codex instruction discovery and precedence](https://developers.openai.com/codex/guides/agents-md)
- [Codex skill discovery and loading](https://developers.openai.com/codex/skills)
- [Codex configuration basics](https://developers.openai.com/codex/config-basic)
- [Claude memory and global rules](https://code.claude.com/docs/en/memory)
