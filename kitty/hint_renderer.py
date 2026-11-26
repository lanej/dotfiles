"""Pure rendering policy shared by both hint session transports."""
import colorsys
import json
import re
from functools import lru_cache


ALPHABET = "asdfghjkl"
ESC = "\x1b"
RESET = ESC + "[0m"
OSC8 = ESC + "]8;;"
ST = ESC + "\\"


# A 256-entry lookup table replaces repeated sRGB exponentiation.
def linear_channel(value):
    value /= 255
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


LINEAR = tuple(linear_channel(i) for i in range(256))
RED = tuple(v * 0.2126 for v in LINEAR)
GREEN = tuple(v * 0.7152 for v in LINEAR)
BLUE = tuple(v * 0.0722 for v in LINEAR)
# Bounded caches can hold every cell of a large truecolor viewport.
COLOR_CACHE = 65536


def rgb(value):
    return value >> 16, value >> 8 & 255, value & 255


def packed(parts):
    r, g, b = parts
    return (r << 16) | (g << 8) | b


@lru_cache(maxsize=COLOR_CACHE)
def mix(fg, bg, amount):
    r, g, b = rgb(fg)
    br, bgc, bb = rgb(bg)
    other = 1 - amount
    return ((round(r * amount + br * other) << 16)
            | (round(g * amount + bgc * other) << 8)
            | round(b * amount + bb * other))


def luminance(color):
    return RED[color >> 16] + GREEN[color >> 8 & 255] + BLUE[color & 255]


def contrast(fg, bg):
    a, b = luminance(fg) + 0.05, luminance(bg) + 0.05
    return a / b if a >= b else b / a


def meets_contrast(fg, bg_luminance, minimum):
    value = luminance(fg) + 0.05
    return (value / bg_luminance if value >= bg_luminance else bg_luminance / value) >= minimum


@lru_cache(maxsize=COLOR_CACHE)
def readable(fg, bg, minimum=4.5):
    """Keep hue and saturation; change HSL lightness only as far as necessary."""
    background = luminance(bg) + 0.05
    if meets_contrast(fg, background, minimum):
        return fg
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb(fg)))
    # For fixed hue and saturation, each RGB component is piecewise linear
    # in HSL lightness. Resolve the midpoint once, not at each search step.
    r, g, b = colorsys.hls_to_rgb(h, 0.5, s)

    def color_at(lightness):
        if lightness <= 0.5:
            scale = lightness * 510
            return ((round(r * scale) << 16) | (round(g * scale) << 8)
                    | round(b * scale))
        scale = (1 - lightness) * 510
        return ((round(255 - (1 - r) * scale) << 16)
                | (round(255 - (1 - g) * scale) << 8)
                | round(255 - (1 - b) * scale))

    candidates = []
    for end, extreme in ((0.0, 0), (1.0, 0xFFFFFF)):
        if not meets_contrast(extreme, background, minimum):
            continue
        lo, hi, best = 0.0, 1.0, extreme
        for _ in range(12):
            mid = (lo + hi) / 2
            color = color_at(l + (end - l) * mid)
            if meets_contrast(color, background, minimum):
                hi, best = mid, color
            else:
                lo = mid
        candidates.append((abs(end - l) * hi, best))
    return min(candidates)[1] if candidates else max(
        (0, 0xFFFFFF), key=lambda c: contrast(c, bg))


@lru_cache(maxsize=COLOR_CACHE)
def dimmed(fg, bg, minimum=4.5):
    """Dim toward the cell's own background without crossing the contrast floor."""
    background = luminance(bg) + 0.05
    if not meets_contrast(fg, background, minimum):
        return readable(fg, bg, minimum)
    candidate = mix(fg, bg, 0.55)
    if meets_contrast(candidate, background, minimum):
        return candidate
    # Avoid caching transient binary-search colors; cache only the final result.
    r, g, b = rgb(fg)
    br, bgc, bb = rgb(bg)
    lo, hi, best = 0.55, 1.0, fg
    for _ in range(12):
        mid = (lo + hi) / 2
        other = 1 - mid
        candidate = ((round(r * mid + br * other) << 16)
                     | (round(g * mid + bgc * other) << 8)
                     | round(b * mid + bb * other))
        if meets_contrast(candidate, background, minimum):
            hi, best = mid, candidate
        else:
            lo = mid
    return best

