# Blocklist review

The implementing agent reviewed the script, Make integration, blocklist, and
README. The script uses standard-library Python, argument arrays rather than
shell interpolation, exact marketplace-qualified IDs, and explicit user scope.
Malformed configuration or inventory produces a nonzero exit before removal.

All 14 focused tests passed (tests.txt). They execute the actual Make target
with a stateful fake Claude CLI. Coverage includes multiple blocked plugins,
duplicate list entries, enabled/disabled installed state, preserving other IDs
and project scope, repeat runs, missing Claude, empty and invalid blocklists,
failed inspection/uninstall, and retry after one of several uninstalls fails.
Dry runs cover default make and make claude wiring.

This is isolated command-integration validation, not a native Claude installation
test or model-behavior comparison. Prior instruction snapshots, routing review,
and their limitations remain in the preceding evidence directories. The previous
Superpowers-only Make implementation is superseded. Historical evidence is kept.
The already-reproduced unrelated tmux PostToolUse wiring failure is unchanged.
