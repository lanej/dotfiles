"""Render observed terminal cells on a fixed grid, without recoloring them."""

import html
import unicodedata


CELL_WIDTH = 9
CELL_HEIGHT = 20
PADDING = 12
FONT = "DejaVu Sans Mono, Menlo, Consolas, monospace"

# These terminal glyphs are geometry rather than font artwork. Draw their
# cell-aligned shapes so GitHub's SVG renderer does not need a Nerd Font and
# neighboring line/box segments meet precisely.
BOX_LINES = {
    "─": "M0 10H9", "│": "M4.5 0V20",
    "┌": "M4.5 20V10H9", "┐": "M0 10H4.5V20",
    "└": "M4.5 0V10H9", "┘": "M0 10H4.5V0",
    "├": "M4.5 0V20M4.5 10H9", "┤": "M4.5 0V20M0 10H4.5",
    "┬": "M0 10H9M4.5 10V20", "┴": "M0 10H9M4.5 10V0",
    "┼": "M0 10H9M4.5 0V20",
    "╭": "M4.5 20V15Q4.5 10 9 10",
    "╮": "M0 10Q4.5 10 4.5 15V20",
    "╰": "M4.5 0V5Q4.5 10 9 10",
    "╯": "M0 10Q4.5 10 4.5 5V0",
    "\ue0b1": "M0 0L9 10L0 20", "\ue0b3": "M9 0L0 10L9 20",
}
FILLED = {
    "\ue0b0": "M0 0L9 10L0 20Z", "\ue0b2": "M9 0L0 10L9 20Z",
    "▌": "M0 0H4.5V20H0Z", "▐": "M4.5 0H9V20H4.5Z",
    "█": "M0 0H9V20H0Z",
}


def palette_lookup(theme):
    roles = theme["roles"]
    names = ("black", "red", "green", "brown", "blue", "magenta", "cyan", "white")
    colors = dict(zip(names, theme["ansi"][:8]))
    colors.update({f"bright{name}": theme["ansi"][i + 8] for i, name in enumerate(names)})
    colors["yellow"] = colors["brown"]
    colors["brightyellow"] = colors["brightbrown"]

    def color(value, fallback):
        if value == "default":
            return fallback
        if len(value) == 6 and all(c in "0123456789abcdefABCDEF" for c in value):
            return "#" + value.upper()
        if value not in colors:
            raise ValueError(f"Unsupported terminal color: {value!r}")
        return colors[value]

    def effective(cell):
        fg = color(cell["fg"], roles["text"])
        bg = color(cell["bg"], roles["surface"])
        return (bg, fg) if cell.get("reverse") else (fg, bg)

    return effective, color


def render_svg(name, rows, theme, *, trim=True):
    """Render raw cells (not compacted text spans); preserve actual cell geometry.

    Wide glyphs occupy their leading cell and the recorded empty continuation.
    Combining marks in one cell do not advance the column. Empty backgrounds
    and explicit underlines remain visible, even without printable characters.
    Only unused trailing default-background rows/columns are cropped.
    """
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("A capture must contain rectangular terminal cells")
    background = theme["roles"]["surface"]
    effective, color = palette_lookup(theme)
    nrows, ncols = len(rows), len(rows[0])
    if trim:
        used = [(y, x) for y, row in enumerate(rows) for x, cell in enumerate(row)
                if (cell["data"].strip() or cell["data"] == ""
                    or effective(cell)[1] != background or cell.get("underscore"))]
        if used:
            nrows = max(y for y, _ in used) + 1
            ncols = max(x for _, x in used) + 1
    width, height = ncols * CELL_WIDTH + 2 * PADDING, nrows * CELL_HEIGHT + 2 * PADDING
    result = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(name, quote=True)} — observed terminal cells">',
        f'<rect width="100%" height="100%" fill="{background}"/>',
        f'<g font-family="{FONT}" font-size="14" xml:space="preserve">',
    ]
    for y, row in enumerate(rows[:nrows]):
        top = PADDING + y * CELL_HEIGHT
        # Paint backgrounds first, so a wide glyph cannot be covered by its
        # continuation cell. Only group adjacent cells with identical fills.
        left = 0
        while left < ncols:
            bg = effective(row[left])[1]
            right = left + 1
            while right < ncols and effective(row[right])[1] == bg:
                right += 1
            if bg != background:
                result.append(f'<rect x="{PADDING + left * CELL_WIDTH}" y="{top}" width="{(right - left) * CELL_WIDTH}" height="{CELL_HEIGHT}" fill="{bg}"/>')
            left = right
        for col, cell in enumerate(row[:ncols]):
            fg, _ = effective(cell)
            x = PADDING + col * CELL_WIDTH
            data = cell["data"]
            if cell.get("underscore"):
                ink = color(cell.get("underline_color", "default"), fg)
                result.append(f'<rect x="{x}" y="{top + 18}" width="{CELL_WIDTH}" height="1" fill="{ink}"/>')
            if not data.strip():
                continue
            if data in BOX_LINES:
                result.append(f'<path d="{BOX_LINES[data]}" transform="translate({x} {top})" stroke="{fg}" stroke-width="1.35" fill="none"/>')
                continue
            if data in FILLED:
                result.append(f'<path d="{FILLED[data]}" transform="translate({x} {top})" fill="{fg}"/>')
                continue
            # pyte records a wide cell as text followed by an empty cell.
            span = 2 if col + 1 < ncols and row[col + 1]["data"] == "" else 1
            weight = "bold" if cell.get("bold") else "normal"
            italic = "italic" if cell.get("italics") else "normal"
            # Preserve full grapheme clusters and place each independently.
            # No textLength or concatenated-span measurements.
            if any(unicodedata.category(ch) == "Cc" for ch in data):
                raise ValueError("Control character in recorded printable cell")
            result.append(f'<text x="{x + span * CELL_WIDTH / 2:g}" y="{top + 15}" text-anchor="middle" fill="{fg}" font-weight="{weight}" font-style="{italic}">{html.escape(data)}</text>')
    result.append("</g></svg>")
    return "\n".join(result) + "\n"


class TerminalMetadata:
    """Remove OSC/DCS control strings, including split reads, not their labels.

    OSC 8 hyperlink labels are ordinary text after the terminator. Preserve
    that text and keep other escape sequences for the terminal emulator.
    """
    def __init__(self):
        self.pending = ""

    def feed(self, data):
        data = self.pending + data
        self.pending = ""
        output = []
        pos = 0
        while pos < len(data):
            start = data.find("\x1b", pos)
            if start == -1:
                output.append(data[pos:])
                break
            output.append(data[pos:start])
            if start + 1 == len(data):
                self.pending = data[start:]
                break
            kind = data[start + 1]
            if kind not in "]P^_X":
                output.append(data[start:start + 2])
                pos = start + 2
                continue
            terminators = ["\x1b\\"]
            if kind == "]":
                terminators.append("\x07")
            ends = [(data.find(end, start + 2), len(end)) for end in terminators]
            complete = [(index, size) for index, size in ends if index != -1]
            if not complete:
                self.pending = data[start:]
                break
            index, size = min(complete)
            pos = index + size
        return "".join(output)