def encode_session(model):
    # Cross-interpreter transport: standard JSON, not Python-version-specific marshal.
    return json.dumps(model, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def decode_session(data):
    return json.loads(data)


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


@lru_cache(maxsize=COLOR_CACHE)
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


def scheme_slots(model, mark, cells):
    """Reserve visible scheme cells only; leave the domain at its original column.

    HTTPS is implicit in hint mode. Other schemes keep their names, using
    only the delimiter cells for the key. Wrapped or custom hyperlink labels
    fall back to the ordinary in-place hint.
    """
    displayed = []
    for x, y in cells:
        cell = model["cells"][y][x]
        if cell is None or cell[1] != 1 or len(cell[0]) != 1:
            break
        displayed.append(cell[0])
        if len(displayed) >= 32 or "".join(displayed).endswith("://"):
            break
    match = re.fullmatch(r"([a-zA-Z][a-zA-Z0-9+.-]*)://", "".join(displayed))
    if match is None:
        return []
    scheme = match[1]
    size = len(match[0])
    if not mark["target"].lower().startswith(scheme.lower() + "://") or len(cells) <= size:
        return []
    x, y = cells[0]
    if cells[:size + 1] != [(x + i, y) for i in range(size + 1)]:
        return []
    return cells[:size] if scheme.lower() == "https" else cells[len(scheme):size]


def active_cells(model, prefix):
    """Index active targets, key cells and hidden scheme cells."""
    marked, keys, hidden = {}, {}, set()
    for i, (mark, label) in enumerate(zip(model["marks"], labels(len(model["marks"])))):
        if not label.startswith(prefix):
            continue
        cells = [tuple(p) for p in mark["cells"]]
        for point in cells:
            marked[point] = i
        remaining = label[len(prefix):]
        slots = scheme_slots(model, mark, cells)
        if remaining and len(slots) >= len(remaining):
            # Right-align a padded key badge in the scheme's own space.
            padding = min(2, len(slots) - len(remaining))
            badge = (" " if padding == 2 else "") + remaining + (" " if padding else "")
            for point in slots[:-len(badge)]:
                hidden.add(point)
                marked.pop(point, None)
            first = True
            for point, char in zip(slots[-len(badge):], badge):
                keys[point] = (char, first and char != " ")
                if char != " ":
                    first = False
            continue
        remaining = iter(remaining)
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
    return marked, keys, hidden


def render(model, prefix="", cols=None, rows=None, *, changed_rows=None):
    """Produce one frame, preserving coordinates, chromatic context and attributes."""
    palette = model["palette"]
    marked, keys, hidden = active_cells(model, prefix)
    output = [RESET]
    if changed_rows is None:
        output.append(ESC + "[H" + ESC + "[2J")
    for y, row in enumerate(model["cells"][:rows]):
        if changed_rows is not None and y not in changed_rows:
            continue
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
            if point in hidden:
                char = " " * width
                flags, deco = 0, 0
            elif point in keys:
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
                # Keep blank cells in the same style runs as surrounding text;
                # skipping them creates excessive SGR transitions.
                fg = dimmed(fg, bg)
                if deco:
                    deco_fg = dimmed(deco_fg, bg, 3.0)
            if mark != last_mark:
                output.append(OSC8 + (f"mark:{mark}" if mark is not None else "") + ST)
                last_mark = mark
            style = (fg, bg, flags, deco, deco_fg if deco else None)
            if style != last_style:
                output.append(sgr(*style))
                last_style = style
            if x != end_x:
                output.append(f"{ESC}[{y + 1};{x + 1}H")
            output.append(char)
            end_x = x + width
        if last_mark is not None:
            output.append(OSC8 + ST)
    output.append(RESET)
    return "".join(output)


class FrameRenderer:
    """Render the initial snapshot once, then repaint only affected rows."""
    def __init__(self, model):
        self.model = model
        self.previous = None
        self.codes = labels(len(model["marks"]))
        self.mark_rows = [frozenset(y for _, y in m["cells"]) for m in model["marks"]]

    def draw(self, prefix="", cols=None, rows=None):
        if self.previous is None:
            result = render(self.model, prefix, cols, rows)
        elif self.previous == prefix:
            return ""
        else:
            changed = set()
            for code, mark_rows in zip(self.codes, self.mark_rows):
                if code.startswith(self.previous) or code.startswith(prefix):
                    changed.update(mark_rows)
            result = render(self.model, prefix, cols, rows, changed_rows=changed)
        self.previous = prefix
        return result


