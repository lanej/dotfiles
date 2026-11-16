"""Keep native Kitty rendering; only choose the title's text."""

import os
from weakref import WeakKeyDictionary

from kitty.fast_data_types import get_boss


_remote_markers = WeakKeyDictionary()


def draw_title(data):
    title = data["title"]
    tab = get_boss().tab_for_id(data["tab_id"])
    if tab is None:
        return title
    window = tab.active_window
    if window is None:
        return title

    marker = window.user_vars.get("dotfiles_zellij", "")
    connections = tuple(sorted(
        process["pid"] for process in window.child.foreground_processes
        if process["cmdline"] and os.path.basename(process["cmdline"][0]) == "ssh"
    ))
    if not marker:
        _remote_markers.pop(window, None)
    elif _remote_markers.get(window, (None,))[0] != marker:
        # A lost SSH connection cannot send cleanup. Bind each unique launcher
        # marker to its transport so it cannot label the next SSH connection.
        _remote_markers[window] = (marker, connections)

    # Cmd-R and explicit window titles keep their normal Kitty ownership.
    if tab.name or window.override_title is not None:
        return title
    if data["tab"].active_exe == "zellij":
        return title.split(" | ", 1)[0]
    if (connections and marker and _remote_markers.get(window) == (marker, connections)
            and window.screen.is_using_alternate_linebuf()):
        host = marker.split("/", 1)[0]
        return f"{host}/{title.split(' | ', 1)[0]}"
    return title
