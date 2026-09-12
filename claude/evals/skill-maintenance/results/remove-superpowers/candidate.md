# Candidate routing review

Same request and manual routing scenario as `baseline.md`.

The shared settings no longer enable Superpowers. For an authorized correction
to an existing `/specify` instruction, both root routing files now direct the
maintainer to the enabled Anthropic `skill-creator:skill-creator` workflow.
The policy still requires retaining the old source and observed failure,
comparing the correction against that source, and preserving review evidence.
No step requires resolving Superpowers or its writing-skills/TDD resources.

A new skill still compares against no skill. If the official skill-creator is
unavailable, the policy still requires reporting the missing dependency and
validation gap; the older repo-owned skill does not silently substitute for it.
The owner's existing instructions and authorization remain authoritative.

This is a manual source-based walkthrough by the implementing Codex agent,
not a paired model evaluation, independent review, or live Claude integration
test. No runtime command, skill, or agent instruction was changed.

