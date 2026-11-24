#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pynvim==0.6.0", "pillow==12.0.0"]
# ///
"""Render Neovim grid captures using the full editor config and a disposable Beads fixture."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
from http.server import ThreadingHTTPServer

import pynvim
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


class Screen:
    def __init__(self, width, height, background):
        self.width, self.height = width, height
        self.terminal_background = background
        self.cells = [[(" ", 0) for _ in range(width)] for _ in range(height)]
        self.attributes = {0: {}}
        self.defaults = dict(foreground=0xD8DEE9, background=background)
        self.cursor = (0, 0)
        self.inherit_terminal_background = False

    def notification(self, name, updates):
        if name != "redraw":
            return
        for update in updates:
            kind = update[0]
            for event in update[1:]:
                if kind == "hl_attr_define":
                    self.attributes[event[0]] = event[1]
                elif kind == "default_colors_set":
                    for key, value in zip(("foreground", "background", "special"), event):
                        self.defaults[key] = (self.terminal_background if key == "background" and self.inherit_terminal_background
                                              else value if value >= 0 else (self.terminal_background if key == "background" else 0xD8DEE9))
                elif kind == "grid_line" and event[0] == 1:
                    _, row, col, values, *_ = event
                    current = 0
                    for cell in values:
                        if len(cell) > 1:
                            current = cell[1]
                        for _ in range(cell[2] if len(cell) > 2 else 1):
                            self.cells[row][col] = (cell[0], current)
                            col += 1
                elif kind == "grid_clear" and event[0] == 1:
                    self.cells = [[(" ", 0) for _ in range(self.width)] for _ in range(self.height)]
                elif kind == "grid_scroll" and event[0] == 1:
                    _, top, bottom, left, right, rows, cols = event
                    previous = [line[:] for line in self.cells]
                    for row in range(top, bottom):
                        for col in range(left, right):
                            source_row, source_col = row + rows, col + cols
                            self.cells[row][col] = (previous[source_row][source_col]
                                                    if top <= source_row < bottom and left <= source_col < right else (" ", 0))
                elif kind == "grid_cursor_goto" and event[0] == 1:
                    self.cursor = event[1], event[2]

    def save(self, destination, fonts):
        size, line_height, padding = 18, 25, 16
        regular = ImageFont.truetype(str(fonts / "HackNerdFontMono-Regular.ttf"), size)
        bold = ImageFont.truetype(str(fonts / "HackNerdFontMono-Bold.ttf"), size)
        cell_width = regular.getlength("M")
        image = Image.new("RGB", (round(self.width * cell_width) + padding * 2,
                                  self.height * line_height + padding * 2), color=f"#{self.terminal_background:06x}")
        draw = ImageDraw.Draw(image)
        visible_colors = set()
        for row, values in enumerate(self.cells):
            for col, (text, identity) in enumerate(values):
                style = {**self.defaults, **self.attributes[identity]}
                fg, bg = style["foreground"], style["background"]
                if style.get("reverse"):
                    fg, bg = bg, fg
                x, y = padding + col * cell_width, padding + row * line_height
                draw.rectangle((round(x), y, round(x + cell_width), y + line_height), fill=f"#{bg:06x}")
                if text and text != " ":
                    visible_colors.add(fg)
                    draw.text((x, y), text, font=bold if style.get("bold") else regular, fill=f"#{fg:06x}")
        assert len(visible_colors) >= 6, "Capture lost Neovim's semantic foreground colors"
        image.save(destination.with_suffix(".png"))
        destination.with_suffix(".txt").write_text("\n".join("".join(c[0] for c in row).rstrip() for row in self.cells) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fonts", type=Path, default=Path.home() / "Library/Fonts")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/screenshots/neovim-beads")
    parser.add_argument("--terminal-theme", type=Path, default=Path.home() / ".config/dotfiles/theme/kitty.conf")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("beads_fixture", ROOT / "scripts/test-nvim-beads.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    state = fixture.Boundary()
    def task(identity, title, status):
        value = fixture.task(identity, title)
        value["status"] = status
        return value
    state.tasks = {
        "trial-authoring": task("trial-authoring", "Native task authoring", "in_progress"),
        "trial-tree": task("trial-tree", "Tree and keyboard navigation", "closed"),
        "trial-theme": task("trial-theme", "Theme and status indicators", "in_progress"),
        "trial-buffers": task("trial-buffers", "Editable task documents", "open"),
        "trial-runtime": task("trial-runtime", "Studio integration", "blocked"),
        "trial-admission": task("trial-admission", "Review the accepted brief", "open"),
        "trial-recovery": task("trial-recovery", "Recover an uncertain save", "deferred"),
    }
    state.tasks["trial-theme"].update(
        description="\n## Problem\nTasks should feel at home in the editor.\n\n## Outcome\nClear hierarchy, readable state, and safe saves.\n\n## Scope\nUse the shared theme and keyboard navigation.\n",
        acceptance_criteria="\n- [x] Reuse the task buffer\n- [x] Preserve ownership on save\n- [ ] Review narrow layouts",
        metadata={"attention": "Review"},
    )
    state.edges = [dict(issue_id=child, depends_on_id=parent, type="parent-child", created_at="2026-11-23T00:00:00Z")
                   for child, parent in (("trial-tree", "trial-authoring"), ("trial-theme", "trial-authoring"),
                                         ("trial-buffers", "trial-authoring"), ("trial-admission", "trial-runtime"))]
    terminal_colors = dict(line.split(maxsplit=1) for line in args.terminal_theme.read_text().splitlines()
                           if line.strip() and not line.lstrip().startswith("#"))
    background = int(terminal_colors["background"].lstrip("#"), 16)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="beads-ui-") as temporary, ThreadingHTTPServer(("127.0.0.1", 0), state.handler()) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for width in (120, 64):
                screen = Screen(width, 30, background)
                nvim = pynvim.attach("child", argv=["nvim", "--embed", "--cmd",
                    "lua vim.opt.rtp:prepend(" + json.dumps(str(ROOT / "nvim")) + "); vim.g.prosession_dir=" + json.dumps(temporary + f"/sessions-{width}/"),
                    "-u", str(ROOT / "nvim/init.lua"), "-i", "NONE", "-n"])
                def notification(name, data):
                    if name == "beads_capture_ready":
                        nvim.stop_loop()
                    else:
                        screen.notification(name, data)
                def setup():
                    nvim.ui_attach(width, 30, rgb=True, ext_linegrid=True)
                    # Lazy resets runtimepath to stdpath(config); keep this assigned checkout active.
                    nvim.exec_lua('vim.opt.rtp:prepend(...)', str(ROOT / "nvim"))
                    assert nvim.exec_lua('return vim.wait(5000,function() return vim.v.vim_did_enter == 1 and vim.g.did_very_lazy end,10)'), "Editor startup did not finish"
                    normal = nvim.exec_lua('return vim.api.nvim_get_hl(0,{name="Normal",link=false})')
                    screen.inherit_terminal_background = "bg" not in normal
                    screen.defaults["background"] = normal.get("bg", background)
                    startup_error = nvim.exec_lua('return vim.v.errmsg')
                    if startup_error:
                        print("Full config startup message: " + startup_error)
                    assert nvim.exec_lua('return package.loaded["lazy"] ~= nil'), "Full editor config did not load"
                    nvim.exec_lua('local settings=...; settings.attention=function(task) return task.metadata and task.metadata.attention end; require("beads").setup({projects={personal=settings}})',
                                  dict(url=f"http://127.0.0.1:{server.server_port}", project_id=fixture.PROJECT, state_dir=temporary))
                    nvim.command("Beads personal")
                    tree_window = nvim.current.window.handle
                    assert nvim.exec_lua('return vim.wait(5000,function() return vim.b.beads_selection ~= nil end,10)'), "Beads tree did not load"
                    nvim.input("l")
                    nvim.command("BeadsOpen trial-theme")
                    assert nvim.exec_lua('return vim.wait(5000,function() return vim.b.beads_id=="trial-theme" end,10)')
                    nvim.exec_lua('vim.api.nvim_buf_set_lines(0,0,1,false,{"# Make task authoring feel native"})')
                    nvim.command("doautocmd TextChanged")
                    assert nvim.exec_lua('return vim.wait(5000,function() return require("markview.state").buf_attached(vim.api.nvim_get_current_buf()) end,10)')
                    nvim.command("Markview render")
                    nvim.api.set_current_win(tree_window)
                    nvim.exec_lua('for i,line in ipairs(vim.api.nvim_buf_get_lines(0,0,-1,false)) do if line:find("Theme") then vim.api.nvim_win_set_cursor(0,{i,0}) end end')
                    nvim.command("doautocmd CursorMoved")
                    nvim.command("redraw!")
                    nvim.exec_lua('local channel=...; vim.defer_fn(function() vim.rpcnotify(channel,"beads_capture_ready") end,1000)', nvim.channel_id)
                try:
                    nvim.run_loop(None, notification, setup_cb=setup)
                    assert any("TASKS" in "".join(c[0] for c in row) for row in screen.cells)
                    screen.save(args.output_dir / f"{width}-columns", args.fonts)
                finally:
                    try:
                        nvim.command("qa!")
                    except (EOFError, OSError):
                        pass
                    nvim.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
    print(args.output_dir)


if __name__ == "__main__":
    main()
