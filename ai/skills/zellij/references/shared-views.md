# Open useful shared views

## Put useful work beside the conversation

Open a pane when a persistent shared view helps: a test run, log tail, diff, file, or terminal UI the user can inspect while discussing it. Reuse a suitable task-owned pane when practical. Give new panes a meaningful title and explicit working directory. Launch the command directly instead of typing it into someone else's shell.

The installed runtime can create a pane without changing any client's focus:

```sh
zellij-pane open --session "$zellij_session" --tab "$zellij_tab_id" \
  --name "Review diff" -- git --no-pager diff --color=always
```

Open defaults to the current working directory, preserves focus, passes command arguments literally, and returns the verified new pane ID. Set `--cwd DIR` when needed. Commands run in the session server's environment. Retain the pane ID and inspect its contents before reporting the result. If creation has an uncertain outcome, inspect before retrying so a lost response does not create duplicate panes.

The helper runs the command in a persistent interactive shell, reports its exit status in that pane, and leaves a prompt after completion. This keeps the view navigable with the installed plugin; a created pane ID confirms creation, not successful command completion. Opening a pane does not broaden authorization for the command it runs. Native `new-pane --close-on-exit` remains useful for disposable views.

To show a local image in a shared pane:

```sh
zellij-pane image --session "$zellij_session" --tab "$zellij_tab_id" \
  --name "Shared image" /absolute/path/to/image.png
```

Image uses an installed `kitten icat` or `kitty +kitten icat`, streams image data for remote terminals, and retains a shell after the viewer exits. It reports missing viewers before creating a pane and installs nothing. A viewer exit status cannot establish rendered pixels; use an actual image capture or the user's observation when that distinction matters. Check navigation as well as the displayed content before handing off a view.

Tell the user where the view is and what it shows, for example: “Opened ‘Review diff’ in tab ‘backend’, pane terminal_12; the changes are visible there.” Refer to observed pane contents in the discussion rather than asking the user to copy text the agent can already read.
