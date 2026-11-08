#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte==0.8.2"]
# ///
"""Compare real native styling with explicit, independently stored baselines."""

import argparse
import codecs
import difflib
import fcntl
import html
import importlib.util
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time

import pyte

ROOT = Path(__file__).resolve().parents[1]
GENERATED = Path(os.environ.get("DOTFILES_THEME_DIR", ROOT / "design-system/generated"))


class NativeScreen(pyte.Screen):
    def report_device_status(self, mode, **kwargs):
        if not kwargs.get("private"):
            super().report_device_status(mode)


def cells(screen, lines):
    return [[{key: getattr(screen.buffer[row][col], key) for key in ("data", "fg", "bg", "bold", "italics", "underscore", "reverse")} for col in range(screen.columns)] for row in range(lines)]


def ansi_cells(text, columns=76, lines=10):
    screen = NativeScreen(columns, lines)
    pyte.Stream(screen).feed(text.replace("\n", "\r\n"))
    return cells(screen, lines)


def compact(rows):
    result = []
    for row in rows:
        spans = []
        for cell in row:
            style = {key: value for key, value in cell.items() if key != "data"}
            if spans and all(spans[-1][key] == value for key, value in style.items()):
                spans[-1]["data"] += cell["data"]
            else:
                spans.append({**cell})
        result.append(spans)
    return result


def terminal(command, env, ready, *, columns=76, lines=24, capture_lines=10):
    pid, fd = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0))
        os.chdir(env["HOME"])
        os.execvpe(command[0], command, env)
    screen = NativeScreen(columns, lines)
    stream, decoder = pyte.Stream(screen), codecs.getincrementaldecoder("utf-8")("replace")
    raw = bytearray()
    deadline = time.monotonic() + 15
    try:
        while time.monotonic() < deadline:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                raw.extend(chunk)
                stream.feed(decoder.decode(chunk))
            if ready(screen):
                return cells(screen, capture_lines)
        raise AssertionError(f"Native preview did not become ready: {command[0]}\n" + "\n".join(screen.display))
    finally:
        os.close(fd)
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        for _ in range(30):
            if os.waitpid(pid, os.WNOHANG)[0]:
                break
            time.sleep(0.03)
        else:
            os.killpg(pid, signal.SIGKILL)
            os.waitpid(pid, 0)


def svg(name, rows):
    theme = json.loads((GENERATED / "colors.json").read_text())
    normal, background = theme["roles"]["text"], theme["roles"]["surface"]
    names = ["black", "red", "green", "brown", "blue", "magenta", "cyan", "white"]
    colors = {key: theme["ansi"][index] for index, key in enumerate(names)}
    colors.update({"bright" + key: theme["ansi"][index + 8] for index, key in enumerate(names)})
    colors["yellow"] = colors["brown"]

    def color(value, fallback):
        if value == "default":
            return fallback
        return "#" + value if len(value) == 6 else colors.get(value, fallback)

    width, height = sum(len(cell["data"]) for cell in rows[0]) * 9 + 24, len(rows) * 20 + 24
    result = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(name)} — captured native terminal cells">', f'<rect width="100%" height="100%" fill="{background}"/>', '<g font-family="monospace" font-size="14" style="white-space:pre">']
    for row, line in enumerate(compact(rows)):
        col = 0
        for cell in line:
            fg, bg = color(cell["fg"], normal), color(cell["bg"], background)
            if cell["reverse"]:
                fg, bg = bg, fg
            x, y = 12 + col * 9, 12 + row * 20
            result.append(f'<rect x="{x}" y="{y}" width="{len(cell["data"])*9}" height="20" fill="{bg}"/>')
            if cell["data"].strip():
                weight = "bold" if cell["bold"] else "normal"
                italic = "italic" if cell["italics"] else "normal"
                decoration = "underline" if cell["underscore"] else "none"
                # WHY: SVG renderers can discard terminal padding before applying textLength.
                visible = cell["data"].strip(" ")
                text_x = x + (len(cell["data"]) - len(cell["data"].lstrip(" "))) * 9
                result.append(f'<text x="{text_x}" y="{y+15}" fill="{fg}" font-weight="{weight}" font-style="{italic}" text-decoration="{decoration}" textLength="{len(visible)*9}" lengthAdjust="spacingAndGlyphs">{html.escape(visible)}</text>')
            col += len(cell["data"])
    return "\n".join([*result, "</g></svg>\n"])


