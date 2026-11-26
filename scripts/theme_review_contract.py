"""Independent, falsifiable acceptance rules for observed native terminal cells.

Never read an application's adapter to determine whether its output is good.
The palette resolves intended semantic ink and surfaces; the contract supplies
independent thresholds, required content and layout/interaction invariants.
"""
import argparse
from collections import Counter
import hashlib
import json
import tomllib
from pathlib import Path
import re
import shutil
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "design-system/native-review-contract.toml"
from theme_review import GLYPH_PATHS

DECORATIVE_JOINS = set("\ue0b0\ue0b1\ue0b2\ue0b3")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contrast(a, b):
    def luminance(color):
        values = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(values, (.2126, .7152, .0722)))
    lo, hi = sorted((luminance(a), luminance(b)))
    return (hi + .05) / (lo + .05)


def effective_ink(theme, cell):
    names = ("black", "red", "green", "brown", "blue", "magenta", "cyan", "white")
    ansi = dict(zip(names, theme["ansi"][:8]))
    ansi.update({"bright" + name: theme["ansi"][i+8] for i, name in enumerate(names)})
    ansi.update(yellow=ansi["brown"], brightyellow=ansi["brightbrown"])
    def resolve(value, default):
        if value == "default":
            return default.upper()
        if re.fullmatch(r"[0-9a-fA-F]{6}", value):
            return "#" + value.upper()
        return ansi[value].upper()
    fg = resolve(cell["fg"], theme["roles"]["text"])
    bg = resolve(cell["bg"], theme["roles"]["surface"])
    return (bg, fg) if cell.get("reverse") else (fg, bg)


def span(row, label, start_at=0):
    """Translate a text match to actual columns, even after a wide/combined glyph."""
    columns = [i for i, cell in enumerate(row) for _ in cell["data"]]
    start = "".join(cell["data"] for cell in row).find(label, start_at)
    return None if start < 0 else (columns[start], columns[start+len(label)-1] + 1)


def compact_grid(rows):
    result = []
    for row in rows:
        spans = []
        for cell in row:
            style = {key: value for key, value in cell.items() if key != "data"}
            if spans and all(spans[-1][key] == value for key, value in style.items()):
                spans[-1]["data"] += cell["data"]
            else:
                spans.append({**cell})
        result.append(spans)
    return result


