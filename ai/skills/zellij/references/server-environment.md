# Launch servers with the user environment

## Launch interactive servers with the user's environment

Before creating, restoring, or restarting an interactive session server, establish a verified user-terminal environment baseline from an unaffected user shell or terminal launcher. A child pane of an affected server is not an independent baseline. Agent command runners can inject `NO_COLOR=1` and `GIT_PAGER=cat`; copying their environment into a long-lived server spreads those overrides to its panes despite correct theme and Git configuration.

Build the launch environment from that baseline and pass it explicitly to the server process. Preserve intentional user settings, including color and pager choices, and the terminal's `TERM` and `COLORTERM`. Exclude runner overrides that are absent from the baseline. Retain the baseline's other required environment values; a comparison of a few display variables is not a complete launch environment. Inspect only the variables needed for the comparison; do not print complete environments or credentials. If the baseline cannot be verified, stop the server launch and report the missing evidence. Do not compensate by changing global shell, theme, or Git configuration.

A clean client reattachment does not remove settings already inherited by a running server or its existing panes. Remove unwanted variables from the launch environment rather than assigning empty strings: some color detection treats an empty `NO_COLOR` as enabled. A repair that requires another server restart remains subject to the existing authorization and preservation rules.

After launch, inspect the relevant variables in the actual server and a disposable child pane. Verify Codex presentation against the user's selected color preference, including intentional color suppression, and the selected Git pager and Delta output in a real terminal when those capabilities are affected. Config files, installed binaries, or a successful attach alone do not establish restored behavior; report any verification that remains unavailable.
