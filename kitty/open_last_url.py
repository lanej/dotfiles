"""Open the last web URL in a kitty window, repairing padded TUI wrapping."""

import re
from bisect import bisect_right

from kittens.tui.handler import result_handler


# Keep OSC 8 targets before removing other terminal formatting.
ESCAPE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]")
HYPERLINK = re.compile(r"\x1b\]8;[^;]*;([^\x07\x1b]*)(?:\x07|\x1b\\)")
URL = re.compile(r"https?://[^\s<>\"`\\\x00-\x1f]+")


def clean_url(url: str) -> str:
    url = url.rstrip(".,;")
    # Preserve balanced parentheses in URLs, but drop prose/Markdown delimiters.
    for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
        while url.endswith(closing) and url.count(closing) > url.count(opening):
            url = url[:-1]
    return url


def plain_text_and_links(text: str):
    parts, spans, links = [], [], []
    position = 0
    linked = False
    for part in re.split(f"({ESCAPE.pattern})", text):
        if ESCAPE.fullmatch(part):
            hyperlink = HYPERLINK.fullmatch(part)
            if hyperlink:
                target = hyperlink.group(1)
                linked = bool(target)
                if URL.fullmatch(target):
                    links.append((position, 1, target))
        else:
            part = part.replace("\x00", " ")
            if linked:
                spans.append((position, position + len(part)))
            parts.append(part)
            position += len(part)
    return "".join(parts), spans, links


def last_url(text: str) -> str | None:
    text, linked_spans, candidates = plain_text_and_links(text)
    linked_starts = [start for start, _ in linked_spans]
    offset = 0
    rows = text.split("\n")
    for index, row in enumerate(rows):
        for match in URL.finditer(row):
            position = offset + match.start()
            span_index = bisect_right(linked_starts, position) - 1
            if span_index >= 0 and position < linked_spans[span_index][1]:
                continue
            url = match.group()
            tail = row[match.end():]
            next_index = index + 1
            # Kitty already joins its soft wraps. Spaces mark a TUI's margin.
            while next_index < len(rows) and tail.strip() == "" and len(tail) >= 2:
                following = rows[next_index]
                fragment = following.strip()
                # Only continue with a single URL-like token, never a paragraph,
                # a new link, or a bullet. Hard-wrapped plain text is ambiguous.
                if (
                    not fragment
                    or fragment.startswith(("http://", "https://", "-", "*", "•", "│"))
                    or re.search(r"[\s<>\"`\\\x00-\x1f]", fragment)
                    or not re.search(r"[/?#&=_%~-]|\d|[a-z0-9]\.[a-z0-9]", fragment, re.I)
                    or len(following) - len(following.lstrip()) > match.start()
                    or clean_url(url) != url
                ):
                    break
                url += fragment
                tail = following[len(following.rstrip(" \r")):]
                next_index += 1
            candidates.append((position, 0, clean_url(url)))
        offset += len(row) + 1
    return max(candidates)[2] if candidates else None


def main(args: list[str]) -> None:
    pass


@result_handler(no_ui=True)
def handle_result(args, answer, target_window_id, boss):
    window = boss.window_id_map.get(target_window_id)
    if window is None:
        return
    # Most recent links are visible; avoid serializing a large scrollback unless
    # the current screen contains no link at all.
    url = last_url(window.as_text(as_ansi=True))
    if url is None and not window.screen.is_using_alternate_linebuf():
        url = last_url(window.as_text(as_ansi=True, add_history=True))
    if url:
        boss.open_url(url, cwd=window.cwd_of_child)