def audit_capture(surface, rows, theme, policy, *, neovim_syntax="vim"):
    checks = []
    def check(name, passed, expected, observed):
        checks.append(dict(id=name, passed=bool(passed), expected=expected, observed=observed))
    def finish():
        return {"surface": surface, "status": "pass" if all(c["passed"] for c in checks) else "fail", "checks": checks}
    valid = bool(rows and rows[0] and all(len(r) == len(rows[0]) for r in rows))
    check("grid.rectangular", valid, "nonempty rectangular grid", [len(rows), len(rows[0]) if rows else 0])
    if not valid:
        return finish()
    rules = policy["surfaces"][surface]
    lines = ["".join(c["data"] for c in row) for row in rows]
    missing = [a for a in rules["anchors"] if not any(a in line for line in lines)]
    check("fixture.content", not missing, rules["anchors"], {"missing": missing})
    forbidden = [a for a in rules.get("forbidden", []) if any(a in line for line in lines)]
    check("fixture.no-startup-errors", not forbidden, "no forbidden startup/error messages", forbidden)
    visual = theme["theme"] in policy["visual_presets"]
    # Nord is a legacy reference, not a claim of Sage-level visual compliance.
    if not visual:
        return finish()
    roles = theme["roles"]
    inks = [[effective_ink(theme, cell) for cell in row] for row in rows]
    base, raised = roles["surface"], roles["surface.raised"]
    floors = policy["contrast"]
    failures = {"text": [], "indicator": []}
    counts = Counter()
    minima = {}
    glyphs = []
    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            data = cell["data"]
            if not data.strip():
                continue
            if any(ch == "\ufffd" or (unicodedata.category(ch) == "Co" and ch not in DECORATIVE_JOINS and ch not in GLYPH_PATHS) for ch in data):
                glyphs.append({"row": y+1, "column": x+1, "glyph": data})
            # These transitions and Neovim's empty-line tildes convey no state.
            if data in DECORATIVE_JOINS or ((surface == "neovim-frame" or surface.startswith("neovim-code-")) and lines[y].strip() == "~"):
                counts["decorative"] += 1
                continue
            kind = "indicator" if all(0x2500 <= ord(ch) <= 0x259f or 0x2800 <= ord(ch) <= 0x28ff or ch == "⋮" for ch in data) else "text"
            fg, bg = inks[y][x]
            ratio = contrast(fg, bg)
            counts[kind] += 1
            minima[kind] = min(minima.get(kind, ratio), ratio)
            if ratio < floors[kind + "_min"]:
                failures[kind].append({"row": y+1, "column": x+1, "glyph": data, "fg": fg, "bg": bg, "ratio": round(ratio, 3)})
    check("evidence.glyphs", not glyphs, "no replacement or unsupported private-use glyphs in SVG evidence", {"count": len(glyphs), "examples": glyphs[:12]})
    for kind in ("text", "indicator"):
        check("contrast." + kind, not failures[kind], {"minimum": floors[kind+"_min"]},
              {"count": counts[kind], "minimum": round(minima[kind], 3) if kind in minima else None,
               "failed_cells": len(failures[kind]), "examples": failures[kind][:12]})

    def styled(y, label, fg, bg=None):
        bounds = span(rows[y], label)
        if bounds is None:
            return False
        return all(ink[0] == roles[fg] and (bg is None or ink[1] == roles[bg]) for ink in inks[y][bounds[0]:bounds[1]])

    def dense_selection(primitive):
        rule = policy["dense_selection"]
        header = next((i for i, line in enumerate(lines)
                       if all(label in line for label in primitive["header"])), len(rows))
        candidates = []
        for y in range(header + 1, len(rows)):
            bg_counts = Counter(bg for _, bg in inks[y] if bg not in (base, raised))
            if not bg_counts:
                continue
            fill, count = bg_counts.most_common(1)[0]
            if count / len(rows[y]) >= rule["min_coverage"] and sum(c["data"].strip() != "" and bg == fill for c, (_, bg) in zip(rows[y], inks[y])) >= primitive["minimum_text_cells"]:
                candidates.append((y, fill, count))
        check(surface + ".unique-selection", len(candidates) == 1, "one selected process row", [y+1 for y, _, _ in candidates])
        for y, fill, count in candidates:
            ratios = {"base": contrast(fill, base), "raised": contrast(fill, raised)}
            check(surface + ".fill-emphasis", min(ratios.values()) >= rule["min_background_contrast"] and ratios["base"] <= rule["max_base_contrast"],
                  {"minimum_vs_base_and_raised": rule["min_background_contrast"], "maximum_vs_base": rule["max_base_contrast"]},
                  {"row": y+1, "fill": fill, "coverage": round(count/len(rows[y]), 3), **{k: round(v, 3) for k, v in ratios.items()}})
            fg = {ink for c, (ink, bg) in zip(rows[y], inks[y]) if c["data"].strip() and bg == fill}
            check(surface + ".selection-ink", fg == {roles[primitive["ink"]]}, roles[primitive["ink"]], sorted(fg))

    def tab_strip(primitive):
        if primitive["row"] not in ("first", "last"):
            raise ValueError("tab-strip requires first or last row")
        y = 0 if primitive["row"] == "first" else len(rows)-1
        labels = primitive["labels"]
        for i, label in enumerate(labels):
            focused = i == primitive["active"]
            fg = primitive["active_ink"] if focused else primitive["inactive_ink"]
            bg = primitive["active_fill"] if focused else "surface"
            bounds = span(rows[y], label)
            actual = [list(pair) for pair in sorted(set(inks[y][bounds[0]:bounds[1]]))] if bounds else []
            check(surface + ".label." + label, styled(y, label, fg, bg),
                  {"fg": roles[fg], "bg": roles[bg]}, {"row": y+1, "label": label, "inks": actual})
        active = span(rows[y], labels[primitive["active"]])
        pad = primitive["padding"]
        excess = [x+1 for x, (_, bg) in enumerate(inks[y]) if bg != base and not (active and active[0]-pad <= x < active[1]+pad)]
        check(surface + ".no-inactive-ribbons", not excess, "non-base fill only within active label and its padding", {"excess_columns": excess[:24], "count": len(excess)})
        for marker in primitive["markers"]:
            i, glyph, role = marker["after"], marker["glyph"], marker["ink"]
            current = span(rows[y], labels[i])
            following = span(rows[y], labels[i+1]) if i+1 < len(labels) else (len(rows[y]), len(rows[y]))
            matches = [] if not (current and following) else [x for x in range(current[1], following[0]) if rows[y][x]["data"] == glyph]
            check(surface + ".marker." + role, len(matches) == 1 and inks[y][matches[0]] == (roles[role], base),
                  "one " + glyph + " on the base after " + labels[i], {"row": y+1, "columns": [x+1 for x in matches], "inks": [list(inks[y][x]) for x in matches]})

    def marked_selection(primitive):
        for label, role in primitive["labels"].items():
            matches = [y for y, row in enumerate(rows) if span(row, label)]
            check(surface + ".status." + label, len(matches) == 1 and styled(matches[0], label, role), role, {"rows": [y+1 for y in matches]})
        selected = [(y, span(row, primitive["selected"])) for y, row in enumerate(rows) if span(row, primitive["selected"])]
        check(surface + ".unique-selection", len(selected) == 1, "one selected anchor", {"rows": [y+1 for y, _ in selected]})
        if len(selected) == 1:
            y, (x, _) = selected[0]
            fill = inks[y][x][1]
            pointers = [i for i in range(x) if rows[y][i]["data"] in primitive["pointers"] and inks[y][i][1] == fill and contrast(*inks[y][i]) >= floors["indicator_min"]]
            ratio = contrast(fill, base)
            check(surface + ".marked-selection", len(pointers) == 1 and ratio <= policy["marked_selection"]["max_base_contrast"],
                  "one contrasting pointer and quiet selected surface", {"row": y+1, "pointer_columns": [i+1 for i in pointers], "fill_contrast": round(ratio, 3)})

    def change_markers(primitive):
        check(surface + ".change-markers", all(any(re.search(pattern, line) for line in lines) for pattern in primitive["patterns"]),
              primitive["patterns"], [line.strip() for line in lines if any(re.search(pattern, line) for pattern in primitive["patterns"])])

    def plain_heading(primitive):
        if primitive["row"] not in ("first", "last"):
            raise ValueError("plain-heading requires first or last row")
        y = 0 if primitive["row"] == "first" else len(rows)-1
        label = primitive["label"]
        bounds = span(rows[y], label)
        region = []
        if bounds:
            start, end = bounds
            pad = primitive["padding"]
            region = list(range(max(0, start-pad), min(len(rows[y]), end+pad)))
        expected = (roles[primitive["ink"]], base)
        passed = bool(bounds and region) and all(
            inks[y][x] == expected and rows[y][x].get("bold", False)
            for x in region)
        check(surface + ".plain-heading", passed,
              {"label": label, "fg": expected[0], "bg": expected[1], "bold": True},
              {"row": y+1, "cells": [{"column": x+1, "fg": inks[y][x][0],
                                      "bg": inks[y][x][1], "bold": rows[y][x].get("bold", False)}
                                     for x in region]})

    def syntax_diversity(primitive):
        # Measure source anchors, not status line, gutter or diagnostics.
        colors = set()
        observed = []
        for anchor in primitive["anchors"]:
            for y, row in enumerate(rows):
                bounds = span(row, anchor)
                if bounds is None:
                    continue
                for x in range(*bounds):
                    if row[x]["data"].strip():
                        colors.add(inks[y][x][0])
                observed.append({"anchor": anchor, "row": y+1})
                break
        check(surface + ".syntax-diversity",
              len(colors) >= primitive["minimum_colors"],
              {"minimum_colors": primitive["minimum_colors"]},
              {"colors": sorted(colors), "anchors": observed})

    def syntax_roles(primitive):
        if primitive.get("treesitter_only", False):
            if not surface.startswith("neovim-code-"):
                raise ValueError(f"{surface}: Tree-sitter syntax roles require a Neovim language surface")
            if neovim_syntax != "treesitter":
                return
        anchor = primitive["anchor"]
        tokens = primitive["tokens"]
        distinct = primitive.get("distinct", False)
        if not anchor or not tokens or any(not token.strip() or anchor.count(token) != 1 for token in tokens):
            raise ValueError(f"{surface}: each syntax role token must occur once in its context")
        expected = {token: {"role": role, "fg": roles[role]} for token, role in tokens.items()}
        matches = [(y, match.start()) for y, line in enumerate(lines)
                   for match in re.finditer(re.escape(anchor), line)]
        evidence = {"anchor_matches": len(matches), "tokens": {}}
        passed = len(matches) == 1
        if passed:
            y, offset = matches[0]
            for token, style in expected.items():
                start, end = span(rows[y], token, offset + anchor.index(token))
                cells = [{"column": x + 1, "fg": inks[y][x][0]}
                         for x in range(start, end) if rows[y][x]["data"].strip()]
                evidence["tokens"][token] = {"row": y + 1, "cells": cells}
                passed = passed and bool(cells) and all(cell["fg"] == style["fg"] for cell in cells)
        if distinct:
            passed = passed and len({style["fg"] for style in expected.values()}) == len(expected)
        check(surface + ".syntax-roles." + primitive["name"], passed,
              {"anchor": anchor, "tokens": expected, "distinct": distinct}, evidence)

    def history_selection(primitive):
        # Selection geometry is native to Atuin, not invented by our adapter.
        signatures = []
        excessive = []
        for label in primitive["labels"]:
            for y, row in enumerate(rows):
                bounds = span(row, label)
                if bounds is None:
                    continue
                start, end = bounds
                region = [(inks[y][x], row[x].get("bold", False)) for x in range(start, end)
                          if row[x]["data"].strip()]
                if not region:
                    continue
                signatures.append({"label": label, "row": y+1,
                    "ink": sorted({pair[0][0] for pair in region}),
                    "bold": any(pair[1] for pair in region)})
                for (fg, bg), _ in region:
                    if contrast(bg, base) > primitive["maximum_fill_contrast"]:
                        excessive.append({"row": y+1, "background": bg})
                break
        check(surface + ".quiet-history", not excessive and len(signatures) == len(primitive["labels"]),
              {"maximum_fill_contrast": primitive["maximum_fill_contrast"]},
              {"excessive": excessive, "rows": signatures})
        check(surface + ".selection-emphasis",
              len({(tuple(s["ink"]), s["bold"]) for s in signatures}) > 1,
              "observable command foreground or weight distinction", signatures)

    handlers = {"history-selection": history_selection, "syntax-diversity": syntax_diversity, "syntax-roles": syntax_roles,
                "dense-selection": dense_selection, "tab-strip": tab_strip,
                "marked-selection": marked_selection, "change-markers": change_markers,
                "plain-heading": plain_heading}
    for primitive in rules.get("primitives", []):
        kind = primitive["kind"]
        if kind not in handlers:
            raise ValueError(f"{surface}: unknown visual primitive {kind!r}")
        handlers[kind](primitive)
    return finish()


