"""Styled, read-only hint overlay. Routing stays in select_hint.py."""
import colorsys
import json
import os
import sys
from functools import lru_cache

from kittens.hints.main import on_mark_clicked
from kittens.tui.handler import Handler, result_handler
from kittens.tui.loop import Loop
from kittens.tui.operations import MouseTracking
from kitty.fast_data_types import Screen, get_options, wcswidth


ALPHABET = "asdfghjkl"
ESC = "\x1b"
RESET = ESC + "[0m"
OSC8 = ESC + "]8;;"
ST = ESC + "\\"


def rgb(value):
    return tuple((value >> shift) & 255 for shift in (16, 8, 0))


def packed(parts):
    r, g, b = parts
    return (r << 16) | (g << 8) | b


@lru_cache(maxsize=4096)
def mix(fg, bg, amount):
    return packed(round(a * amount + b * (1 - amount)) for a, b in zip(rgb(fg), rgb(bg)))


@lru_cache(maxsize=4096)
def luminance(color):
    def linear(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return sum(w * linear(v) for w, v in zip((0.2126, 0.7152, 0.0722), rgb(color)))


def contrast(fg, bg):
    a, b = sorted((luminance(fg), luminance(bg)))
    return (b + 0.05) / (a + 0.05)


@lru_cache(maxsize=4096)
def readable(fg, bg, minimum=4.5):
    """Keep hue and saturation; change HSL lightness only as far as necessary."""
    if contrast(fg, bg) >= minimum:
        return fg
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb(fg)))

    def color_at(lightness):
        return packed(round(v * 255) for v in colorsys.hls_to_rgb(h, lightness, s))

    candidates = []
    for end in (0.0, 1.0):
        if contrast(color_at(end), bg) < minimum:
            continue
        lo, hi = 0.0, 1.0
        for _ in range(16):
            mid = (lo + hi) / 2
            if contrast(color_at(l + (end - l) * mid), bg) >= minimum:
                hi = mid
            else:
                lo = mid
        candidates.append((abs(end - l) * hi, color_at(l + (end - l) * hi)))
    return min(candidates)[1] if candidates else max(
        (0, 0xFFFFFF), key=lambda c: contrast(c, bg))


