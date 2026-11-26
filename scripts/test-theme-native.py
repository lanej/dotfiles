#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte==0.8.2"]
# ///
"""Compare real native styling with explicit, independently stored baselines."""

import argparse
import codecs
from collections import namedtuple
import difflib
import fcntl
import html
import importlib.util
import json
import tomllib
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

from theme_review import TerminalColorQueries, TerminalMetadata, render_svg
import theme_review_contract as review_contract

ROOT = Path(__file__).resolve().parents[1]
GENERATED = Path(os.environ.get("DOTFILES_THEME_DIR", ROOT / "design-system/generated"))


class NativeStream(pyte.Stream):
    # Inline terminal redraws can move left by several tab stops with CSI Z.
    csi = {**pyte.Stream.csi, "Z": "back_tab"}
    pending = ""

    def feed(self, data):
        # pyte treats xterm's CSI >4;2m keyboard mode as SGR underline.
        # A PTY read can split the escape sequence at any byte.
        # DCS is terminal metadata. pyte otherwise prints Zellij's attachment
        # announcements over pane contents, even when they span multiple reads.
        data = re.sub(r"\x1bP.*?\x1b\\", "", self.pending + data, flags=re.DOTALL)
        tail = re.search(r"\x1b(?:P.*|\[>?[0-9:;]*)?\Z", data, flags=re.DOTALL)
        self.pending = tail[0] if tail else ""
        complete = data[:tail.start()] if tail else data
        # pyte parses colon-separated SGR parameters as printable characters.
        complete = re.sub(r"\x1b\[58:2::(\d+):(\d+):(\d+)m", "\x1b" + r"[58;2;\1;\2;\3m", complete)
        super().feed(re.sub(r"\x1b\[>[0-9;]*m", "", complete))


class ReviewStream(NativeStream):
    def __init__(self, screen):
        self.metadata = TerminalMetadata()
        super().__init__(screen)

    def feed(self, data):
        super().feed(self.metadata.feed(data))


