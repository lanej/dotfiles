#!/usr/bin/env python3
"""Exercise passive WhichKey against a real, isolated Zellij PTY."""
import html
import importlib
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

workflow = importlib.import_module("test-zellij")
palette = importlib.import_module("test-zellij-command-prompt")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


def rendered(terminal):
    return "\n".join(palette.screen(terminal))


def capture(terminal, name):
    """Write a real terminal capture as SVG, not a synthetic mockup."""
    destination = os.environ.get("ZELLIJ_TEST_ARTIFACTS")
    if not destination:
        return
    output = Path(destination) / "which-key"
    output.mkdir(parents=True, exist_ok=True)
    rows = palette.screen(terminal)
    width, height = 1040, 660
    lines = []
    for i, row in enumerate(rows):
        lines.append(f'<text x="18" y="{30 + i * 19}">{html.escape(row)}</text>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="#2e3440"/>'
        '<g font-family="Menlo, DejaVu Sans Mono, monospace" font-size="15" '
        'xml:space="preserve" fill="#d8dee9">' + "".join(lines) + '</g></svg>'
    )
    (output / f"{name}.svg").write_text(svg)
    (output / f"{name}.txt").write_text("\n".join(rows) + "\n")


def main():
    binary = shutil.which("zellij")
    assert binary, "Install the pinned Zellij runtime before testing"
    installed = Path.home() / ".local/share/zellij/plugins/which-key.wasm"
    assert installed.exists(), "Run make zellij-which-key before testing"
    with tempfile.TemporaryDirectory(prefix="zellij-which-key-") as root:
        work = Path(root)
        home, runtime = work / "home", work / "runtime"
        home.mkdir()
        runtime.mkdir()
        plugin = home / ".local/share/zellij/plugins/which-key.wasm"
        plugin.parent.mkdir(parents=True)
        shutil.copyfile(installed, plugin)
        config = home / ".config/zellij"
        (config / "layouts").mkdir(parents=True)
        (config / "layouts/test.kdl").write_text(
            'layout { tab { pane; } new_tab_template { pane; } }\n'
        )
        production = (ROOT / "zellij/config.kdl").read_text()
        native_keys = palette.block(palette.block(production, r"keybinds\b"), r"\btmux\s*\{")
        selected = "\n".join(palette.block(native_keys, rf'bind "{re.escape(key)}"')
                             for key in ("?", "c"))
        config.joinpath("config.kdl").write_text("""
default_mode "locked"
default_shell "/bin/sh"
default_layout "test"
show_startup_tips false
show_release_notes false
session_serialization false
pane_frames true
mouse_mode false
plugins {
    which-key location="file:~/.local/share/zellij/plugins/which-key.wasm"
}
load_plugins { which-key }
keybinds clear-defaults=true {
    locked { bind "Ctrl f" { SwitchToMode "Tmux"; } }
    normal { bind "Ctrl f" { SwitchToMode "Tmux"; } }
    tmux {
        bind "Esc" { SwitchToMode "Locked"; }
""" + selected + """
    }
}
""")
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh",
               "PS1": PROMPT.decode(), "TERM": "xterm-256color",
               "XDG_CONFIG_HOME": str(config.parent),
               "XDG_RUNTIME_DIR": str(runtime), "ZELLIJ_SOCKET_DIR": str(runtime),
               "XDG_CACHE_HOME": str(work / "cache"),
               "XDG_DATA_HOME": str(work / "data")}
        workflow.preserve_rust_homes(env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID",
                    "ZELLIJ_CONFIG_DIR", "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE"):
            env.pop(key, None)
        subprocess.run([binary, "setup", "--check"], env=env, check=True,
                       capture_output=True)
        name = "which-key-test"
        terminal = Terminal(binary, env, name,
                            [binary, "attach", "--create", name, "--", "/bin/sh"],
                            install_navigation=False)
        try:
            terminal.until("plugin consent dialog", lambda: "(y/n)" in rendered(terminal).lower())
            terminal.send(b"y")
            terminal.until("shell available", lambda:
                           PROMPT.decode().strip() in rendered(terminal)
                           and "(y/n)" not in rendered(terminal).lower())
            terminal.send(b"\x06")
            terminal.until("delayed overlay appears", lambda:
                           "keybindings" in rendered(terminal))
            capture(terminal, "prefix-open")
            # The overlay must never capture the next native binding.
            terminal.send(b"c")
            terminal.until("native new-tab binding still works", lambda:
                           len(terminal.tabs()) == 2)
            terminal.until("overlay disappears on prefix exit", lambda:
                           "keybindings" not in rendered(terminal))
            capture(terminal, "prefix-closed")
            terminal.send(b"\x06\x1b")
            terminal.drain(0.5)
            assert "keybindings" not in rendered(terminal), "cancelled prefix opened overlay"
            terminal.send(b"\x06c")
            terminal.until("rapid prefix sequence works", lambda:
                           len(terminal.tabs()) == 3)
            terminal.drain(0.5)
            assert "keybindings" not in rendered(terminal), "stale timer reopened overlay"
            print("PASS: delayed display, native execution, cancellation, and stale timer")
        except Exception:
            capture(terminal, "failure")
            raise
        finally:
            subprocess.run([binary, "kill-session", name], env=env,
                           capture_output=True, timeout=5)
            terminal.close()


if __name__ == "__main__":
    main()