def verify_review(directory, policy_path=CONTRACT, *, profile=None, commit=None, preset=None, colors=None,
                  gallery=None, require_treesitter=False):
    """Verify evidence against the current independent contract; fail closed.

    Exact replay prevents hand-recolored or stale SVGs from passing. This is
    content integrity, not an attestation that the producing CI runner is trusted.
    """
    from theme_review import render_svg
    manifest = json.loads((directory / "manifest.json").read_text())
    policy = tomllib.loads(policy_path.read_text())
    if manifest.get("schema") != 2 or manifest.get("contract_sha256") != sha256(policy_path):
        raise ValueError("missing or stale review contract")
    if commit is not None and manifest.get("commit") != commit:
        raise ValueError("review evidence belongs to a different checkout")
    if manifest.get("auditor_sha256") != sha256(Path(__file__)) or manifest.get("renderer_sha256") != sha256(Path(__file__).with_name("theme_review.py")):
        raise ValueError("review evidence uses a different auditor or renderer")
    if preset is not None and manifest.get("preset") != preset:
        raise ValueError("review evidence belongs to a different preset")
    if colors is not None and manifest.get("colors_sha256") != sha256(colors):
        raise ValueError("review evidence does not use the expected generated theme")
    if sha256(directory / "review-contract.toml") != manifest["contract_sha256"] or sha256(directory / "colors.json") != manifest["colors_sha256"]:
        raise ValueError("review inputs changed")
    theme = json.loads((directory / "colors.json").read_text())
    if theme["theme"] != manifest["preset"] or theme["symbols"] != manifest["symbols"]:
        raise ValueError("review preset or symbol mode mismatch")
    expected = set(policy["profiles"][profile]) if profile else set(manifest["required_surfaces"])
    if set(manifest["surfaces"]) != expected or set(manifest["required_surfaces"]) != expected:
        raise ValueError("review coverage differs from required surfaces")
    neovim_syntax = manifest.get("neovim_syntax", "vim")
    if neovim_syntax not in {"vim", "treesitter"}:
        raise ValueError("unknown Neovim syntax engine in review evidence")
    if require_treesitter and (neovim_syntax != "treesitter" or not any(s.startswith("neovim-code-") for s in expected)):
        raise ValueError("review evidence requires Neovim language captures from Tree-sitter")
    errors = []
    for surface, item in manifest["surfaces"].items():
        if item["status"] != "captured":
            errors.append(surface + ": capture failed")
            # Verify the partial frame too, if present. Incomplete captures
            # cannot pass even when their remaining visible cells pass.
            if "grid" not in item:
                continue
        files = [surface + ".json"]
        structured = surface in policy["structured_only"]
        if not structured:
            files += [surface + suffix for suffix in (".grid.json", ".ansi", ".svg", ".audit.json")]
        if set(item["sha256"]) != set(files):
            raise ValueError(surface + ": missing evidence files")
        for name in files:
            if sha256(directory / name) != item["sha256"][name]:
                raise ValueError(name + ": evidence bytes changed")
        if structured:
            if item.get("contract_status") != "not-visual":
                raise ValueError(surface + ": structured evidence cannot prove visuals")
            continue
        rows = json.loads((directory / (surface + ".grid.json")).read_text())
        if item.get("rows") != len(rows) or item.get("columns") != len(rows[0]):
            raise ValueError(surface + ": grid geometry mismatch")
        if json.loads((directory / (surface + ".json")).read_text()) != compact_grid(rows):
            raise ValueError(surface + ": compact cells do not match the observed grid")
        rendered = render_svg(surface, rows, theme, trim=surface not in ("zellij", "bottom", "tmux"))
        if (directory / (surface + ".svg")).read_text() != rendered:
            raise ValueError(surface + ": SVG does not replay from the observed grid")
        audit = audit_capture(surface, rows, theme, policy, neovim_syntax=neovim_syntax)
        expected_status = "fail" if item["status"] != "captured" else audit["status"]
        if json.loads((directory / (surface + ".audit.json")).read_text()) != audit or item.get("contract_status") != expected_status:
            raise ValueError(surface + ": audit report does not replay")
        errors.extend(surface + ": " + c["id"] for c in audit["checks"] if not c["passed"])
        if gallery is not None:
            published = gallery / (surface + ".svg")
            if not published.is_file() or sha256(published) != item["sha256"][surface + ".svg"]:
                errors.append(surface + ": gallery image missing or differs from native artifact")
    return errors


