---
name: skill-authoring
description: Create, revise, or review reusable agent skills, commands, and agent instructions. Use when authoring instruction packages or repairing their discovery, portability, or behavior.
---

# Skill authoring

Own the instructions in the repository that maintains them. This workflow works with Codex and Claude Code and does not require a vendor's authoring plugin. Existing user instructions and repository policy remain authoritative.

## Establish the contract

Read the current entrypoint, its callers, supporting resources, installation path, and the repository's maintenance policy. Identify the user outcome, invocation, intended host capabilities, artifacts, authority limits, and retained behavior. Reuse established decisions; ask only when an unresolved choice changes those outcomes.

Choose a representative request and an observable result that could expose a defect before editing. For a repair, use the reported failure. Distinguish package discovery, instruction loading, assistant behavior, and external outcomes; evidence for one does not establish the others.

## Author the smallest useful package

- Use `SKILL.md` with YAML `name` and `description`; the name matches its lowercase, hyphenated directory. Describe the capability and its actual triggers. Narrow broad verbs such as "verify" to the intended workflow.
- Put essential behavior in the entrypoint. Add `references/`, `scripts/`, or `assets/` only for material that earns its place. Tell the reader when to load a reference or run a script. Keep Markdown paragraphs on one source line.
- Keep one canonical procedure per capability. Compatibility commands route to that procedure; they do not copy its rules. Preserve meaningful existing artifacts and lifecycle states when moving sources.
- Separate shared meaning from host mechanics: available tools, identity, transcript formats, planning restrictions, and dispatch. Never require a vendor-specific tool on another host or claim an unavailable operation succeeded.
- Specify consequential failures and unknown outcomes. Unanswered questions remain unanswered; intent, dispatch, completion, approval, and verified effects are distinct.
- Preserve the caller's scope and authority. A skill invocation does not grant permission to publish, message others, write global memory, or execute a plan beyond the user's instruction. Delegated tasks inherit only the stated authority.
- Avoid generic advice, invented requirements, fixed interview quotas, duplicated policies, and default evaluation bundles. Add source comments only where the repository's comment guidance calls for them.

## Validate proportionately

Run [the package validator](scripts/validate.py) with `uv run /path/to/skill-authoring/scripts/validate.py /path/to/skill ...`. It checks metadata and local resource links; it does not prove assistant behavior. Run changed executable helpers against representative inputs, including consequential failure cases. Prefer an existing behavioral detector over a second harness; source-string assertions cannot establish that instructions work.

In dotfiles, run the affected installer/detector plus `bash claude/evals/skill-maintenance/check_size.sh --base origin/master`, `bin/claude-skill-audit --path ai/skills`, and `git diff --check`. Deliberately force-add new instruction sources when the repository ignores them. Keep CI selection tied to the actual inputs of each detector.

For complex interaction or authority changes, obtain independent review. When realistic execution would reduce uncertainty and delegation is available, give a fresh-context agent the skill, a realistic request, raw input artifacts, and a temporary output directory. Do not supply the expected answer or the author's conclusions. Bound permitted effects. Review the resulting artifacts yourself; report unavailable capabilities or simulated boundaries. Do not turn routine edits into a broad model study. Reviewers and evaluating agents must not recursively dispatch reviews.

## Install and report

Install through the owning repository's supported path. Preserve unrelated local entries and user configuration. Verify discoverability in the actual host, read the installed resources, and exercise the representative request where possible. A portable install must remain readable without the authoring checkout.

Report the changed behavior, relevant verification, and material limits. Keep package checks, observed model behavior, and live external outcomes separate. Update the existing documentation rather than creating a parallel maintenance policy.
