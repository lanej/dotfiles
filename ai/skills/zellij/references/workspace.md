# Preserve shared resources and apply collaboration proportionately

## Preserve the shared workspace

Prefer explicit targets and operations that preserve focus. Refresh pane identity before sending input, changing layout, or closing a pane; titles and numeric IDs can be reused. Existing panes may contain editors, REPLs, or another agent rather than an idle shell. Write to them only when the task authorizes controlling that process and its state is known.

Track panes and processes created for the task. Close only owned disposable panes after checking their current contents and active processes. Leave useful shared views open and mention them at handoff. Preserve user panes, focus, and layout unless changing them serves the user's request.

Stay within the existing session for collaboration. Avoid nesting an attachment to the same or a containing session; recursive viewers can collapse geometry and disrupt the shared view. Session shutdown, broad pane closure, and restarting a server need their own task justification and authorization.

## Apply it proportionately

- “Why is the test stuck?” Locate the test pane, capture its current output and relevant history, then investigate the observed stall.
- “Let's review this together.” Open a named diff or file view, confirm its pane ID, and direct the user to that shared view.
- “The monitor looks clipped.” Inspect pane geometry and an actual image when available; verify the changed view again after a repair.

For work that gains nothing from shared terminal context, continue normally. Report unavailable session access or unsupported capture capabilities briefly and keep progressing with the evidence available.
