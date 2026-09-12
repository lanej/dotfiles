# Baseline review before editing

Request: Remove the Superpowers Claude Code plugin in a PR, favoring the
remaining official plugins and the owner’s custom skills.

Source snapshot: `baseline-sources.json`, captured from commit
`939036cea8495be4cc06a4969c02c1e528a4a64d` before editing.

Observed failure: `.claude/settings.json` enables
`superpowers@claude-plugins-official`. Both root instruction files route to a
policy that explicitly requires `superpowers:writing-skills` and its TDD
background before maintenance. Removing only the settings entry would leave
future authorized skill maintenance dependent on the removed plugin.

Manual routing scenario: An owner asks to correct an existing `/specify`
instruction after Superpowers has been uninstalled. Under the old policy, the
maintainer must resolve Superpowers before editing and report its absence when
unavailable. The enabled official skill-creator alone cannot satisfy that route.
This is a source-based walkthrough, not a captured Claude execution.

The evaluation scope is plugin configuration and maintenance routing. Existing
runtime commands, skills, agent definitions, gates, and historical evidence are
outside the requested behavior change.
