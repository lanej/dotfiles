# Removal review

The change satisfies the repository portion of the owner's request:
- Remove only `superpowers@claude-plugins-official` from enabled plugins.
- Remove its required authoring route from the maintenance policy and root
  instruction files; retain the official skill-creator route.
- Record the rejected tool in the tech radar, as the repository requests.
- Preserve historical evaluation records and runtime custom skills.

A parsed comparison of old and new settings confirms all remaining values,
including other enabled plugins and hooks, are identical. The source review
confirms baseline retention, paired comparisons, evidence provenance, size
limits, missing-dependency reporting, and existing authorization rules remain.
The evidence checker and CI workflow have not been edited.

Validation: 43 maintenance tests passed. The broader bin suite produced 89
passes, four live-tmux skips (tmux is unavailable), and one failure:
`ConfigurationTests.test_all_lifecycle_hooks_are_wired_once`, for a missing
PostToolUse hook. The exact failing test also fails on the untouched base commit
`939036cea8495be4cc06a4969c02c1e528a4a64d` in a separate worktree.
This pre-existing failure is not repaired by the plugin-removal change.

Authoring context: the available Codex skill-creator guidance was read from
`skill://flora-skills/root/.codex/skills/.system/skill-creator/SKILL.md`.
The installed executor skill catalog contains neither Superpowers writing-skills
nor the target Anthropic skill-creator plugin. Those workflows were not executed;
Codex guidance is not represented as a substitute for that target plugin.
The owner explicitly authorized removing Superpowers, including its dependency
in the maintenance route. This narrow configuration/routing review is manual,
performed by the implementing agent, and makes no behavioral-validation claim.
No model calls, model comparison settings, or native Claude session were used.

The PR removes the tracked configuration. It cannot remove an installed plugin
from the owner's machine here; its description includes the documented user-scope
uninstall command for existing installations. Restart Claude Code afterward.