def export_gallery(directory, gallery, *, profile, commit, preset, colors):
    """Publish exact captured bytes, never a repaired or synthesized screenshot."""
    if not profile or not commit or not preset or colors is None:
        raise ValueError("gallery export requires profile, checkout, preset and expected colors")
    failures = verify_review(directory, profile=profile, commit=commit, preset=preset, colors=colors)
    if failures:
        raise ValueError("gallery export requires a passing profile: " + ", ".join(failures))
    manifest = json.loads((directory / "manifest.json").read_text())
    gallery.mkdir(parents=True, exist_ok=True)
    for surface, item in manifest["surfaces"].items():
        if "svg" in item:
            name = surface + ".svg"
            shutil.copyfile(directory / name, gallery / name)
    errors = verify_review(directory, profile=profile, commit=commit, preset=preset, colors=colors, gallery=gallery)
    if errors:
        raise ValueError("exported gallery does not match evidence: " + ", ".join(errors))


def write_summary(path, directory, verdict, errors):
    """Publish measured results, not an aesthetic approval."""
    manifest = json.loads((directory / "manifest.json").read_text())
    lines = [f'### Native review — {manifest["preset"]} / {verdict}',
             "", f'Checkout: {manifest["commit"]}. Human approval: pending.', "",
             f'Neovim language syntax engine: {manifest.get("neovim_syntax", "vim")}.', "",
             "| Surface | Capture | Contract | Min text | Min indicator | Failed predicates |",
             "| --- | --- | --- | ---: | ---: | --- |"]
    for surface, item in manifest["surfaces"].items():
        audit_path = directory / (surface + ".audit.json")
        audit = json.loads(audit_path.read_text()) if audit_path.is_file() else {"checks": []}
        checks = {c["id"]: c for c in audit["checks"]}
        def minimum(kind):
            result = checks.get("contrast." + kind, {}).get("observed", {}).get("minimum")
            return f"{result:.3f}:1" if result is not None else "—"
        failed = ", ".join(c["id"] for c in audit["checks"] if not c["passed"]) or "—"
        lines.append(f'| {surface} | {item["status"]} | {item["contract_status"]} | {minimum("text")} | {minimum("indicator")} | {failed} |')
    if errors:
        lines += ["", "Verification failures:", *("- " + str(error).replace("\n", " ") for error in errors)]
    lines += ["", "See the uploaded native review artifact for exact SVGs, grids, raw output and coordinate-level audit JSON.", ""]
    with path.open("a") as out:
        out.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-dir", type=Path, required=True)
    parser.add_argument("--profile", choices=("theme", "zellij"))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--preset", required=True)
    parser.add_argument("--colors", type=Path)
    parser.add_argument("--require-treesitter", action="store_true", help="Require actual Neovim language captures in Tree-sitter mode")
    parser.add_argument("--gallery-dir", type=Path, help="Require every published SVG to match the verified artifact bytes")
    parser.add_argument("--summary", type=Path, help="Append measured results to a review summary")
    parser.add_argument("--export-gallery", type=Path, help="Copy exact SVGs only after every required check passes")
    args = parser.parse_args()
    try:
        failures = verify_review(args.verify_dir, profile=args.profile, commit=args.commit,
                                 preset=args.preset, colors=args.colors, gallery=args.gallery_dir,
                                 require_treesitter=args.require_treesitter)
    except (ValueError, OSError, KeyError, TypeError) as error:
        if args.summary and (args.verify_dir / "manifest.json").is_file():
            write_summary(args.summary, args.verify_dir, "evidence invalid", [error])
        raise
    if args.summary:
        write_summary(args.summary, args.verify_dir, "failed" if failures else "checks passed", failures)
    if failures:
        raise SystemExit("Native review contract failed:\n" + "\n".join(failures))
    if args.export_gallery:
        export_gallery(args.verify_dir, args.export_gallery, profile=args.profile,
                       commit=args.commit, preset=args.preset, colors=args.colors)
    print("Native review contract: verified evidence and all applicable checks passed (not visual approval)")
