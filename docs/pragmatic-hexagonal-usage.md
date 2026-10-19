# Using Pragmatic Hexagonal Architecture

Pragmatic Hexagonal Architecture is the default for ordinary Codex software work.
Global guidance requires loading its skill and standard before design, implementation, modification, debugging, or review.
The standard governs software properties; installation and test results establish different facts.

## Install and activate

Run from this checkout:

```sh
make codex-config
```

This target installs global guidance and depends on skill installation.
Default `make` includes the same target and preserves partial setup progress.
Setup remains separate from linting, architecture review, and example verification.
Start a fresh Codex session after installation.

Global guidance installs at `~/.codex/AGENTS.md`.
The skill installs at `~/.agents/skills/dotfiles/pragmatic-hexagonal` through the shared synchronizer.
The installer currently targets the default home locations.
A custom `CODEX_HOME` needs global guidance installed into that configuration directory separately.
Do not assume changing `CODEX_HOME` redirects this installer.

The canonical specification is `ai/skills/pragmatic-hexagonal/references/standard.md`.
[The documentation entrypoint](pragmatic-hexagonal-architecture.md) symlinks to that single source.
The skill packages its standard and examples using relative references.
Copy the complete skill directory when installing elsewhere; copying `SKILL.md` alone is insufficient.

## Apply and review

Identify consequential claims, their conditions, contradictory evidence, and interpretation limits.
Use existing contracts, types, examples, tests, return values, or runtime mechanisms.
Choose the smallest architecture preserving the required properties.
Reviews report specific violations, affected behavior, and supporting evidence.
Separate established facts, assumptions, and verification gaps.
Trivial changes require no architecture report.

Codex combines global guidance with closer project instructions using documented precedence.
Global `AGENTS.override.md` can replace global `AGENTS.md`; closer project instructions can refine or override guidance.
Record material deviations using the standard's exception format.
These defaults do not technically override every repository instruction.

## Verify distinct concerns

```sh
make test-pragmatic-hexagonal  # Reference behavior and isolated controlled defects
make test-setup                # Installation workflow and partial-progress behavior
make lint                      # Explicit instruction and skill checks
```

Example checks establish only their exercised claims and detector sensitivity.
Their simulated provider cannot establish real provider behavior or future software compliance.
Installation checks establish placement and references; placement alone does not establish discovery.

Codex 0.163.0 exposes a prompt-rendering smoke test:

```sh
cd /tmp
codex debug prompt-input 'Describe the default software architecture guidance.'
```

Inspect the rendered prompt for global guidance and the installed skill's metadata.
Use an unrelated working directory to exclude this repository's project instructions.
An isolated-home run must install global guidance and skills into that temporary home.
Prompt rendering verifies discovery context, not the complete standard's actual loading or future adherence.

An optional bounded `codex exec --ephemeral --json` task can request read-only loading.
Inspect its tool activity for reads of both `SKILL.md` and `references/standard.md`.
Use the real unchanged authentication configuration; temporary homes also need discovered global skills.
Do not change authentication, providers, permissions, or sandbox settings for this check.
The installed Anthropic authoring workflow is unavailable; report that validation limit separately.

## Observed loading check

On 2026-10-18, Codex CLI 0.163.0 rendered the installed global guidance and
exactly one skill catalog entry using a temporary home outside dotfiles.
A bounded read-only Codex task then read both the installed `SKILL.md` and full
standard successfully and identified PHA-P03 in the timeout scenario.
This was a loading and one-scenario smoke check, not a general adherence study.
The reference provider remains simulated. Temporary authentication/configuration
copies used the existing settings and were removed after the smoke check.

## Official integration references

- [Instruction discovery and precedence](https://developers.openai.com/codex/guides/agents-md)
- [Skill discovery and loading](https://developers.openai.com/codex/skills)
- [Configuration basics](https://developers.openai.com/codex/config-basic)
