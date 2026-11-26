"""Styled, read-only hint overlay. Routing stays in select_hint.py."""
import marshal
import os
import sys
from functools import lru_cache

from kittens.hints.main import on_mark_clicked
from kittens.tui.handler import Handler, result_handler
from kittens.tui.loop import Loop
from kittens.tui.operations import MouseTracking
from kitty.fast_data_types import Screen, get_options, wcswidth


from hint_renderer import (ALPHABET, ESC, RESET, OSC8, ST, COLOR_CACHE, FrameRenderer,
                           active_cells, contrast, dimmed, labels, luminance, mix, readable,
                           render, rgb, sgr, encode_session, decode_session)
import re

URL_MASK = bytes(1 if i & 2 else 0 for i in range(256))
URL_RUN = re.compile(b"\x01+")


def encode_snapshot(model):
    # Only locally constructed primitive data crosses this pipe, and both
    # processes use the same pinned Kitty/Python runtime. Avoid JSON's decimal
    # conversion, repeated escaping, and text decoding.
    return marshal.dumps(model)


def decode_snapshot(data):
    return marshal.loads(data, allow_code=False)


def source_snapshot(screen, rows):
    """Read Kitty's resolved cell attributes, not a stripped ANSI transcript."""
    opts = get_options()
    profile = screen.color_profile
    base_fg, base_bg = int(profile.default_fg), int(profile.default_bg)

    @lru_cache(maxsize=COLOR_CACHE)
    def resolve(value, fallback):
        color = profile.as_color(value)
        return fallback if color is None else int(color)

    palette = {
        "foreground": base_fg,
        "background": base_bg,
        "target": int(opts.color0),
        "key_bg": int(opts.selection_background),
        "key_fg": int(opts.color3),
        "accent": int(opts.url_color),
    }
    cells, wrapped = [], []
    for y, row in enumerate(rows):
        line = screen.visual_line(y)
        wrapped.append(line.last_char_has_wrapped_flag())
        result = []
        for x, (char, _) in enumerate(row):
            if not char:
                result.append(None)
                continue
            cur = line.cursor_from(x)
            fg = resolve(cur.fg, base_fg)
            bg = resolve(cur.bg, base_bg)
            if cur.reverse:
                fg, bg = bg, fg
            if cur.dim:
                fg = mix(fg, bg, float(opts.dim_opacity))
            flags = int(cur.bold) | (int(cur.italic) << 1) | (int(cur.strikethrough) << 2)
            decoration = int(cur.decoration)
            deco_fg = resolve(cur.decoration_fg, fg)
            # Tabs and NULs occupy cells, not cursor movement in the overlay.
            char = char.replace("\t", " ").replace("\x00", " ")
            result.append([char, 1 if len(char) == 1 and char.isascii() else max(1, wcswidth(char)),
                           fg, bg, flags, decoration, deco_fg])
        cells.append(result)
    return {"cells": cells, "wrapped": wrapped, "palette": palette}


def hyperlink_marks(rows, overrides=None):
    """Group contiguous OSC 8 cells; synthetic file destinations use the same path."""
    overrides = overrides or {}
    marks = []
    active = None
    for y, row in enumerate(rows):
        for x, (_, url) in enumerate(row):
            url = overrides.get((x, y), url)
            if not url:
                active = None
                continue
            if active is None or active["target"] != url:
                active = {"target": url, "cells": []}
                marks.append(active)
            active["cells"].append([x, y])
    return marks


