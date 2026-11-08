#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools==4.68.0", "brotli==1.2.1"]
# ///
"""Subset an explicitly supplied Nerd Font for the catalog's default symbols."""

import argparse
import json
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from theme import Presentation

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    args = parser.parse_args()
    tokens = json.loads((ROOT / "design-system/tokens.json").read_text())["presentation"]
    resolved = Presentation(tokens, {}).values
    characters = {ord(c) for name, spec in tokens.items() if spec["type"] == "string" for c in resolved[name]}
    font = TTFont(args.font, recalcTimestamp=False)
    options = subset.Options()
    options.name_IDs, options.name_languages, options.name_legacy = ["*"], ["*"], True
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=characters)
    subsetter.subset(font)
    font.flavor = "woff2"
    font.save(ROOT / "docs/design-system/symbols.woff2")


if __name__ == "__main__":
    main()
