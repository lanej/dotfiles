# Kitty hint picker

The URL and link/file shortcuts launch one local Go executable using Kitty's native formatted screen snapshot. It uses the already configured `KITTY_LISTEN_ON` Unix socket to query the palette and route selected destinations. It never enables remote control or changes socket permissions.

## Install

Run `make kitty-native-hints` with Kitty 0.50.0, Go 1.26 or newer, and Python 3.11+ available for the upstream build generator. The build verifies the pinned Kitty source archive, compiles and tests the helper, and installs it in `~/.local/bin/hint-native`. Run `make kitty-config` and reload Kitty after installing the executable. Configuration targets do not download or compile software. Rebuild explicitly when the helper changes.

Ctrl+Shift+E selects visible URLs. Cmd+Shift+U selects OSC 8 hyperlinks and files in the originating Zellij pane. Escape cancels; ordinary mouse clicks select highlighted targets. No persistent worker or custom Python kitten is involved at runtime.

The Zellij receiver validates the ticket, source pane and working directory before opening a file; the picker also checks the source Kitty window and cursor marker immediately before dispatch. A successful socket write is not a confirmation that the receiver opened the file. The existing socket API cannot make the marker check and send a single atomic operation.

Kitty's public action interface differs from its private hyperlink callback. For `allow_hyperlinks ask`, the helper does not bypass confirmation; use ordinary Kitty link activation instead. Remote file links require the Zellij receiver. The standard URL action preserves Kitty's configured opener. ANSI sized text and other unsupported screen controls are not guaranteed to reproduce cell geometry; such snapshots fail explicitly rather than selecting from a corrupted frame.
