# Prevent attention-menu navigation from nesting a session inside itself

Status: recovered, implemented, independently reviewed, and installed on November 13, 2026. Running session servers retain their old code until restarted; they were preserved to keep their programs alive.

## What happened

On November 12, 2026, at 19:52:59 Pacific, `main` opened its shared popup as terminal pane 35. The native log records a normal `dotfiles-popup` handshake with ancestry `["main"]`. At 19:53:05, that same pane announced `main` instead of `dotfiles-popup`. Zellij then acknowledged `main` as nested inside `main`. A subsequent popup handshake at 19:53:11 inherited an ancestry list containing 2,178 copies of `main`.

The live pane inspection confirmed the loop: `main/terminal_35` ran the popup attachment command but reported `nested_session_name: "main"`. Its attention message repeated the host tab and “Shared popup” title. `main` had two attached clients; the actual `dotfiles-popup` session had none.

Josh recalls selecting an item from the “Needs my attention” menu, possibly an item associated with a popup. The log does not retain the selected row or the input event. The exact item remains unknown.

An isolated reproduction with the previous Zellij runtime, revision `e9491658c1bad657fab8e474ab6186dd819eddf6`, confirms that this menu can cause the observed transition. Start a host with an attention item, attach a guest in a floating pane, open the guest's native attention menu, and press Enter on the host's item. The floating pane changes from `nested_session_name: "fixture-guest"` to `"fixture-host"`. This reproduction loads the native `session-manager` menu and uses no custom status plugin.

## Recovery

Closed only `main/terminal_35`, the recursive attachment view. The attached client count fell from two to one. All nine other terminal panes in `main` survived, and all three terminal panes in `dotfiles-popup` survived. Follow-up inspection found no nested panes in `main`. Removing the attachment also reaches the runtime's existing client cleanup, which clears ancestry when its nesting client disconnects. Neither session server was restarted.

Private before/after pane snapshots and the bounded reproduction are retained in `/private/tmp/zellij-main-recovery-20261113/`.

## Cause and ownership

The native menu's `Inbox::go_to_selected` sends `FocusSessionPane { session_name, pane_id }` and closes the menu. The server dispatches that request through `Screen::session_pane_command` to `Screen::go_to_session_pane`. Local targets receive a pane-focus operation; every other session receives `ServerInstruction::SwitchSession` for the invoking client.

That client can be the attachment running inside the shared popup. Reconnecting it to its host preserves its containing terminal, making the host a child of itself. The nested handshake accepts the resulting self-reference; ancestry propagation and the nested status summaries then feed back through the same session. The menu's navigation is the initiating defect; the repeating tracker text is a consequence.

The fix is in the `lanej/zellij` runtime fork at `256a247936750a5490e337f40ea74cb35e094ed3`, branch `fix/attention-ancestor-navigation`. Dotfiles pins that revision and Neovim client revision `5c33972d36e8ceea011d4bc240e8cbb5a298ab0e` with matching generated protobuf definitions.

## Implemented behavior

The server rejects a nested attachment's attempt to reconnect to an ancestor, retaining the client, pane and programs. It shows: “This item belongs to a containing session. Return to that session before opening it.” In this configuration, `Ctrl-f u` returns control to the immediate host; deeper nesting may require repeating it.

Session reconnect requests, including attention-menu focus, history and close-current, pass through the screen's client-specific guard before history changes or source removal. Rejection reaches the existing client notice and CLI completion paths. The router keeps its client connection open while validation runs; it previously disconnected immediately after a keyboard switch request, even if asynchronous validation rejected it. A concurrent ordinary attachment to the same guest can navigate independently.

Each running server owns a full UUID v4. It survives renaming and changes on restart. Names remain display and lookup labels; equal names on distinct hosts do not establish a cycle. New identity-bearing guest announcements and ancestry messages are checked for self-reference, repeated UUIDs, malformed UUIDs and depth above 32 before their nesting state is accepted.

### Contracts and state

Public menu and plugin requests retain their existing names, pane IDs and invoking client IDs. The internal protocols add optional fields:

```text
Announce       + optional server_instance_id: UUID
AnnounceAck    + optional identity_ancestry: { server_instance_ids: UUID[] }
AncestryUpdate + optional identity_ancestry: { server_instance_ids: UUID[] }
SessionAttention + optional server_instance_id: UUID
SwitchContext    + optional expected_server_instance_id: UUID
                 + optional source_cleanup_token: string
ClientToServerMsg + SessionSwitchAttached { source_cleanup_token }
```

The guard stores each client's state as discovering, ordinary, or nested with names and optional UUID ancestry. Expected nested clients stay pending until the handshake supplies identity; a timeout never promotes them to ordinary. Ordinary candidates settle after three seconds. Descendants receive unknown identity while a containing attachment is pending or identities conflict, then receive a fresh ancestry update. Removing one client preserves the remaining clients' ancestry and host controls.

Native pane environments set `ZELLIJ_NESTED_ATTACH=1`. The popup helper preserves that marker while removing its traditional Zellij variables; `zssh` explicitly carries its original nested/ordinary classification. Native clients capture the classification before modifying their own environment and retain it across reconnects. Browser and remote bridge messages carry the declaration and authoritative identity frames. Legacy ancestry without UUIDs remains unknown and blocks cross-session navigation from that attachment with an explanatory notice.

The peer-attention response supplies the live destination UUID, including when its screen snapshot times out. The source carries the expected UUID through reconnect; the destination checks it before changing focus, history or other clients. Replacement returns an explicit “destination session changed” error. The source attachment may already have been released at that point, but source and replacement programs remain alive.

Close-current retains its existing eligibility rule: no command submitted and no other interactive client attached at switch time. An eligible source receives a bounded cleanup token. The destination confirms attachment after initialization, and the source rechecks that token, command state and attached clients before terminating itself. Missing confirmation preserves the source.

## Verification and limits

`make test-zellij-ancestor-navigation` uses real terminal clients and the native attention menu without custom status plugins. The old binary fails at the assertion that the menu must not attach the host inside itself. The candidate passes these checks:

- Ancestor menu and close-current rejection retain the exact client listing, terminal pane IDs, shell PID and shell memory.
- A concurrent ordinary attachment can switch to the host, while the original nested attachment remains protected.
- A nested attachment can switch to an unrelated session.
- An untouched source closes after a confirmed valid handoff.
- Pausing the isolated client and replacing its destination before reconnect produces a clear rejection and preserves both sessions' shell PID and memory.

Focused native tests cover the guard, existing nesting behavior, identity encoding, environment propagation, cleanup-message encoding and screen-query timeout identity. The release build and formatting checks pass, and independent code review approved the material changes. Dotfiles helper checks pass with the generated contract. The installed runtime also passes the ancestor-navigation detector, the shared-popup shell-preservation journey and real Neovim pane navigation with the matching client.

SSH, browser and mixed-version transport behavior received source review and compilation rather than equivalent real transport acceptance. An arbitrary legacy host that removes every nesting marker cannot provide a complete cycle-prevention guarantee. Identity-less nested attachments deliberately have restricted cross-session navigation. The installed binary and dependency pins do not upgrade already running servers; restarting them would terminate their terminal processes, so this recovery left them running.
