# Convergent removal

Follow-up request: put plugin removal in default make, checking Claude availability
and converging to the desired state.

Baseline: commit aabe930834553a9b2b493bf5b5f8dad8d2442873 removes the enabled
setting, but its Makefile only links configuration and does not uninstall plugins.
The prior instruction snapshots and routing review remain in remove-superpowers/.

Candidate: claude depends on the phony claude-plugins target. Default all already
includes claude through the existing .PHONY dependency. The new target checks for
the CLI, reads the installed inventory, and uninstalls only the exact Superpowers
ID at user scope. An absent CLI or absent matching installation succeeds without
uninstalling anything. Inventory, JSON parsing, and uninstall errors propagate.
Cleanup runs before the existing settings symlink steps.

The instruction sources and their routing are unchanged from the prior review;
this follow-up changes Makefile behavior and documents that behavior in README.