def neovim(work, env, plugins):
    script = work / "theme.lua"
    script.write_text('''
vim.opt.rtp:prepend(vim.env.THEME_ROOT .. "/nvim")
for _, plugin in ipairs({"gitsigns.nvim", "lualine.nvim", "fzf-lua"}) do
  local path = vim.env.THEME_PLUGINS .. "/" .. plugin
  assert(vim.fn.isdirectory(path) == 1, "Missing real plugin: " .. path)
  vim.opt.rtp:append(path)
end
require("dotfiles-theme").setup()
require("gitsigns").setup()
require("lualine").setup({options = {theme = require("dotfiles-theme").lualine()}})
require("fzf-lua").setup()
vim.api.nvim_set_hl(0, "FzfLuaFzfPointer", {fg = "#010203"})
vim.api.nvim_exec_autocmds("User", {pattern = "LazyLoad"})
vim.wait(100, function() return false end)
local function observed()
  local result = {}
  for _, name in ipairs({"Normal", "NormalFloat", "Visual", "Comment", "Function", "String", "Type", "DiagnosticError", "DiagnosticWarn", "DiffAdd", "DiffDelete", "GitSignsAdd", "GitSignsStagedAdd", "GitSignsAddInline", "FzfLuaNormal", "FzfLuaBorder", "FzfLuaCursorLine", "FzfLuaFzfPointer", "FzfLuaFzfMatch", "FzfLuaFzfCursorLine", "lualine_a_normal", "@variable.member"}) do
    result[name] = vim.api.nvim_get_hl(0, {name = name, link = false})
  end
  result.terminal_color_4 = vim.g.terminal_color_4
  return result
end
local before = observed()
vim.cmd.colorscheme("dotfiles")
vim.wait(100, function() return false end)
assert(vim.deep_equal(before, observed()), "Native plugin styling changes after colorscheme reload")
vim.fn.writefile({vim.json.encode(before)}, vim.env.THEME_OBSERVATIONS)
''')
    path = work / "neovim.json"
    subprocess.run(["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l", str(script)], env={**env, "THEME_ROOT": str(ROOT), "THEME_PLUGINS": str(plugins), "THEME_OBSERVATIONS": str(path)}, check=True, capture_output=True, text=True)
    return json.loads(path.read_text())


