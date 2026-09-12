# Blocklist generalization

Request: generalize plugin removal to a reusable script and a list of unwanted
plugins, initially containing Superpowers, before merging.

Baseline: PR head 1857f214bbb5db54178987c08651d2ba0ce398a3 embeds one
Superpowers-specific check and uninstall in the Makefile. Adding another rejected
plugin requires changing imperative code.

Candidate: claude/blocked-plugins.json stores marketplace-qualified plugin IDs.
Make invokes bin/claude-remove-blocked-plugins with that file. The script detects
Claude, validates the blocklist and installed inventory, and removes the exact
user-scope intersection through the official CLI. Duplicate entries uninstall once;
an empty list, missing CLI, or absent matching installation is a no-op. Failures
propagate, and another run continues from the remaining installed state.

The existing instruction-policy sources and their routing remain unchanged from
the original removal review. This follow-up generalizes executable cleanup only.