class NativeScreen(pyte.Screen):
    def back_tab(self, count=1):
        stops = sorted((stop for stop in self.tabstops if stop < self.cursor.x), reverse=True)
        n = max(1, count)
        self.cursor.x = stops[n - 1] if len(stops) >= n else 0

    def resize(self, lines=None, columns=None):
        old_width = self.columns
        super().resize(lines=lines, columns=columns)
        # pyte keeps its initial stops forever. xterm extends the eight-column
        # tab grid on growth and cannot move the cursor past a shrunken edge.
        self.tabstops.intersection_update(range(self.columns))
        self.tabstops.update(range(max(8, (old_width + 7) // 8 * 8), self.columns, 8))

    def report_device_status(self, mode, **kwargs):
        if not kwargs.get("private"):
            super().report_device_status(mode)


# pyte 0.8.2 tracks whether a cell is underlined, but discards SGR 58/59.
ZellijCell = namedtuple("ZellijCell", [*pyte.screens.Char._fields, "underline_color"])


class ZellijScreen(NativeScreen):
    @property
    def default_char(self):
        return ZellijCell(*super().default_char, "default")

    def reset(self):
        super().reset()
        self.cursor.attrs = self.default_char

    def select_graphic_rendition(self, *attrs):
        if attrs[:2] == (58, 2) and len(attrs) == 5:
            color = "{:02x}{:02x}{:02x}".format(*attrs[2:])
            self.cursor.attrs = self.cursor.attrs._replace(underline_color=color)
        elif attrs == (59,):
            self.cursor.attrs = self.cursor.attrs._replace(underline_color="default")
        else:
            super().select_graphic_rendition(*attrs)


def cells(screen, lines):
    attributes = ("data", "fg", "bg", "bold", "italics", "underscore", "reverse")
    if isinstance(screen, ZellijScreen):
        attributes += ("underline_color",)
    return [[{key: getattr(screen.buffer[row][col], key) for key in attributes}
             for col in range(screen.columns)] for row in range(lines)]


def ansi_cells(text, columns=76, lines=10, *, review=False):
    screen = NativeScreen(columns, lines)
    (ReviewStream if review else NativeStream)(screen).feed(text.replace("\n", "\r\n"))
    return cells(screen, lines)


def compact(rows):
    return review_contract.compact_grid(rows)


def stop_child_group(pid):
    def send(sig):
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            # Darwin rejects signals to a group whose leader has already exited.
            # Ignore that race only when this owned child can actually be reaped.
            if os.waitpid(pid, os.WNOHANG)[0]:
                return True
            raise
        return False

    if os.waitpid(pid, os.WNOHANG)[0] or send(signal.SIGTERM):
        return
    for _ in range(30):
        if os.waitpid(pid, os.WNOHANG)[0]:
            return
        time.sleep(0.03)
    if not send(signal.SIGKILL):
        os.waitpid(pid, 0)


class IncompleteCapture(AssertionError):
    """Keep the observed frame even when the readiness criterion fails."""

    def __init__(self, message, rows):
        super().__init__(message)
        self.rows = rows


def terminal(command, env, ready, *, columns=76, lines=24, capture_lines=10, raw_path=None):
    pid, fd = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0))
        os.chdir(env["HOME"])
        os.execvpe(command[0], command, env)
    screen = NativeScreen(columns, lines)
    stream = (ReviewStream if raw_path else NativeStream)(screen)
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    raw = bytearray()
    queries = TerminalColorQueries(json.loads((GENERATED / "colors.json").read_text())) if raw_path or command[0] == "nvim" else None
    deadline = time.monotonic() + 15
    ready_since = None
    try:
        while time.monotonic() < deadline:
            if select.select([fd], [], [], 0.01)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                raw.extend(chunk)
                if queries:
                    for reply in queries.feed(chunk):
                        os.write(fd, reply)
                stream.feed(decoder.decode(chunk))
            if ready(screen):
                if not raw_path:
                    return cells(screen, capture_lines)
                # Give asynchronous preview/status widgets time to finish.
                ready_since = ready_since or time.monotonic()
                if time.monotonic() - ready_since >= 0.25:
                    return cells(screen, capture_lines)
            else:
                ready_since = None
        message = f"Native preview did not become ready: {command[0]}\n" + "\n".join(screen.display)
        if raw_path:
            raise IncompleteCapture(message, cells(screen, capture_lines))
        raise AssertionError(message)
    finally:
        if raw_path:
            raw_path.write_bytes(raw)
        os.close(fd)
        stop_child_group(pid)


def svg(name, rows, *, trim=True):
    theme = json.loads((GENERATED / "colors.json").read_text())
    return render_svg(name, rows, theme, trim=trim)


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
local function picker_colors()
  local roles = require("dotfiles-theme").colors()
  local function foreground(name)
    return string.format("#%06X", vim.api.nvim_get_hl(0, {name = name, link = false}).fg)
  end
  assert(foreground("FzfLuaFzfMatch") == roles.match)
  assert(foreground("FzfLuaLiveSym") == roles.match)
  assert(foreground("FzfLuaFzfPointer") == roles.accent)
  assert(foreground("FzfLuaFzfMatch") ~= foreground("DiagnosticError"))
  assert(foreground("FzfLuaSymbolSignature") == roles["syntax.type"])
  assert(foreground("FzfLuaSymbolFile") == roles.text)
  assert(foreground("FzfLuaSymbolSignature") ~= foreground("FzfLuaSymbolFile"))
  assert(vim.api.nvim_get_hl(0, {name = "FzfLuaSymbolSignature"}).italic)
  assert(vim.api.nvim_get_hl(0, {name = "FzfLuaSymbolFile"}).bold)
end
picker_colors()
vim.cmd.colorscheme("dotfiles")
vim.wait(100, function() return false end)
picker_colors()
assert(vim.deep_equal(before, observed()), "Native plugin styling changes after colorscheme reload")
vim.fn.writefile({vim.json.encode(before)}, vim.env.THEME_OBSERVATIONS)
''')
    path = work / "neovim.json"
    subprocess.run(["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l", str(script)], env={**env, "THEME_ROOT": str(ROOT), "THEME_PLUGINS": str(plugins), "THEME_OBSERVATIONS": str(path)}, check=True, capture_output=True, text=True)
    return json.loads(path.read_text())


def run(surface, work, env, plugins, *, raw_path=None, treesitter_site=None):
    review = raw_path is not None

    def observed_ansi(text, *, columns=76, lines=10):
        if raw_path:
            raw_path.write_text(text)
        return ansi_cells(text, columns, lines, review=review)

    if surface == "atuin":
        if not review:
            raise ValueError("Atuin capture requires --review-dir")
        # Use only a disposable history database; never sync or execute commands.
        config = work / "home/.config/atuin"
        themes = config / "themes"
        themes.mkdir(parents=True)
        shutil.copyfile(GENERATED / "atuin.toml", themes / "dotfiles.toml")
        data = work / "atuin-data"
        data.mkdir()
        (config / "config.toml").write_text(
            'auto_sync = false\nupdate_check = false\nstyle = "compact"\n'
            'inline_height = 0\ninvert = true\nshow_preview = true\n'
            'show_help = false\nprefers_reduced_motion = true\n'
            'filter_mode = "global"\nsearch_mode = "fuzzy"\n'
            'keymap_mode = "emacs"\nstore_failed = true\n'
            'db_path = ' + json.dumps(str(data / "history.db")) + '\n'
            'key_path = ' + json.dumps(str(data / "key")) + '\n'
            'record_store_path = ' + json.dumps(str(data / "records.db")) + '\n'
            '[theme]\nname = "dotfiles"\n')
        isolated = {**env, "ATUIN_CONFIG_DIR": str(config),
                    "ATUIN_THEME_DIR": str(themes),
                    "ATUIN_SESSION": "00000000000000000000000000000001"}
        fixture = tomllib.loads((ROOT / "design-system/fixtures/atuin.toml").read_text())
        for entry in fixture["history"]:
            history_id = subprocess.check_output(
                ["atuin", "history", "start", "--", entry["command"]],
                env=isolated, cwd=env["HOME"], text=True).strip()
            subprocess.run(["atuin", "history", "end", "--exit", str(entry["exit"]),
                            "--duration", str(entry["duration_ns"]), "--", history_id],
                           env=isolated, cwd=env["HOME"], check=True, capture_output=True)
        anchors = ("git status --short", "git diff --stat", "git log --oneline -10", "git fetch --prune")
        return terminal(["atuin", "search", "--interactive", "--", "git"],
                        isolated, lambda screen: all(a in "\n".join(screen.display) for a in anchors),
                        columns=112, lines=25, capture_lines=25, raw_path=raw_path)

    if "-code-" in surface:
        if not review:
            raise ValueError("language captures require --review-dir")
        app, language = surface.split("-code-", 1)
        policy = tomllib.loads(review_contract.CONTRACT.read_text())
        fixture = policy["languages"][language]
        source = ROOT / fixture["file"]
        if app == "neovim":
            script = work / "language-review.lua"
            script.write_text('''
if vim.env.THEME_TREESITTER_SITE then
  local ok, err = pcall(function()
    vim.opt.runtimepath:prepend(vim.env.THEME_TREESITTER_SITE)
    vim.treesitter.language.register("bash", "sh")
    local language = vim.treesitter.language.get_lang(vim.bo.filetype)
    assert(language and vim.treesitter.query.get(language, "highlights"), "missing highlight query")
    vim.treesitter.start(0, language)
  end)
  if not ok then
    io.stderr:write("Tree-sitter fixture setup failed: " .. tostring(err) .. "\\n")
    vim.cmd.cquit()
  end
end
vim.opt.number = true
vim.opt.cursorline = true
vim.opt.signcolumn = "yes"
vim.opt.laststatus = 2
vim.opt.statusline = "%t %=%y"
vim.opt.showmode = false
vim.opt.ruler = false
vim.opt.tabstop = 4
local ns = vim.api.nvim_create_namespace("language-review")
vim.diagnostic.config({virtual_text = {current_line = false, prefix = "·"},
  signs = {text = {[vim.diagnostic.severity.WARN] = "!"}}})
vim.diagnostic.set(ns, 0, {{lnum = 0, col = 0,
  severity = vim.diagnostic.severity.WARN, message = "Review retry policy"}})
vim.api.nvim_win_set_cursor(0, {4, 0})
''')
            command = ["nvim", "-u", "NONE", "-i", "NONE", "-n",
                       "--cmd", "set rtp^=" + str(ROOT / "nvim"),
                       "--cmd", "set rtp+=" + str(ROOT / "nvim/after"),
                       "-c", "colorscheme dotfiles", "-c", "syntax on",
                       "-c", "set filetype=" + fixture["filetype"],
                       str(source), "-c", "luafile " + str(script)]
            anchors = policy["surfaces"][surface]["anchors"]
            if treesitter_site is not None:
                env = {**env, "THEME_TREESITTER_SITE": str(treesitter_site)}
            return terminal(command, env, lambda screen: all(
                anchor in "\n".join(screen.display) for anchor in anchors),
                columns=112, lines=24, capture_lines=24, raw_path=raw_path)
        if app == "bat":
            marker = work / "language-bat-cache-ready"
            if not marker.exists():
                subprocess.run(["bat", "cache", "--build"], env=env, check=True, capture_output=True)
                marker.touch()
            command = ["bat", "--theme=Dotfiles", "--color=always", "--paging=never",
                       "--style=numbers,header,grid", "--terminal-width=112",
                       "--language=" + fixture["bat_language"], str(source)]
            output = subprocess.check_output(command, env=env, text=True)
            return observed_ansi(output, columns=112, lines=max(24, len(output.splitlines()) + 1))
        raise ValueError(surface)

    if surface == "neovim":
        return neovim(work, env, plugins)
    if surface == "neovim-frame":
        command = ["nvim", "-u", "NONE", "-i", "NONE", "-n", "--cmd", "set rtp^=" + str(ROOT / "nvim"), "-c", "colorscheme dotfiles", "-c", "syntax on", "-c", "set noshowmode noruler laststatus=0 noshowcmd", str(ROOT / "design-system/fixtures/code.lua")]
        if review:
            script = work / "visual-review.lua"
            script.write_text('''
vim.opt.number = true
vim.opt.cursorline = true
vim.opt.signcolumn = "yes"
vim.opt.laststatus = 2
vim.opt.ruler = true
vim.opt.rtp:append(vim.env.THEME_PLUGINS .. "/lualine.nvim")
require("lualine").setup({options = {theme = require("dotfiles-theme").lualine()}})
local ns = vim.api.nvim_create_namespace("theme-review")
vim.diagnostic.config({virtual_text = {current_line = false, prefix = "·"}, signs = true})
vim.diagnostic.set(ns, 0, {
  {lnum = 1, col = 0, severity = vim.diagnostic.severity.WARN, message = "Review retry budget"},
  {lnum = 5, col = 2, severity = vim.diagnostic.severity.ERROR, message = "Fixture diagnostic"},
})
vim.api.nvim_win_set_cursor(0, {4, 4})
''')
            command += ["-c", "luafile " + str(script)]
            return terminal(command, {**env, "THEME_PLUGINS": str(plugins)},
                            lambda screen: "Review retry budget" in "\n".join(screen.display)
                            and "Fixture diagnostic" in "\n".join(screen.display)
                            and "code.lua" in "\n".join(screen.display),
                            columns=104, lines=15, capture_lines=15, raw_path=raw_path)
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
        # Keep machine-specific notices and status modules outside this narrow fixture.
        # Its fixed name is isolated by the private socket directory.
        name, columns, lines = ("work", 100, 16) if review else ("work", 28, 8)
        client = workflow.Terminal(shutil.which("zellij"), native_env, name, install_navigation=False)
        screen = ZellijScreen(120, 32)
        stream = (ReviewStream if review else NativeStream)(screen)
        decoder, offset = codecs.getincrementaldecoder("utf-8")("replace"), 0
        def update_screen():
            nonlocal offset
            stream.feed(decoder.decode(bytes(client.output[offset:])))
            offset = len(client.output)

        def ready():
            update_screen()
            return ("0:Shell" in screen.display[0] and "!?" not in screen.display[0]
                    and screen.display[2].strip("│ ") == workflow.PROMPT.decode().strip()
                    and all(screen.buffer[0][x].underscore for x in range(columns))
                    and screen.buffer[lines - 1][columns - 1].fg == screen.buffer[0][5].underline_color
                    and (not review or all(name in screen.display[0] for name in ("Editor", "Publisher"))))
        try:
            client.grant_status_permissions()
            client.until("theme fixture shell ready", lambda: workflow.PROMPT in client.output)
            client.action("rename-pane", "Shell")
            if review:
                client.action("new-tab", "--name", "Editor", "--no-focus")
                client.action("new-tab", "--name", "Publisher", "--no-focus")
            update_screen()
            screen.resize(lines=lines, columns=columns)
            fcntl.ioctl(client.fd, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0))
            # Remove shell-specific startup text before recording the pane.
            client.send(b"printf '\\033[2J\\033[H'\r")
            client.send(b"\x06")
            try:
                client.until("native themed prefix", ready)
            except AssertionError as error:
                if raw_path:
                    update_screen()
                    raise IncompleteCapture(str(error), cells(screen, lines)) from error
                raise
            return cells(screen, lines)
        finally:
            if raw_path:
                raw_path.write_bytes(client.output)
            subprocess.run(["zellij", "kill-session", name], env=native_env, capture_output=True, timeout=5)
            client.close()
    if surface == "cli":
        command = [str(ROOT / "bin/dotfiles-theme"), "--color=always"]
        if review:
            command.append("--catalog")
        text = subprocess.check_output(command, env=env, text=True)
        return observed_ansi(text, columns=120 if review else 76,
                             lines=len(text.splitlines()) + 1 if review else 10)
    if surface in ("bat", "delta"):
        cache = subprocess.run(["bat", "cache", "--build"], env=env, capture_output=True, text=True)
        if cache.returncode:
            raise AssertionError(cache.stderr)
        text = subprocess.check_output(["bat", "--list-themes", "--color=never"], env=env, text=True)
        assert "Dotfiles" in text, "bat did not register the generated syntax theme"
        if surface == "bat":
            source = ROOT / "design-system/fixtures/code.lua"
            command = ["bat", "--theme=Dotfiles", "--color=always", "--paging=never", "--style=plain", "--language=lua", source.name]
            if review:
                command[4] = "--style=numbers,header,grid"
                command.insert(-1, "--terminal-width=96")
            text = subprocess.check_output(command, cwd=source.parent, env=env, text=True)
        else:
            themes = subprocess.check_output(["delta", "--list-syntax-themes"], env=env, text=True)
            assert "Dotfiles" in themes, "delta cannot read the generated bat theme cache"
            command = ["delta", "--paging=never", "--width=96" if review else "--width=76", "--true-color=always"]
            if review:
                # Line numbers exercise a richer native mode. Sage's actual
                # generated config, not the review invocation, retains +/-.
                command.append("--line-numbers")
            text = subprocess.check_output(command, env=env, cwd=env["HOME"], input=(ROOT / "design-system/fixtures/change.diff").read_text(), text=True)
        rows = observed_ansi(text, columns=96 if review else 76, lines=24 if review else 10)
        return rows
    if surface == "glow":
        document = ROOT / "design-system/fixtures/document.md"
        if review:
            document = work / "review.md"
            document.write_text("""# Service inspection

Review **api** and its [runbook](https://example.com/runbook) before publishing.

## Release checklist

- [x] Configuration validated
- [ ] Approval pending

| Service | Status | Evidence |
| --- | --- | --- |
| api | Ready | Current |
| worker | Failed | Stale |

> Missing data remains unknown.

Inspect the value of `retries`:

```lua
-- Retry only when the connection is transient.
local retries = 3
return retries
```
""")
        text = subprocess.check_output(["glow", "--style", str(GENERATED / "glow.json"), "--width=70", str(document)], env=env, stdin=subprocess.DEVNULL, text=True)
        return observed_ansi(text, lines=max(24, len(text.splitlines()) + 1) if review else 14)
    if surface == "fzf":
        if review:
            semantic = json.loads((GENERATED / "tokens.json").read_text())["semantic_states"]
            candidates = work / "review-picker.tsv"
            preview = work / "review-preview.txt"
            items = [
                ("execution.input", "Publish release"),
                ("execution.running", "Compile workspace"),
                ("execution.failed", "Run integration tests"),
                ("execution.blocked", "Await upstream check"),
                ("execution.succeeded", "Validate configuration"),
                ("execution.queued", "Generate release notes"),
            ]
            lines = []
            for i, (key, label) in enumerate(items):
                token = semantic[key]
                rgb = ";".join(str(int(token["fg"][j:j+2], 16)) for j in (1, 3, 5))
                lines.append(f'{i}\t\033[38;2;{rgb}m{token["symbol"]} {token["label"]:<12}\033[0m  {label}')
            candidates.write_text("\n".join(lines) + "\n")
            preview.write_text("TASK DETAILS\n\nPublish release\nAuthorization required\n\nRepository: workspace\nChecks: 12 passed\n")
            command = ["bash", "-c", '''"$1" --ansi --no-multi --no-sort --delimiter="\\t" --with-nth=2.. --reverse --info=hidden --header="Workspace tasks" --prompt="Search > " --preview='cat "$THEME_REVIEW_PREVIEW"' --preview-window=right:45% < "$2"''',
                       "bash", str(ROOT / "bin/dotfiles-fzf"), str(candidates)]
            return terminal(command, {**env, "THEME_REVIEW_PREVIEW": str(preview)},
                            lambda screen: all(label in "\n".join(screen.display)
                                               for label in ("Publish release", "FAILED", "TASK DETAILS")),
                            columns=108, lines=16, capture_lines=16, raw_path=raw_path)
        command = ["bash", "-c", 'printf "api\\tapi OK\\nworker\\tworker ERROR\\n" | "$1" --no-multi --delimiter="\\t" --with-nth=2.. --reverse --info=hidden --header="Services" --prompt="Search > "', "bash", str(ROOT / "bin/dotfiles-fzf")]
        return terminal(command, env, lambda screen: "worker ERROR" in "\n".join(screen.display))
    if surface == "bottom":
        if review:
            def selected_row_ready(screen):
                # Readiness is content, never compliance with a desired color.
                # The independent audit owns row coverage, ink and fill.
                header = next((y for y, line in enumerate(screen.display)
                               if "Name(n)" in line and "CPU%" in line), None)
                return header is not None and any(
                    re.search(r"\d+(?:\.\d+)?%.*\d+(?:\.\d+)?%", line)
                    for line in screen.display[header + 1:])

            return terminal(["btm", "--config_location", str(GENERATED / "bottom.toml"), "--basic"],
                            env, selected_row_ready, columns=100, lines=18,
                            capture_lines=18, raw_path=raw_path)
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
            if review:
                tmux("rename-window", "Editor")
                tmux("set-option", "-w", "@claude-state", "thinking")
                tmux("set-option", "-w", "@claude-glyph", "◐")
                tmux("respawn-pane", "-k", "printf 'Workspace review\\n\\nReady to inspect changes.\\n'; sleep 60")
                tmux("new-window", "-d", "-n", "Publisher", "sleep 60")
                tmux("set-option", "-w", "-t", "fixture:Publisher", "@claude-state", "failed")
                tmux("set-option", "-w", "-t", "fixture:Publisher", "@claude-glyph", "×")
                tmux("new-window", "-d", "-n", "Checks", "sleep 60")
                tmux("set-option", "-w", "-t", "fixture:Checks", "@claude-state", "approval")
                tmux("set-option", "-w", "-t", "fixture:Checks", "@claude-glyph", "!")
                tmux("new-window", "-d", "-n", "Shell", "sleep 60")
                def tabs_ready(screen):
                    # A bad tab must still produce a counterexample.
                    return all(label in "\n".join(screen.display)
                               for label in ("Workspace review", "Editor", "Publisher", "Checks", "Shell"))

                return terminal(["tmux", "-S", socket, "attach-session", "-t", "fixture"], env,
                                tabs_ready, columns=112, lines=16,
                                capture_lines=16, raw_path=raw_path)
            return observations
        finally:
            subprocess.run(["tmux", "-S", socket, "kill-server"], env=env, capture_output=True)
    raise ValueError(surface)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    base_surfaces = ["kitty", "neovim", "neovim-frame", "zellij", "tmux", "cli", "fzf", "bat", "delta", "glow", "bottom"]
    parser.add_argument("--surface", action="append")
    parser.add_argument("--profile", choices=("theme", "zellij"),
                        help="Capture every required surface in a native review profile")
    parser.add_argument("--plugins-dir", type=Path, default=Path.home() / ".local/share/nvim/lazy")
    parser.add_argument("--treesitter-site", type=Path,
                        help="Use installed parsers and queries from this runtime directory in Neovim language captures")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--record", action="store_true", help="Explicitly replace observed baselines; inspect changes before accepting them")
    mode.add_argument("--review-dir", type=Path, help="Write unapproved native review evidence outside regression baselines")
    args = parser.parse_args()
    metadata = json.loads((GENERATED / "colors.json").read_text())
    preset = metadata["theme"]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", preset):
        parser.error("invalid generated theme name")
    symbols = metadata.get("symbols", "unicode")
    if symbols not in ("unicode", "ascii"):
        parser.error("invalid generated symbols representation")
    variant = Path("ascii") if symbols == "ascii" else Path()
    baselines = ROOT / "design-system/baselines" / preset / variant
    if args.review_dir:
        args.review_dir.mkdir(parents=True, exist_ok=True)
    evidence = {"preset": preset, "symbols": symbols,
                "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() if args.review_dir else None,
                "run_id": os.environ.get("GITHUB_RUN_ID"), "mode": "native-review", "surfaces": {}}
    failures = []
    if args.profile and (not args.review_dir or args.surface):
        parser.error("--profile requires --review-dir and cannot be combined with --surface")
    if args.review_dir:
        policy = tomllib.loads(review_contract.CONTRACT.read_text())
        allowed = set(base_surfaces) | set(policy["surfaces"])
        surfaces = policy["profiles"][args.profile] if args.profile else (args.surface or base_surfaces)
    else:
        allowed = set(base_surfaces)
        surfaces = args.surface or base_surfaces
    if any(surface not in allowed for surface in surfaces):
        parser.error("unknown surface or language capture outside review mode")
    treesitter_site = args.treesitter_site.resolve() if args.treesitter_site else None
    if treesitter_site is not None:
        if not args.review_dir or not any(surface.startswith("neovim-code-") for surface in surfaces):
            parser.error("--treesitter-site requires a Neovim language review capture")
        if not treesitter_site.is_dir():
            parser.error("--treesitter-site must be an existing directory")
    neovim_syntax = "treesitter" if treesitter_site is not None else "vim"
    if args.review_dir:
        if len(set(surfaces)) != len(surfaces):
            parser.error("review surfaces must be unique")
        policy = tomllib.loads(review_contract.CONTRACT.read_text())
        shutil.copyfile(review_contract.CONTRACT, args.review_dir / "review-contract.toml")
        shutil.copyfile(GENERATED / "colors.json", args.review_dir / "colors.json")
        evidence.update(
            schema=2, approval="unreviewed", required_surfaces=surfaces, neovim_syntax=neovim_syntax,
            contract_sha256=review_contract.sha256(review_contract.CONTRACT),
            colors_sha256=review_contract.sha256(GENERATED / "colors.json"),
            auditor_sha256=review_contract.sha256(Path(review_contract.__file__)),
            renderer_sha256=review_contract.sha256(Path(__file__).with_name("theme_review.py")),
        )
    with tempfile.TemporaryDirectory(prefix="theme-native-", dir="/tmp") as temporary:
        work = Path(temporary).resolve()
        home = work / "home"
        for name in (".config/bat/themes", ".config/dotfiles", ".cache", ".local/share"):
            (home / name).mkdir(parents=True, exist_ok=True)
        (home / ".config/dotfiles/theme").symlink_to(GENERATED)
        shutil.copyfile(GENERATED / "Dotfiles.tmTheme", home / ".config/bat/themes/Dotfiles.tmTheme")
        shutil.copytree(ROOT / "bat/syntaxes", home / ".config/bat/syntaxes")
        (home / ".gitconfig").write_text('[include]\npath = ' + str(GENERATED / 'delta.gitconfig') + '\n[delta]\nfeatures = dotfiles\n')
        locale = "C.UTF-8" if sys.platform.startswith("linux") else "en_US.UTF-8"
        env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache"), "XDG_DATA_HOME": str(home / ".local/share"), "BAT_CONFIG_DIR": str(home / ".config/bat"), "BAT_CACHE_PATH": str(home / ".cache/bat"), "TERM": "xterm-256color", "COLORTERM": "truecolor", "CLICOLOR_FORCE": "1", "DOTFILES_THEME_DIR": str(GENERATED), "LANG": locale, "LC_ALL": locale}
        for name in ("TMUX", "TMUX_PANE", "NO_COLOR", "FZF_DEFAULT_OPTS", "FZF_DEFAULT_OPTS_FILE", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "BAT_THEME", "DELTA_FEATURES", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "THEME_TREESITTER_SITE"):
            env.pop(name, None)
        # Delta reads Git configuration via Git; isolate it from the checkout and host.
        env["GIT_CONFIG_GLOBAL"] = str(home / ".gitconfig")
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        for surface in surfaces:
            raw_path = args.review_dir / (surface + ".ansi") if args.review_dir else None
            incomplete = None
            try:
                observed = run(surface, work, env, args.plugins_dir, raw_path=raw_path, treesitter_site=treesitter_site)
            except IncompleteCapture as error:
                if not args.review_dir:
                    raise
                failures.append(surface)
                incomplete = str(error)
                observed = error.rows
            except Exception as error:
                if not args.review_dir:
                    raise
                failures.append(surface)
                detail = {"status": "failed", "error": str(error), "contract_status": "fail"}
                if raw_path.exists():
                    detail.update(ansi=raw_path.name, sha256={raw_path.name: review_contract.sha256(raw_path)})
                evidence["surfaces"][surface] = detail
                print(f"REVIEW FAILED {surface}: {error}", file=sys.stderr)
                continue
            terminal_rows = isinstance(observed, list) and observed and isinstance(observed[0], list)
            snapshot = compact(observed) if terminal_rows else observed
            baseline = baselines / f"{surface}.json"
            if args.review_dir:
                snapshot_name = surface + ".json"
                (args.review_dir / snapshot_name).write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
                detail = {"status": "captured", "cells": snapshot_name, "contract_status": "not-visual"}
                if incomplete is not None:
                    detail.update(status="capture-failed", error=incomplete, contract_status="fail")
                if raw_path.exists():
                    detail["ansi"] = raw_path.name
                if terminal_rows:
                    grid = args.review_dir / (surface + ".grid.json")
                    grid.write_text(json.dumps(observed, separators=(",", ":"), ensure_ascii=False) + "\n")
                    detail.update(grid=grid.name, rows=len(observed), columns=len(observed[0]))
                    capture = args.review_dir / (surface + ".svg")
                    report_path = args.review_dir / (surface + ".audit.json")
                    try:
                        audit = review_contract.audit_capture(surface, observed, metadata, policy, neovim_syntax=neovim_syntax)
                        report_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
                        detail.update(audit=report_path.name, contract_status="fail" if incomplete is not None else audit["status"])
                        for check in audit["checks"]:
                            if not check["passed"]:
                                print(f"REVIEW FAIL {surface}/{check['id']}: {json.dumps(check['observed'], ensure_ascii=False)}", file=sys.stderr)
                        if audit["status"] != "pass":
                            failures.append(surface)
                        # Preserve the failed image for diagnosis, rather than dropping it.
                        capture.write_text(svg(surface, observed, trim=surface not in ("zellij", "bottom", "tmux")))
                        detail["svg"] = capture.name
                    except Exception as error:
                        failures.append(surface)
                        detail.update(status="render-failed", contract_status="fail", error=str(error))
                        print(f"REVIEW EVIDENCE FAILED {surface}: {error}", file=sys.stderr)
                detail["sha256"] = {detail[key]: review_contract.sha256(args.review_dir / detail[key])
                                    for key in ("cells", "grid", "ansi", "svg", "audit") if key in detail}
                evidence["surfaces"][surface] = detail
                print(f"REVIEW {surface}: captured, contract={detail['contract_status']}, visual approval=pending")
            elif args.record:
                baselines.mkdir(parents=True, exist_ok=True)
                baseline.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
                if terminal_rows:
                    capture = ROOT / "docs/design-system/presets" / preset / variant / f"{surface}.svg"
                    capture.parent.mkdir(parents=True, exist_ok=True)
                    capture.write_text(svg(surface, observed))
                print(f"RECORDED {surface}: inspect baseline and native capture")
            else:
                expected = json.loads(baseline.read_text())
                if snapshot != expected:
                    difference = "\n".join(difflib.unified_diff(json.dumps(expected, indent=2, sort_keys=True).splitlines(), json.dumps(snapshot, indent=2, sort_keys=True).splitlines(), fromfile="expected", tofile="observed", lineterm=""))
                    raise AssertionError(f"{surface}: native style regression against {baseline.relative_to(ROOT)}\n{difference}")
                print(f"PASS {surface}: native styling and baseline agree")
    if args.review_dir:
        (args.review_dir / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n")
        if failures:
            raise SystemExit("Native visual review failed: " + ", ".join(dict.fromkeys(failures)))


if __name__ == "__main__":
    main()
