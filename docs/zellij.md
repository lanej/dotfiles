# Zellij

My Zellij setup uses **Ctrl-f** as the prefix, Vim-style navigation, and one top tab bar. Start with the [keybinding map](zellij-keybinds.mdx), or choose a feature below.

The shared canonical Nord theme is documented in the [design-system catalog](design-system.mdx), with current native theme examples.

## Start a session

Enable Zellij in your [machine settings](../README.md#configuration-sets), then install the selected tools with `make install`. The guides below describe the managed modern configuration.

```sh
zj
zj work
```

`zj` attaches to or creates `main`; `zj work` chooses a session named `work`. **Ctrl-f d** detaches and keeps programs running. Run the same command to return.

If a first-use permission prompt appears in the top bar, focus it with **Ctrl-f k** and press **y**. After updating Zellij or its configuration, start a new session to use the new features; finish or save work before restarting older sessions.

## Familiar keys

Press **Ctrl-f**, release it, then press the next key. Uppercase letters need Shift. **Esc**, **Enter**, or **Ctrl-c** cancels the prefix. Most shortcuts immediately return control to the application.

The [keybinding map](zellij-keybinds.mdx) lists shortcuts, aliases, and keys inside modes. **Ctrl-f p** pastes copied session text; **Ctrl-f Ctrl-p** switches tabs.

<span id="smart-pane-navigation"></span>

## Navigation

| Feature | Use it to… |
| --- | --- |
| [Smart pane navigation](zellij/smart-navigation.mdx) | Move through editor splits and terminal panes with the same keys |
| [Status bar and tab titles](zellij/status-bar.mdx) | Read tab positions, activity, and keyboard modes |
| [Tab picker](zellij/tab-picker.mdx) | Find a tab and preview its panes |
| [Session picker](zellij/session-picker.mdx) | Switch between running workspaces |
| [Swap tabs](zellij/tab-swap.mdx) | Exchange two tab positions |

<span id="equalize-layout"></span>

## Pane arrangement

| Feature | Use it to… |
| --- | --- |
| [Move a pane](zellij/move-pane.mdx) | Move one running pane into a new or existing tab |
| [Gather panes](zellij/gather-panes.mdx) | Bring a tab's live panes into another tab |
| [Equalize panes](zellij/equalize.mdx) | Balance a row or column, or choose a layout |
| [Golden-ratio sizing](zellij/golden-ratio.mdx) | Size a full-height left pane for comfortable work |

## Shared popup and session shutdown

| Feature | Use it to… |
| --- | --- |
| [Shared popup](zellij/shared-popup.mdx) | Keep a scratch shell across tabs and sessions |
| [Command prompt](zellij/command-prompt.mdx) | Run a Zellij action without a shell command |
| [Create and rename sessions](zellij/sessions.mdx) | Open or name a workspace |
| [Detach one client](zellij/detach-client.mdx) | Disconnect a selected view while leaving programs running |
| [Shut down a session](zellij/shutdown.mdx) | Deliberately end one session with confirmation |

## Forwarded SSH agents

Use [SSH and forwarded agents](zellij/ssh-agent.mdx) to open remote workspaces and reconnect without losing authentication in existing panes. The same page covers the shared popup and 1Password agents.

<span id="keyboard-selection-and-paste"></span>
<span id="native-agent-status-and-attention"></span>
<span id="inbox-notices-and-history"></span>

## Text and attention

| Feature | Use it to… |
| --- | --- |
| [Copy and paste](zellij/copy-paste.mdx) | Select scrollback text and choose the right paste source |
| [Attention and triage](zellij/attention.mdx) | Visit requests, watch output, and mute panes |
| [Notifications and history](zellij/notifications.mdx) | Review events with a preview of their source panes |

## History and recovery

Detaching preserves running programs. After a session exits, the session manager may offer to reconstruct its layout and rerun commands; that does not restore program memory. The fuzzy session picker lists running sessions only.

Scrollback keeps up to 100,000 live lines per pane and up to 10,000 lines for recovery. A crash can lose recent output. The shared popup does not restore its running work after a server exit or reboot.

## Differences that remain

Older installations may use the legacy configuration: tab numbering starts at 1, several custom shortcuts are unavailable, and copying differs. See [legacy differences](zellij-keybinds.mdx#legacy-configuration) when your keys do not match.

Moving a live pane to another session, exact cell sizing, and tmux's timed repeat window are not supported. The relevant feature pages explain the alternatives.
