#!/usr/bin/env python3
"""Kitten to close tab with confirmation if tmux is running."""

from typing import List
from kitty.boss import Boss


def main(args: List[str]) -> str:
    """Close tab with confirmation if tmux is running."""
    return ""


def handle_result(
    args: List[str], answer: str, target_window_id: int, boss: Boss
) -> None:
    """Handle the result and close the tab if appropriate."""
    tab = boss.active_tab
    if not tab:
        return

    # Get the foreground processes in the tab
    processes = []
    for window in tab:
        if window.child and window.child.foreground_processes:
            processes.extend(
                [p["cmdline"][0] for p in window.child.foreground_processes]
            )

    # Check if tmux is running
    has_tmux = any("tmux" in str(p).lower() for p in processes)

    if has_tmux:
        # Ask for confirmation
        boss.confirm(
            "Tmux session active. Close tab?",
            lambda confirmed: boss.close_tab() if confirmed else None,
        )
    else:
        # Close without confirmation
        boss.close_tab()


handle_result.no_ui = False