def run(surface, work, env, plugins):
    if surface == "neovim":
        return neovim(work, env, plugins)
    if surface == "neovim-frame":
        command = ["nvim", "-u", "NONE", "-i", "NONE", "-n", "--cmd", "set rtp^=" + str(ROOT / "nvim"), "-c", "colorscheme dotfiles", "-c", "syntax on", "-c", "set noshowmode noruler laststatus=0 noshowcmd", str(ROOT / "design-system/fixtures/code.lua")]
        return terminal(command, env, lambda screen: "print(greet" in "\n".join(screen.display))
    if surface == "kitty":
        config = work / "home/.config/kitty"
        config.mkdir()
        (config / "kitty.conf").symlink_to(ROOT / "kitty/kittyconf")
        code = '''from kitty.config import load_config
import os, json
bad = []
opts = load_config(os.environ["THEME_KITTY_CONFIG"], accumulate_bad_lines=bad)
assert not bad, repr(bad)
print(json.dumps({name: str(getattr(opts, name)) for name in ("foreground", "background", "selection_foreground", "selection_background", "cursor", "active_tab_foreground", "background_opacity", *("color" + str(i) for i in range(16)))}))'''
        return json.loads(subprocess.check_output(["kitty", "+runpy", code], env={**env, "THEME_KITTY_CONFIG": str(config / "kitty.conf")}, text=True))
    if surface == "zellij":
        specification = importlib.util.spec_from_file_location("zellij_workflow", ROOT / "scripts/test-zellij.py")
        workflow = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(workflow)
        runtime, temporary = work / "run", work / "tmp"
        runtime.mkdir(mode=0o700)
        temporary.mkdir()
        native_env = {**env, "SHELL": "/bin/sh", "PS1": workflow.PROMPT.decode(), "XDG_RUNTIME_DIR": str(runtime), "XDG_STATE_HOME": str(work / "state"), "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temporary)}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR", "ZELLIJ_CONFIG_FILE", "ENV", "BASH_ENV"):
            native_env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij"], cwd=ROOT, env=native_env, check=True, capture_output=True)
        name = "theme-" + work.name
        client = workflow.Terminal(shutil.which("zellij"), native_env, name, install_navigation=False, columns=76)
        screen = NativeScreen(76, 32)
        stream, decoder, offset = pyte.Stream(screen), codecs.getincrementaldecoder("utf-8")("replace"), 0
        def ready():
            nonlocal offset
            stream.feed(decoder.decode(bytes(client.output[offset:])))
            offset = len(client.output)
            return "PREFIX" in screen.display[0] and "Esc cancels" in screen.display[0]
        try:
            client.grant_status_permissions()
            client.until("theme fixture shell ready", lambda: workflow.PROMPT in client.output)
            client.send(b"\x06")
            client.until("native themed prefix", ready)
            return cells(screen, 1)
        finally:
            subprocess.run(["zellij", "kill-session", name], env=native_env, capture_output=True, timeout=5)
            client.close()
    if surface == "cli":
        text = subprocess.check_output([str(ROOT / "bin/dotfiles-theme"), "--color=always"], env=env, text=True)
        return ansi_cells(text)
    if surface in ("bat", "delta"):
        cache = subprocess.run(["bat", "cache", "--build"], env=env, capture_output=True, text=True)
        if cache.returncode:
            raise AssertionError(cache.stderr)
        text = subprocess.check_output(["bat", "--list-themes", "--color=never"], env=env, text=True)
        assert "Dotfiles" in text, "bat did not register the generated syntax theme"
        if surface == "bat":
            command = ["bat", "--theme=Dotfiles", "--color=always", "--paging=never", "--style=plain", "--language=lua", str(ROOT / "design-system/fixtures/code.lua")]
            text = subprocess.check_output(command, env=env, text=True)
        else:
            themes = subprocess.check_output(["delta", "--list-syntax-themes"], env=env, text=True)
            assert "Dotfiles" in themes, "delta cannot read the generated bat theme cache"
            text = subprocess.check_output(["delta", "--paging=never", "--width=76", "--true-color=always"], env=env, input=(ROOT / "design-system/fixtures/change.diff").read_text(), text=True)
        return ansi_cells(text)
    if surface == "glow":
        text = subprocess.check_output(["glow", "--style", str(GENERATED / "glow.json"), "--width=70", str(ROOT / "design-system/fixtures/document.md")], env=env, stdin=subprocess.DEVNULL, text=True)
        return ansi_cells(text, lines=14)
    if surface == "fzf":
        command = ["bash", "-c", 'printf "api\\tapi OK\\nworker\\tworker ERROR\\n" | "$1" --no-multi --delimiter="\\t" --with-nth=2.. --reverse --info=hidden --header="Services" --prompt="Search > "', "bash", str(ROOT / "bin/dotfiles-fzf")]
        return terminal(command, env, lambda screen: "worker ERROR" in "\n".join(screen.display))
    if surface == "bottom":
        result = terminal(["btm", "--config_location", str(GENERATED / "bottom.toml"), "--basic"], env, lambda screen: "CPU" in "\n".join(screen.display), capture_lines=2)
        # WHY: CPU count and resource samples vary across hosts; CPU0 exists on both.
        label = next(cell for cell in result[0] if cell["data"].strip())
        assert label["data"] == "0", "bottom's CPU0 layout changed"
        return {"cpu0_label": {key: value for key, value in label.items() if key != "data"}}
    if surface == "tmux":
        socket = str(work / "tmux.sock")
        command = ["tmux", "-S", socket, "-f", str(GENERATED / "tmux.conf"), "new-session", "-d", "-s", "fixture", "sleep 60"]
        subprocess.run(command, env=env, check=True, capture_output=True)
        try:
            def tmux(*args):
                return subprocess.check_output(["tmux", "-S", socket, *args], env=env, text=True)
            observations = {key: tmux("show-options", "-gv", key).strip() for key in ("window-status-current-style", "window-style", "pane-active-border-style", "pane-border-style", "message-style", "status-style")}
            for key, value in {"@claude-state": "approval", "@claude-bg": "#010203", "@claude-fg": "#040506", "@claude-since": "123", "@claude-reason": "fixture"}.items():
                tmux("set-option", "-w", key, value)
            tmux("source-file", str(GENERATED / "tmux.conf"))
            drawn = tmux("display-message", "-p", "#{E:window-status-format}")
            attention = json.loads((GENERATED / "colors.json").read_text())["roles"]["status.attention"]
            assert attention in drawn and "#010203" not in drawn and "#040506" not in drawn
            subprocess.run([sys.executable, str(ROOT / "bin/tmux-claude-state"), "refresh-theme"], env={**env, "TMUX": socket + ",0,0"}, check=True)
            assert tmux("show-options", "-wv", "@claude-bg").strip() == json.loads((GENERATED / "colors.json").read_text())["roles"]["status.attention"]
            assert tmux("show-options", "-wv", "@claude-since").strip() == "123"
            assert tmux("show-options", "-wv", "@claude-reason").strip() == "fixture"
            assert observations == {key: tmux("show-options", "-gv", key).strip() for key in observations}
            return observations
        finally:
            subprocess.run(["tmux", "-S", socket, "kill-server"], env=env, capture_output=True)
    raise ValueError(surface)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", action="append", choices=["kitty", "neovim", "neovim-frame", "zellij", "tmux", "cli", "fzf", "bat", "delta", "glow", "bottom"])
    parser.add_argument("--plugins-dir", type=Path, default=Path.home() / ".local/share/nvim/lazy")
    parser.add_argument("--record", action="store_true", help="Explicitly replace observed baselines; inspect changes before accepting them")
    args = parser.parse_args()
    preset = json.loads((GENERATED / "colors.json").read_text())["theme"]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", preset):
        parser.error("invalid generated theme name")
    baselines = ROOT / "design-system/baselines" / preset
    surfaces = args.surface or ["kitty", "neovim", "neovim-frame", "zellij", "tmux", "cli", "fzf", "bat", "delta", "glow", "bottom"]
    with tempfile.TemporaryDirectory(prefix="theme-native-", dir="/tmp") as temporary:
        work = Path(temporary).resolve()
        home = work / "home"
        for name in (".config/bat/themes", ".config/dotfiles", ".cache", ".local/share"):
            (home / name).mkdir(parents=True, exist_ok=True)
        (home / ".config/dotfiles/theme").symlink_to(GENERATED)
        shutil.copyfile(GENERATED / "Dotfiles.tmTheme", home / ".config/bat/themes/Dotfiles.tmTheme")
        (home / ".gitconfig").write_text('[include]\npath = ' + str(GENERATED / 'delta.gitconfig') + '\n[delta]\nfeatures = dotfiles\n')
        locale = "C.UTF-8" if sys.platform.startswith("linux") else "en_US.UTF-8"
        env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache"), "XDG_DATA_HOME": str(home / ".local/share"), "BAT_CONFIG_DIR": str(home / ".config/bat"), "BAT_CACHE_PATH": str(home / ".cache/bat"), "TERM": "xterm-256color", "COLORTERM": "truecolor", "CLICOLOR_FORCE": "1", "DOTFILES_THEME_DIR": str(GENERATED), "LANG": locale, "LC_ALL": locale}
        for name in ("TMUX", "TMUX_PANE", "NO_COLOR", "FZF_DEFAULT_OPTS", "FZF_DEFAULT_OPTS_FILE", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "BAT_THEME", "DELTA_FEATURES"):
            env.pop(name, None)
        for surface in surfaces:
            observed = run(surface, work, env, args.plugins_dir)
            terminal_rows = isinstance(observed, list) and observed and isinstance(observed[0], list)
            snapshot = compact(observed) if terminal_rows else observed
            baseline = baselines / f"{surface}.json"
            if args.record:
                baselines.mkdir(parents=True, exist_ok=True)
                baseline.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
                if terminal_rows:
                    capture = ROOT / "docs/design-system/presets" / preset / f"{surface}.svg"
                    capture.parent.mkdir(parents=True, exist_ok=True)
                    capture.write_text(svg(surface, observed))
                print(f"RECORDED {surface}: inspect baseline and native capture")
            else:
                expected = json.loads(baseline.read_text())
                if snapshot != expected:
                    difference = "\n".join(difflib.unified_diff(json.dumps(expected, indent=2, sort_keys=True).splitlines(), json.dumps(snapshot, indent=2, sort_keys=True).splitlines(), fromfile="expected", tofile="observed", lineterm=""))
                    raise AssertionError(f"{surface}: native style regression against {baseline.relative_to(ROOT)}\n{difference}")
                print(f"PASS {surface}: native styling and baseline agree")


if __name__ == "__main__":
    main()