def raw_url_marks(rows, wrapped):
    """Use Kitty's own URL detector on a scratch screen; never mark the source."""
    if not rows or not rows[0]:
        return []
    height, width = len(rows), len(rows[0])
    scratch = Screen(None, height, width, 0)
    candidates = []
    for y, row in enumerate(rows):
        chars = [char.replace("\t", " ").replace("\x00", " ") for char, _ in row]
        text = "".join(chars)
        scratch.cursor_position(y + 1, 1)
        scratch.draw(text)
        scratch.line(y).set_wrapped_flag(wrapped[y])
        start = text.find("://")
        if start < 0:
            continue
        if all(len(char) == 1 for char in chars):
            positions = range(width)
        else:
            positions = [x for x, char in enumerate(chars) for _ in char]
        while start >= 0:
            candidates.append((positions[start], y))
            start = text.find("://", start + 3)
    # Drawing later rows can update the previous row's wrap flag.
    for y, flag in enumerate(wrapped):
        scratch.line(y).set_wrapped_flag(flag)
    marks, seen = [], set()
    for x, y in candidates:
        scratch.detect_url(x, y)
        target = scratch.current_url_text()
        if not target:
            continue
        # Pixel scrolling adds a leading render-only row; our snapshot uses visual rows.
        mask = scratch.current_selections()[-width * height:]
        # Scan the selection mask in C. Only materialize actual marked cells
        # in Python, rather than traversing every screen cell per candidate.
        cells = tuple((i % width, i // width) for run in URL_RUN.finditer(mask.translate(URL_MASK))
                      for i in range(run.start(), run.end()))
        if not cells or cells in seen:
            continue
        seen.add(cells)
        marks.append({"target": target.replace("\r", "").replace("\n", ""),
                      "cells": [list(p) for p in cells]})
    return sorted(marks, key=lambda m: (m["cells"][0][1], m["cells"][0][0]))


class HintOverlay(Handler):
    use_alternate_screen = False
    overlay_ready_report_needed = True
    mouse_tracking = MouseTracking.buttons_only

    def __init__(self, model):
        self.model = model
        self.renderer = FrameRenderer(model)
        self.codes = self.renderer.codes
        self.prefix = ""
        self.result = {}

    def initialize(self):
        self.cmd.set_window_title("Choose URL" if self.model["type"] == "url" else "Choose text")
        self.cmd.set_cursor_visible(False)
        self.cmd.set_line_wrapping(False)
        self.draw()

    @Handler.atomic_update
    def draw(self):
        self.write(self.renderer.draw(self.prefix, self.screen_size.cols, self.screen_size.rows))

    def on_resize(self, new_size):
        super().on_resize(new_size)
        # The snapshot is immutable. Reopen to select from a resized source.
        self.quit_loop()

    def select(self, index):
        self.result = {"match": [self.model["marks"][index]["target"]],
                       "groupdicts": [{}], "programs": [], "multiple_joiner": "auto",
                       "customize_processing": "", "type": self.model["type"],
                       "extra_cli_args": [], "cwd": os.getcwd()}
        self.quit_loop()

    def on_text(self, text, in_bracketed_paste=False):
        if in_bracketed_paste:
            return
        for char in text:
            candidate = self.prefix + char
            matches = [i for i, code in enumerate(self.codes) if code.startswith(candidate)]
            if not matches:
                continue
            self.prefix = candidate
            if self.codes[matches[0]] == candidate:
                self.select(matches[0])
                return
        self.draw()

    def on_key(self, event):
        if event.matches("escape"):
            self.quit_loop()
        elif event.matches("backspace"):
            self.prefix = self.prefix[:-1]
            self.draw()

    def on_interrupt(self):
        self.quit_loop()

    def on_eot(self):
        self.quit_loop()

    def on_click(self, event):
        marked, _, _ = active_cells(self.model, self.prefix)
        index = marked.get((event.cell_x, event.cell_y))
        if index is not None:
            self.select(index)

    def on_kitty_cmd_response(self, response):
        if response.get("Type") == "mark_activated":
            index = response.get("Mark")
            if isinstance(index, int) and 0 <= index < len(self.codes) and self.codes[index].startswith(self.prefix):
                self.select(index)


def main(args):
    model = decode_snapshot(sys.stdin.buffer.read())
    if not model["marks"]:
        return {}
    handler = HintOverlay(model)
    loop = Loop()
    loop.loop(handler)
    return handler.result


@result_handler(has_ready_notification=True, open_url_handler=on_mark_clicked)
def handle_result(args, data, target_window_id, boss):
    # select_hint owns the callback (including Zellij receiver cancellation).
    pass