def source_snapshot(screen, rows):
    """Read Kitty's resolved cell attributes, not a stripped ANSI transcript."""
    opts = get_options()
    profile = screen.color_profile
    base_fg, base_bg = int(profile.default_fg), int(profile.default_bg)

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
            result.append([char, max(1, wcswidth(char)), fg, bg, flags, decoration, deco_fg])
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
        chars, positions = [], []
        for x, (char, _) in enumerate(row):
            char = char.replace("\t", " ").replace("\x00", " ")
            chars.append(char)
            positions.extend([x] * len(char))
        text = "".join(chars)
        scratch.cursor_position(y + 1, 1)
        scratch.draw(text)
        scratch.line(y).set_wrapped_flag(wrapped[y])
        start = text.find("://")
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
        cells = tuple((i % width, i // width) for i, flags in enumerate(mask) if flags & 2)
        if not cells or cells in seen:
            continue
        seen.add(cells)
        marks.append({"target": target.replace("\r", "").replace("\n", ""),
                      "cells": [list(p) for p in cells]})
    return sorted(marks, key=lambda m: (m["cells"][0][1], m["cells"][0][0]))


def labels(count):
    # A fixed-width home-row code is prefix-free, including screens with >9 targets.
    width, capacity = 1, len(ALPHABET)
    while capacity < count:
        width += 1
        capacity *= len(ALPHABET)
    result = []
    for i in range(count):
        code = ""
        for _ in range(width):
            i, digit = divmod(i, len(ALPHABET))
            code = ALPHABET[digit] + code
        result.append(code)
    return result


def sgr(fg, bg, flags=0, decoration=0, deco_fg=None):
    parts = ["0", "38;2;" + ";".join(map(str, rgb(fg))), "48;2;" + ";".join(map(str, rgb(bg)))]
    if flags & 1:
        parts.append("1")
    if flags & 2:
        parts.append("3")
    if flags & 4:
        parts.append("9")
    if decoration:
        parts.append("4:" + str(decoration))
        if deco_fg is not None:
            parts.append("58:2::" + ":".join(map(str, rgb(deco_fg))))
    return ESC + "[" + ";".join(parts) + "m"


def active_cells(model, prefix):
    """Index active targets and the remaining hint characters by terminal cell."""
    marked, keys = {}, {}
    for i, (mark, label) in enumerate(zip(model["marks"], labels(len(model["marks"])))):
        if not label.startswith(prefix):
            continue
        cells = [tuple(p) for p in mark["cells"]]
        for point in cells:
            marked[point] = i
        remaining = iter(label[len(prefix):])
        first = True
        for x, y in cells:
            cell = model["cells"][y][x]
            if cell is None:
                continue
            key = next(remaining, None)
            if key is None:
                break
            keys[(x, y)] = (key, first)
            first = False
    return marked, keys


def render(model, prefix="", cols=None, rows=None):
    """Produce one frame, preserving coordinates, chromatic context and attributes."""
    palette = model["palette"]
    marked, keys = active_cells(model, prefix)
    output = [RESET, ESC + "[H" + ESC + "[2J"]
    for y, row in enumerate(model["cells"][:rows]):
        output.append(f"{ESC}[{y + 1};1H")
        last_style, last_mark, end_x = None, None, 0
        for x, cell in enumerate(row[:cols]):
            if cell is None:
                continue
            char, width, fg, bg, flags, deco, deco_fg = cell
            if cols is not None and x + width > cols:
                break
            point = (x, y)
            mark = marked.get(point)
            if point in keys:
                char, next_key = keys[point]
                char += " " * (width - 1)
                bg = palette["key_bg"]
                fg = readable(palette["key_fg"] if next_key else palette["foreground"], bg)
                flags, deco = 1, 0
            elif mark is not None:
                bg = palette["target"] if bg == palette["background"] else mix(palette["target"], bg, 0.65)
                fg = readable(fg, bg)
                deco = deco or 1
                deco_fg = readable(palette["accent"], bg, 3.0)
            else:
                fg = mix(fg, bg, 0.55)
                deco_fg = mix(deco_fg, bg, 0.55)
            if mark != last_mark:
                output.append(OSC8 + (f"mark:{mark}" if mark is not None else "") + ST)
                last_mark = mark
            style = (fg, bg, flags, deco, deco_fg)
            if style != last_style:
                output.append(sgr(*style))
                last_style = style
            if x != end_x:
                output.append(f"{ESC}[{y + 1};{x + 1}H")
            output.append(char)
            end_x = x + wcswidth(char)
        if last_mark is not None:
            output.append(OSC8 + ST)
    output.append(RESET)
    return "".join(output)


class HintOverlay(Handler):
    use_alternate_screen = False
    overlay_ready_report_needed = True
    mouse_tracking = MouseTracking.buttons_only

    def __init__(self, model):
        self.model = model
        self.codes = labels(len(model["marks"]))
        self.prefix = ""
        self.result = {}

    def initialize(self):
        self.cmd.set_window_title("Choose URL" if self.model["type"] == "url" else "Choose text")
        self.cmd.set_cursor_visible(False)
        self.cmd.set_line_wrapping(False)
        self.draw()

    @Handler.atomic_update
    def draw(self):
        self.write(render(self.model, self.prefix, self.screen_size.cols, self.screen_size.rows))

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
        marked, _ = active_cells(self.model, self.prefix)
        index = marked.get((event.cell_x, event.cell_y))
        if index is not None:
            self.select(index)

    def on_kitty_cmd_response(self, response):
        if response.get("Type") == "mark_activated":
            index = response.get("Mark")
            if isinstance(index, int) and 0 <= index < len(self.codes) and self.codes[index].startswith(self.prefix):
                self.select(index)


def main(args):
    model = json.load(sys.stdin)
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
