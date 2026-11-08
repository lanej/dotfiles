#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte==0.8.2"]
# ///
"""Exercise presentation variants through native programs and real Git states."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native", ROOT / "scripts/test-theme-native.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
PLUGINS = Path.home() / ".local/share/nvim/lazy"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="theme-presentation-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.source, self.output = self.work / "source", self.work / "output"
        shutil.copytree(ROOT / "design-system", self.source, ignore=shutil.ignore_patterns("generated", "baselines"))
        self.home = self.work / "home"
        self.home.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"), "STARSHIP_CACHE": str(self.work / "cache"), "STARSHIP_CONFIG": str(self.output / "starship.toml"), "STARSHIP_LOG": "error", "DOTFILES_THEME_DIR": str(self.output), "TERM": "xterm-256color", "COLORTERM": "truecolor", "CLICOLOR_FORCE": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        for key in ("TMUX", "TMUX_PANE", "NO_COLOR", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            self.env.pop(key, None)
        self.generate({})

    def generate(self, overrides, roles=None):
        preset = json.loads((self.source / "themes/nord.json").read_text())
        preset.update(name="variant", presentation=overrides)
        preset["roles"].update(roles or {})
        (self.source / "themes/variant.json").write_text(json.dumps(preset, ensure_ascii=False))
        subprocess.run(["python3", str(ROOT / "scripts/theme.py"), "--source", str(self.source), "--theme", "variant", "--output-dir", str(self.output)], check=True)

    def git(self, path, *args, check=True):
        return subprocess.run(["git", "-C", str(path), *args], env=self.env, check=check, capture_output=True, text=True)

    def repository(self, name="repo"):
        path = self.work / name
        path.mkdir()
        self.git(path, "init", "-q", "-b", "main")
        self.git(path, "config", "user.name", "Theme fixture")
        self.git(path, "config", "user.email", "fixture@example.invalid")
        for file in ("modified", "deleted", "renamed", "typechanged", "conflict"):
            (path / file).write_text("base\n")
        self.git(path, "add", ".")
        self.git(path, "commit", "-qm", "base")
        return path

    def module(self, path, name="git_status", raw=False):
        result = subprocess.run(["starship", "module", name, "--path", str(path)], env=self.env, stdin=subprocess.DEVNULL, check=True, capture_output=True, text=True)
        self.assertEqual(result.stderr, "")
        return result.stdout if raw else ANSI.sub("", result.stdout)

    def test_git_file_states_counts_and_literal_symbols(self):
        path = self.repository()
        self.assertEqual(self.module(path), "")
        (path / "modified").write_text("changed\n")
        (path / "deleted").unlink()
        self.git(path, "mv", "renamed", "new-name")
        (path / "typechanged").unlink()
        (path / "typechanged").symlink_to("modified")
        (path / "staged").write_text("new\n")
        self.git(path, "add", "staged")
        (path / "untracked").write_text("new\n")
        status = self.module(path)
        for expected in ("1", "1", "1", "1", "1"):
            self.assertIn(expected, status)
        self.assertRegex(status, r"(?:^| )1(?: |$)")
        default_cells = native.ansi_cells(self.module(path, raw=True), columns=256)
        modified = next(cell for row in default_cells for cell in row if cell["data"] == "")
        self.assertEqual(modified["fg"], "ebcb8b")
        self.assertFalse(modified["bold"])
        self.assertIn(" main", self.module(path, "git_branch"))
        components = json.loads((self.source / "components.json").read_text())
        components["git.file.branch"]["symbol"] = {"token": "symbol.git.file.modified"}
        (self.source / "components.json").write_text(json.dumps(components))
        self.generate({"symbol.git.file.untracked": '$[]()\\"', "symbol.git.file.modified": "M", "symbol.git.file.staged": "+", "symbol.git.file.branch": "B", "emphasis.git.file.modified.bold": True}, roles={"git.file.modified": "@status.error"})
        variant = self.module(path)
        self.assertIn('$[]()\\"1', variant)
        self.assertIn("M1", variant)
        self.assertIn("+1", variant)
        self.assertNotIn("", variant)
        changed_cells = native.ansi_cells(self.module(path, raw=True), columns=256)
        modified = next(cell for row in changed_cells for cell in row if cell["data"] == "M")
        self.assertEqual(modified["fg"], "bf616a")
        self.assertTrue(modified["bold"])
        self.assertIn("M main", self.module(path, "git_branch"))

    def test_git_stash_conflict_and_tracking_states(self):
        path = self.repository()
        (path / "modified").write_text("stashed\n")
        self.git(path, "stash", "push", "-qm", "fixture")
        self.assertIn("1", self.module(path))
        self.git(path, "checkout", "-qb", "other")
        (path / "conflict").write_text("other\n")
        self.git(path, "commit", "-qam", "other")
        self.git(path, "checkout", "-q", "main")
        (path / "conflict").write_text("main\n")
        self.git(path, "commit", "-qam", "main")
        self.assertNotEqual(self.git(path, "merge", "other", check=False).returncode, 0)
        self.assertIn("1", self.module(path))
        remote = self.work / "remote.git"
        self.git(path, "init", "--bare", "-q", str(remote))
        tracked = self.repository("tracked")
        self.git(tracked, "remote", "add", "origin", str(remote))
        self.git(tracked, "push", "-qu", "origin", "main")
        peer = self.work / "peer"
        self.git(tracked, "clone", "-q", "-b", "main", str(remote), str(peer))
        self.git(peer, "config", "user.name", "Theme fixture")
        self.git(peer, "config", "user.email", "fixture@example.invalid")
        (peer / "remote-file").write_text("remote\n")
        self.git(peer, "add", ".")
        self.git(peer, "commit", "-qm", "remote")
        self.git(peer, "push", "-q")
        self.git(tracked, "fetch", "-q")
        self.assertIn("1", self.module(tracked))
        (tracked / "local-file").write_text("local\n")
        self.git(tracked, "add", ".")
        self.git(tracked, "commit", "-qm", "local")
        diverged = self.module(tracked)
        self.assertIn("1", diverged)
        self.assertIn("1", diverged)
        self.git(tracked, "merge", "--no-edit", "origin/main")
        self.assertIn("2", self.module(tracked))
        self.assertNotIn("", self.module(tracked))

    def test_heading_padding_and_separator_native_overrides(self):
        self.generate({"emphasis.heading": False, "space.inline": 3, "symbol.separator.section.left": ">", "symbol.git.hunk.change": "~", "symbol.git.staged_hunk.change": ":", "symbol.git.branch_hunk.change": "+"}, roles={"diff.change": "@status.error", "diff.change.dim": "@status.success"})
        glow = subprocess.check_output(["glow", "--style", str(self.output / "glow.json"), "--width=70", str(ROOT / "design-system/fixtures/document.md")], env=self.env, stdin=subprocess.DEVNULL, text=True)
        rows = native.ansi_cells(glow, lines=14)
        heading = [cell for row in rows for cell in row if cell["bg"] == "88c0d0" and cell["data"].strip()]
        self.assertTrue(heading)
        self.assertTrue(all(not cell["bold"] for cell in heading))
        self.assertIn("   dotfiles-theme   ", ANSI.sub("", subprocess.check_output(["glow", "--style", str(self.output / "glow.json"), "--width=70", "-"], input="`dotfiles-theme`", env=self.env, text=True)))
        socket = str(self.work / "tmux.sock")
        tmux = ["tmux", "-S", socket]
        subprocess.run([*tmux, "-f", str(self.output / "tmux.conf"), "new-session", "-d", "-s", "fixture"], env=self.env, check=True, capture_output=True)
        try:
            label = subprocess.check_output([*tmux, "display-message", "-p", "#{E:status-left}"], env=self.env, text=True)
            self.assertIn("   fixture   ", label)
            self.assertIn(">", label)
            self.assertNotIn("", label)
        finally:
            subprocess.run([*tmux, "kill-server"], env=self.env, capture_output=True)
        path = self.repository()
        script = self.work / "presentation.lua"
        script.write_text('''
vim.opt.rtp:prepend(vim.env.THEME_ROOT .. "/nvim")
for _, plugin in ipairs({"gitsigns.nvim", "lualine.nvim"}) do
  vim.opt.rtp:append(vim.env.THEME_PLUGINS .. "/" .. plugin)
end
local theme = require("dotfiles-theme")
theme.setup()
require("lualine").setup({options = theme.lualine_options()})
require("gitsignsconfig")
vim.cmd.edit(vim.env.THEME_REPOSITORY .. "/modified")
vim.api.nvim_buf_set_lines(0, 0, -1, false, {"changed"})
assert(vim.wait(3000, function()
  for _, namespace in pairs(vim.api.nvim_get_namespaces()) do
    for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(0, namespace, 0, -1, {details = true})) do
      if mark[4].sign_text and vim.trim(mark[4].sign_text) == "~" then return true end
    end
  end
  return false
end), "Gitsigns did not render the overridden hunk symbol")
require("git-branch-signs").render(0, "base\\n")
local ns = vim.api.nvim_get_namespaces()["git-branch-signs"]
assert(vim.trim(vim.api.nvim_buf_get_extmarks(0, ns, 0, -1, {details = true})[1][4].sign_text) == "+")
local function check()
  assert(not vim.api.nvim_get_hl(0, {name = "Title", link = false}).bold)
  assert(require("gitsigns.config").config.signs.change.text == "~")
  assert(vim.api.nvim_get_hl(0, {name = "GitSignsChange", link = false}).fg == 0xBF616A)
  assert(vim.api.nvim_get_hl(0, {name = "GitSignsStagedChange", link = false}).fg == 0xA3BE8C)
  assert(vim.api.nvim_get_hl(0, {name = "DotfilesGitBranchChange", link = false}).fg == 0xA3BE8C)
  assert(require("gitsigns.config").config.signs_staged.change.text == ":")
  assert(require("lualine").get_config().options.section_separators.left == ">")
end
check()
local compiled = dofile(vim.env.DOTFILES_THEME_DIR .. "/neovim.lua")
compiled.highlights.Title.bold = true
compiled.components["git.hunk.change"].symbol = "!"
compiled.components["git.branch_hunk.change"].symbol = ":"
compiled.separators.section.left = "<"
vim.fn.writefile(vim.split("return " .. vim.inspect(compiled), "\\n", {plain = true}), vim.env.DOTFILES_THEME_DIR .. "/neovim.lua")
vim.cmd.colorscheme("dotfiles")
assert(vim.api.nvim_get_hl(0, {name = "Title", link = false}).bold)
assert(require("gitsigns.config").config.signs.change.text == "!")
assert(require("lualine").get_config().options.section_separators.left == "<")
assert(vim.wait(3000, function()
  for _, namespace in pairs(vim.api.nvim_get_namespaces()) do
    for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(0, namespace, 0, -1, {details = true})) do
      if mark[4].sign_text and vim.trim(mark[4].sign_text) == "!" then return true end
    end
  end
  return false
end), "Gitsigns did not refresh rendered signs after colorscheme reload")
require("git-branch-signs").render(0, "base\\n")
assert(vim.trim(vim.api.nvim_buf_get_extmarks(0, ns, 0, -1, {details = true})[1][4].sign_text) == ":")
''')
        result = subprocess.run(["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l", str(script)], env={**self.env, "THEME_ROOT": str(ROOT), "THEME_PLUGINS": str(PLUGINS), "THEME_REPOSITORY": str(path)}, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugins-dir", type=Path, default=PLUGINS)
    args, remaining = parser.parse_known_args()
    PLUGINS = args.plugins_dir
    unittest.main(argv=[__file__, *remaining])
