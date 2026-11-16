# Using Builder

Builder is the shared software skill for Claude, Codex and other assistants. Its required `SKILL.md` core retains all twelve PHA requirement IDs, material applicability limits and construction safeguards. The full [Pragmatic Hexagonal Architecture](pragmatic-hexagonal-architecture.md) standard defines software properties; [Software construction](software-construction.md) supplies construction detail. Read those references for the task triggers in the core: boundary/model/adapter/consequential effect changes or architecture reviews, and uncertain feasibility/retained prototypes/manual-only protection/security or performance viability/verification-timing ambiguity, respectively. Neither installation checks nor a development sequence establishes compliance.

## Install and activate

Builder is project-scoped, alongside testing, comment, and language guidance. Install the versioned package with:

```sh
source-code setup --repo ~/src/project --stage alpha --go --mode shadow --pr-template none
```

Use tracked mode to share policy with a team. Shadow mode keeps installed files out of normal Git status. The project records its schema version, policy version, lifecycle stage, and installed languages in `.source-code.json`. Start a fresh session or reload the client's skill catalog after installation. See [source-code setup](repository-bootstrap.md) for stage transitions, packaging, conflict handling, and upgrades.

Default Claude, Codex, and Pi catalogs no longer advertise engineering standards, language guidance, or Git/PR workflow skills. These and their code-specific planning, testing, and review context load from selected project bundles. The [project-only manifest](../ai/skills/project-only.json) owns that exclusion. Normal setup removes known managed default links and Builder guidance while retaining unrelated personal skills, aliases, and instructions. Existing explicit package references remain readable at `~/.local/share/software-standards/builder`; their presence does not activate the policy globally.

The canonical package source remains `ai/skills/builder/`. Project installation copies complete skills and supporting references, so a clone can use them without the dotfiles checkout. Readable files and catalog discovery do not establish model adherence. The installer's legacy manifest and exclusion-marker names remain compatible with `repo-bootstrap`.

## Apply and review

Begin with a steel thread: one narrow path from the real entrypoint through the necessary decisions and integration boundaries to an observable result. Choose a representative input and expected outcome, connect that path and exercise it before broadening the capability. The [Builder guide](builder.mdx) explains the approach with a document-import example.

TDD is optional; verification is not. Keep early testing light: start with a representative happy-path check through the steel thread, adding failure and boundary checks when they affect safety, feasibility or the credibility of the result. Introduce unit tests when isolating stable decisions improves protection or diagnosis. Use a credible experiment for uncertain feasibility. Name substituted boundaries and remaining gaps rather than claiming the complete path is verified. Once meaningful behavior will be retained, protect it before substantial expansion or material restructuring. Plan working-and-verifying increments rather than separate implementation and testing phases. This does not waive delivery gates or explicit project mandates.

When writing implementation-agent briefs, direct loading of the Builder core and task-relevant detail. Explicit user or project test-first requirements still govern that work.

Apply the architecture standard to consequential claims, conditions,
contradictory evidence, and interpretation limits. Use existing software
artifacts and the smallest supporting architecture. Reviews identify requirement
violations, affected behavior, supporting evidence, and gaps. Assess protection
of retained behavior, not whether tests were authored first, except where the
project explicitly requires test-first development.

Follow each host's documented instruction precedence and applicable project constraints.
Record material architecture deviations using the standard's exception format.
Project lifecycle selection does not waive existing repository requirements. Trivial changes require no architecture report.

## Verify distinct concerns

```sh
make test-pragmatic-hexagonal  # Reference behavior and isolated controlled defects
python3 -m pytest -q bin/codex-skills-sync_test.py  # Managed default retirement and preservation
make test-setup               # Default setup and partial-progress behavior
make lint                    # Explicit instruction and skill checks
```

Example checks establish exercised claims and detector sensitivity.
The simulated provider cannot establish real provider behavior or future software compliance.
Installation checks establish placement, migration, and readable references, not
assistant adherence. The migration fixture represents the previous filesystem
layout; it is not a live assistant session.

For a loading check, start a fresh session outside dotfiles. Use an ordinary small software task and a boundary/effect task; inspect reads to confirm the selected core is loaded once and detailed references are loaded by their triggers. Check distinctions between solution properties and construction procedure, retained-behavior protection, unknown outcomes, and supported verification claims. A read-only exercise checks behavior in those scenarios; it cannot establish reliable future adherence or measure all host-injected context.

Global Codex instructions keep essential triggers and safeguards in `codex/AGENTS.md`; workflow detail remains binding in [agent operating procedures](agent-operating-procedures.md). Full Codex setup regenerates its global file, so edit canonical sources rather than the installed file. Preserve personal additions before regeneration. Logistics Services separately checks measured `o200k_base` startup/task reading, including its core and declared required references. File-text counts exclude catalogs, host prompts, tools and history.

### Historical loading evidence — before the Builder rename

On 2026-10-18, Codex 0.163.0 discovered and loaded the earlier
`pragmatic-hexagonal` skill and architecture standard outside dotfiles.
The shared installer also completed repeatedly in the live home; both assistants'
links resolved to the same installed copy. Claude 2.1.295 discovered the earlier
skill metadata, then reported “Not logged in” before model or tool reads.
Authentication remained unchanged.

Those observations predate Builder and `construction.md`. They do not establish
loading of the renamed skill or the new construction policy. At that update, a fresh live Codex/Claude loading check remained required; its execution environment had neither runtime, Anthropic skill-creator, nor independent writer/reviewer delegation. These historical observations do not establish loading of the later compact core.

## Official integration references

- [Codex instruction discovery and precedence](https://developers.openai.com/codex/guides/agents-md)
- [Codex skill discovery and loading](https://developers.openai.com/codex/skills)
- [Codex configuration basics](https://developers.openai.com/codex/config-basic)
- [Claude memory and global rules](https://code.claude.com/docs/en/memory)
