"""Resolve only a single diff3 conflict between one-line lint scope expressions."""

import re
import sys
from pathlib import Path

path = Path(".golangci.yml")
text = path.read_text()
conflict = re.compile(
    r"^<<<<<<< [^\n]*\n(.*?)^\|\|\|\|\|\|\| [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*(?:\n|$)",
    re.MULTILINE | re.DOTALL,
)
matches = list(conflict.finditer(text))
if len(matches) != 1:
    sys.exit("lint scope adapter requires exactly one diff3 conflict")
match = matches[0]
if re.search(
    r"^(<{7}|={7}|>{7}|\|{7})",
    text[: match.start()] + text[match.end() :],
    re.MULTILINE,
):
    sys.exit("additional conflict markers require manual resolution")


def scope(block):
    lines = block.splitlines()
    if len(lines) != 1:
        sys.exit(
            "only a single path-except scope line per side can be resolved automatically"
        )
    line = re.fullmatch(r"([ \t]*)path-except: \^internal/\((.+)\)[ \t]*", lines[0])
    if not line:
        sys.exit("unsupported lint scope expression; resolve manually")
    parts = []
    depth = 0
    current = ""
    for character in line[2]:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                sys.exit("unbalanced lint scope expression")
        if character == "|" and depth == 0:
            if not current:
                sys.exit("empty lint scope alternative")
            parts.append(current)
            current = ""
        else:
            current += character
    if depth != 0 or not current:
        sys.exit("unbalanced or empty lint scope expression")
    parts.append(current)
    return line[1], parts


ours_indent, ours = scope(match[1])
base_indent, base = scope(match[2])
theirs_indent, theirs = scope(match[3])
if ours_indent != base_indent or ours_indent != theirs_indent:
    sys.exit("scope indentation changed; resolve manually")
merged = ours + [item for item in theirs if item not in base and item not in ours]
replacement = f"{ours_indent}path-except: ^internal/({'|'.join(merged)})\n"
path.write_text(text[: match.start()] + replacement + text[match.end() :])
print("resolved additive lint scope")
