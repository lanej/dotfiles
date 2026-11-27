#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools==4.68.0", "brotli==1.2.1"]
# ///
"""Subset an explicitly supplied Nerd Font for the catalog's shared and preset symbols."""

import argparse
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from theme import Presentation, read

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    args = parser.parse_args()
    source = ROOT / "design-system"
    tokens = read(source / "tokens.toml")["presentation"]
    overrides = [{}] + [read(preset).get("presentation", {}) for preset in sorted((source / "themes").glob("*.toml"))]
    characters = set()
    for variant in overrides:
        resolved = Presentation(tokens, variant).values
        characters.update(ord(c) for name, spec in tokens.items() if spec["type"] == "string" for c in resolved[name])
    for group in read(source / "semantic-states.toml"):
        characters.update(ord(state["octicon"]) for state in group["states"] if "octicon" in state)
    font = TTFont(args.font, recalcTimestamp=False)
    cmap = font.getBestCmap()
    missing = sorted(c for c in characters if 0xE000 <= c <= 0xF8FF and c not in cmap)
    if missing:
        parser.error("Missing catalog glyphs: " + ", ".join(f"U+{c:04X}" for c in missing))
    options = subset.Options()
    options.name_IDs, options.name_languages, options.name_legacy = ["*"], ["*"], True
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=characters)
    subsetter.subset(font)
    font.flavor = "woff2"
    font.save(ROOT / "docs/design-system/symbols.woff2")


if __name__ == "__main__":
    main()
