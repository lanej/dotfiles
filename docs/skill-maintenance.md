# Maintaining skills and agent instructions

This policy applies to repo-owned skills, slash commands, agent definitions,
shared instructions, and their scripts, templates, and references. A command such
as `/socrates` is instructional behavior even though its entrypoint is not named
`SKILL.md`. Existing user instructions and authorization remain authoritative.

## Use the installed authoring workflows

Before editing, load **superpowers:writing-skills** and its required TDD background.
Use its failing-baseline → minimal correction → passing scenario → refactor cycle,
including its guidance for matching the instruction's form to the observed failure.
For an existing skill, retain the old version and its failure before changing it.

Use the enabled Anthropic **skill-creator:skill-creator** for its applicable paired
evaluations, captured outputs, grading, and user-review workflow. Writing-skills
governs the baseline-before-edit sequence; skill-creator supplies the evaluation
and review mechanics. Scope those mechanics to the task rather than duplicating
both workflows. A new skill compares against no skill; an improvement compares
against its captured old version. Follow the actual loaded guidance for the
relevant skill type, including pressure tests where it calls for them.

Resolve these qualified names through the runtime's installed skill/plugin
catalog. Record the versions or source locations used in the evaluation notes.
The older repo-owned `claude/skills/skill-creator` is not a substitute for the
enabled Anthropic plugin merely because its name matches. Do not edit plugin
caches or update installed plugins as a side effect of maintaining another skill.
If a required workflow is unavailable, report the missing dependency and the
validation that cannot be performed; do not claim it was followed.

These are maintainer instructions. Keep them here rather than copying the
authoring workflow into every runtime skill.

## Retain regression evidence

Keep the actual prompts, source snapshots, model/settings, baseline failures,
candidate outputs, and review judgments in the skill's evaluation directory.
Preserve unsuccessful runs; make a new iteration instead of rewriting history.
Explain fixture changes, and rerun both arms when comparison inputs change.
Judge observable decisions and artifacts; a source-string assertion or green
helper test does not establish that the consuming agent behaves correctly.

For Socrates, retain and rerun the core eight dialogue scenarios when changing its
dialogue/readiness behavior. Include affected `/specify`, `/shape`, `/critique`,
and `/verify` consumers and the shared scaffold/planning references in the review.
Reuse `claude/evals/socrates-dialogue/` and its documented review gate. Check native
file preservation or approval transitions when changing those mechanisms; label
tool-free evidence as simulated rather than native integration validation.

After the applicable evaluation and review, add `evidence.json` in a new directory
under `claude/evals/`. This small provenance record points to the existing outputs;
it does not replace skill-creator's benchmark, grading, or review files:

```json
{
  "version": 1,
  "sources": {
    "claude/skills/example/SKILL.md": "<SHA-256 of evaluated source bytes>",
    "claude/skills/example/references/workflow.md": "<SHA-256 of dependency bytes>"
  },
  "artifacts": {
    "baseline": {"path": "claude/evals/example/iteration-1/baseline.md", "sha256": "<SHA-256>"},
    "candidate": {"path": "claude/evals/example/iteration-1/candidate.md", "sha256": "<SHA-256>"},
    "review": {"path": "claude/evals/example/iteration-1/review.md", "sha256": "<SHA-256>"}
  },
  "checks": [
    {"name": "Report-only preserves files", "passed": true,
     "evidence": "Candidate transcript and fixture check show unchanged file hashes/counts."}
  ]
}
```

Include every changed instruction/resource and every unchanged dependency used by
the evaluated behavior in `sources`. For a reviewed deletion, use `null` for the
deleted source. Additional named artifacts can bind fixtures, manifests, individual
outputs, and grading files; capture all evidence the review relies on. Paths are
repository-relative, regular files. No credentials or private task data belong in
these records. JSON placeholders above must be replaced with real hashes.

CI requires every changed governed path to have a current record whose entire
source/dependency set and evidence artifacts match. Every declared check must pass.
It checks provenance and completeness of declared fields, **not** the truth of a
review, independence of its author, or completeness of the declared dependencies.
Reviewers still assess those. An unchanged historical run can remain in the repo
without validating a changed source. Unrelated existing skills need no backfill.

The policy, routing files, gate scripts, workflow, and budget overrides also require
evidence when changed, so their maintenance remains reviewable.

## Keep entrypoints within a size budget

CI measures tracked `SKILL.md` files in the Claude/Gemini skill trees and Markdown
command/agent entrypoints. Default budgets are **500 lines and approximately 4,000
tokens per file**, including frontmatter. The token estimate is
`ceil(UTF-8 bytes / 4)`, a deterministic size proxy, **not a Claude tokenizer or
API token count**. It needs no credentials or network access.

Each metric is checked separately against the larger of its budget and its size
on the PR base (or pre-push master). Existing overages may stay the same size or
shrink; they may not grow. New entrypoints must meet both budgets. This is a
non-growth rule for existing files, not a mandate to rewrite vendored skills.

Use progressive disclosure for relevant conditional detail. Moving text to a
reference that is always loaded does not reduce runtime context cost; include that
dependency in the evaluation and review. Size checks measure entrypoints, not the
complete dynamically loaded context.

When a larger entrypoint is justified, add a per-file override with `max_lines`
and/or `max_estimated_tokens` plus a concrete `reason` in
`claude/evals/skill-maintenance/size-budgets.json`. Budget changes themselves require
current reviewed evidence. These are local defaults, not claims that the upstream
authoring skills mandate these exact limits.

## Run the local checks

```sh
python3 -m pytest -q claude/evals/skill-maintenance
python3 claude/evals/skill-maintenance/check_evidence.py --base origin/master
python3 claude/evals/skill-maintenance/check_size.py --base origin/master
```

The evidence gate compares committed changes through `HEAD` and reads current file
bytes. Commit the candidate before the final check; subsequent edits invalidate
its captured hashes. CI runs without model calls. A green CI result establishes
the mechanical checks above, not automatic approval or proof of skill quality.
