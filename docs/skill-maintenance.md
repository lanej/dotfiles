# Maintaining skills and agent instructions

Follow the testing policy in [AGENTS.md](../AGENTS.md): one regression detector
per user-visible feature. It applies to repo-owned skills, commands, agents,
and supporting scripts and references. Existing user instructions and
authorization remain authoritative.

## Authoring

For a substantive change to instructional behavior, load the enabled Anthropic
**skill-creator:skill-creator** through the runtime's installed catalog. Use the
parts of its authoring guidance relevant to the change, within the owner's
one-detector policy. The older repo-owned `claude/skills/skill-creator` is not a
substitute merely because its name matches. Do not edit plugin caches or update
installed plugins as a side effect. If the workflow is unavailable, report the
validation limit without claiming it was followed.

Routine configuration, documentation, and small script maintenance do not
require an authoring workflow, paired model evaluation, or evidence bundle.
Review the diff, check syntax where applicable, and run the affected feature's
existing detector. Improve that detector when repairing a regression rather
than adding a test for each helper or input variant.

A detector should exercise a representative user outcome. For instruction
changes, that may be one realistic dialogue or task; source-string assertions
cannot establish agent behavior. Keep its fixtures small and use the same
scenario to assess the correction. Report simulated or mocked boundaries.

Describe validation in the PR. Do not generate source snapshots, hash receipts,
baseline/candidate/review narratives, or new evaluation directories for routine
maintenance. Git already retains prior source versions. Broader behavioral
studies and their supporting artifacts require an explicit owner request.

## Entrypoint size budget

CI checks tracked `SKILL.md`, `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` files at
any depth, plus Markdown entrypoints under `claude/commands/` and
`claude/agents/`, against **500 lines and approximately 4,000 tokens**. Symlinks
are skipped in the source scan; the installed scan follows them. The installed
`claude/CONSTITUTION.md` import is also covered in both scans. The estimate is
`ceil(UTF-8 bytes / 4)`, not a Claude tokenizer count.
The Bash checker uses `wc -l` and `wc -c`, including a final unterminated line.
It needs Git, standard Unix tools, and the same `jq` already used by setup.

Default `make` checks both the repository instructions (meta) and the installed
instructions (applied) after setup finishes. Installed coverage matches the
Makefile's destinations: `~/.claude/CLAUDE.md`, `~/.claude/CONSTITUTION.md`,
`~/.claude/{commands,agents,skills}`, and `~/.gemini/skills`. It follows file and
directory symlinks, includes local untracked additions in those trees, and
reports source and installed results separately. Absent destinations are
skipped; broken links or unreadable instructions fail the check.

Each limit is the larger of that budget and the file's size on the PR base.
Existing overages may stay the same size or shrink; new entrypoints must meet
both limits. This does not require rewriting existing vendored skills.
Installed files use their corresponding repository source's base size and
override. Local additions or external symlink targets without a regular tracked
source use the default limits. Default `make` compares against `HEAD`; use
`make INSTRUCTION_SIZE_BASE=origin/master` to compare against the PR base.

Use progressive disclosure for conditional detail; moving always-loaded text
to another file does not reduce runtime context. Size checks measure entrypoints,
not their complete dynamically loaded context.

When a larger entrypoint is justified, add `max_lines` and/or
`max_estimated_tokens` with a concrete `reason` in
`claude/evals/skill-maintenance/size-budgets.json`.

For an entrypoint change, run:

```sh
bash claude/evals/skill-maintenance/check_size.sh --base origin/master
```

To check both source and installed instructions without running setup:

```sh
bash claude/evals/skill-maintenance/check_size.sh --base origin/master --installed-home "$HOME"
```

CI scans the tracked sources and exercises installed coverage in the single
regression detector using a temporary home with a real symlinked skill tree.

When changing the size checker itself, run its single regression detector:

```sh
bash claude/evals/skill-maintenance/size_test.sh
```
