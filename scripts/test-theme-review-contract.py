#!/usr/bin/env python3
"""Negative controls for the independent native visual acceptance contract."""
import copy
import json
import tomllib
from pathlib import Path
import shutil
import tempfile
import unittest

from theme_review import render_svg
import theme_review_contract as review


POLICY = tomllib.loads(review.CONTRACT.read_text())
# Fixed historical Sage values keep the bad and corrected specimens independent
# of future changes to the compiler or adapter under test.
THEME = {
    "theme": "sage", "symbols": "unicode",
    "roles": {
        "surface": "#0D1513", "surface.raised": "#17231E",
        "text": "#D7DFD9", "text.strong": "#EEF1EE", "text.inverse": "#0D1513",
        "text.muted": "#A3B1A7", "accent": "#ACC8B7", "focus": "#C4B2D9",
        "status.info": "#8CC5CC", "status.error": "#F18C96",
        "status.attention": "#DDA783",
    },
    "ansi": ["#17231E", "#F18C96", "#A6CD82", "#E8C88B", "#95B5D3", "#C4B2D9", "#8CC5CC", "#D7DFD9",
             "#9CAB9F", "#F18C96", "#A6CD82", "#E8C88B", "#95B5D3", "#C4B2D9", "#8FB9A8", "#EEF1EE"],
}


def row(text, fg="default", bg="default", width=100):
    return [{"data": ch, "fg": fg.lstrip("#"), "bg": bg.lstrip("#"), "bold": False,
             "italics": False, "underscore": False, "reverse": False}
            for ch in text.ljust(width)]


def paint(cells, label, fg, bg):
    start, end = review.span(cells, label)
    for cell in cells[start:end]:
        cell.update(fg=fg.lstrip("#"), bg=bg.lstrip("#"))


def bottom():
    return [row("Name(n) CPU%(c) Mem%(m) PID(p)"),
            row("producer  1.8%  0.6%  123", "#EEF1EE", "#5E7067"),
            row("publisher  0.3%  0.4%  456")]


def tmux():
    roles = THEME["roles"]
    cells = row(" fixture  0:Editor  ◐  1:Publisher ×  2:Checks !  3:Shell")
    paint(cells, "0:Editor", roles["text.inverse"], roles["focus"])
    for label in ("1:Publisher", "2:Checks", "3:Shell"):
        paint(cells, label, roles["text.muted"], roles["surface"])
    for glyph, role in (("◐", "status.info"), ("×", "status.error"), ("!", "status.attention")):
        paint(cells, glyph, roles[role], roles["surface"])
    return [row("Workspace review"), cells]


def report(surface, rows):
    return review.audit_capture(surface, rows, THEME, POLICY)


def failures(audit):
    return {c["id"] for c in audit["checks"] if not c["passed"]}


class NativeReviewContractTests(unittest.TestCase):
    def test_dense_selection_rejects_both_excessive_and_invisible_fill(self):
        self.assertEqual(report("bottom", bottom())["status"], "pass")
        for fg, bg in (("#0D1513", "#ACC8B7"), ("#EEF1EE", "#26352D")):
            specimen = bottom()
            specimen[1] = row("producer  1.8%  0.6%  123", fg, bg)
            bad = failures(report("bottom", specimen))
            self.assertIn("bottom.fill-emphasis", bad)
            # Both mutations pass text contrast. Contrast alone would miss them.
            self.assertNotIn("contrast.text", bad)
        specimen = bottom()
        specimen[2] = copy.deepcopy(specimen[1])
        self.assertIn("bottom.unique-selection", failures(report("bottom", specimen)))

    def test_inactive_status_ribbon_and_wrong_marker_are_rejected(self):
        specimen = tmux()
        audit = report("tmux", specimen)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(json.loads(json.dumps(audit)), audit, "audit must replay from JSON without type changes")
        paint(specimen[-1], "1:Publisher", "#0D1513", "#F18C96")
        bad = failures(report("tmux", specimen))
        self.assertIn("tmux.no-inactive-ribbons", bad)
        self.assertNotIn("contrast.text", bad)
        specimen = tmux()
        paint(specimen[-1], "×", "#A3B1A7", "#0D1513")
        self.assertIn("tmux.marker.status.error", failures(report("tmux", specimen)))

    def test_actual_low_contrast_and_incomplete_fixture_are_rejected(self):
        specimen = [row("code.lua"), row("1 local retries = 3"), row('print(greet("world"), retries)')]
        self.assertEqual(report("bat", specimen)["status"], "pass")
        paint(specimen[1], "1", "#444444", "#0D1513")
        self.assertIn("contrast.text", failures(report("bat", specimen)))
        specimen[-1] = row(" ")
        self.assertIn("fixture.content", failures(report("bat", specimen)))

    def test_plain_session_heading_rejects_fill_and_missing_weight(self):
        specimen = [row(" work 0:Shell 1:Editor 2:Publisher"), row("zellij-ready>")]
        for cell in specimen[0][:6]:
            cell["bold"] = True
        self.assertEqual(report("zellij", specimen)["status"], "pass")
        for cell in specimen[0][:6]:
            cell.update(fg="0d1513", bg="acc8b7")
        self.assertIn("zellij.plain-heading", failures(report("zellij", specimen)))
        for cell in specimen[0][:6]:
            cell.update(fg="d7dfd9", bg="0d1513", bold=False)
        self.assertIn("zellij.plain-heading", failures(report("zellij", specimen)))

    def test_primitives_are_reusable_and_fail_closed(self):
        policy = copy.deepcopy(POLICY)
        policy["surfaces"]["process-table"] = copy.deepcopy(policy["surfaces"]["bottom"])
        self.assertEqual(review.audit_capture("process-table", bottom(), THEME, policy)["status"], "pass")
        specimen = bottom()
        specimen[1] = row("producer  1.8%  0.6%  123", "#0D1513", "#ACC8B7")
        self.assertIn("process-table.fill-emphasis",
                      failures(review.audit_capture("process-table", specimen, THEME, policy)))
        policy["surfaces"]["process-table"]["primitives"].append({"kind": "misspelled"})
        with self.assertRaisesRegex(ValueError, "unknown visual primitive"):
            review.audit_capture("process-table", bottom(), THEME, policy)

    def test_evidence_replay_rejects_altered_or_omitted_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = bottom()
            shutil.copyfile(review.CONTRACT, root / "review-contract.toml")
            data = {
                "colors.json": THEME,
                "bottom.grid.json": rows,
                "bottom.json": review.compact_grid(rows),
                "bottom.audit.json": report("bottom", rows),
            }
            for name, value in data.items():
                (root / name).write_text(json.dumps(value))
            (root / "bottom.svg").write_text(render_svg("bottom", rows, THEME, trim=False))
            (root / "bottom.ansi").write_bytes(b"synthetic unit-test observation")
            files = ["bottom" + suffix for suffix in (".grid.json", ".json", ".audit.json", ".svg", ".ansi")]
            item = {"status": "captured", "contract_status": "pass", "rows": len(rows),
                    "columns": len(rows[0]), "sha256": {name: review.sha256(root / name) for name in files}}
            manifest = {
                "schema": 2, "commit": "unit-test-checkout", "preset": "sage", "symbols": "unicode",
                "contract_sha256": review.sha256(review.CONTRACT),
                "colors_sha256": review.sha256(root / "colors.json"),
                "auditor_sha256": review.sha256(Path(review.__file__)),
                "renderer_sha256": review.sha256(Path(review.__file__).with_name("theme_review.py")),
                "required_surfaces": ["bottom"], "surfaces": {"bottom": item},
            }
            def save():
                (root / "manifest.json").write_text(json.dumps(manifest))
            save()
            def verify(**kwargs):
                return review.verify_review(root, commit="unit-test-checkout", preset="sage", **kwargs)
            self.assertEqual(verify(), [])
            with self.assertRaisesRegex(ValueError, "coverage"):
                verify(profile="theme")
            gallery = root / "gallery"
            gallery.mkdir()
            self.assertTrue(verify(gallery=gallery))
            shutil.copyfile(root / "bottom.svg", gallery / "bottom.svg")
            self.assertEqual(verify(gallery=gallery), [])
            item.update(status="capture-failed", contract_status="fail", grid="bottom.grid.json")
            save()
            self.assertIn("bottom: capture failed", verify(gallery=gallery))
            summary = root / "summary.md"
            review.write_summary(summary, root, "failed", ["bottom: capture failed"])
            self.assertIn("capture-failed", summary.read_text())
            self.assertIn("Human approval: pending", summary.read_text())
            item.update(status="captured", contract_status="pass")
            save()
            (gallery / "bottom.svg").write_text("recolored")
            self.assertTrue(verify(gallery=gallery))
            (root / "bottom.svg").write_text("recolored")
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                verify()
            # Rehashing a hand-edited image still cannot pass deterministic replay.
            item["sha256"]["bottom.svg"] = review.sha256(root / "bottom.svg")
            save()
            with self.assertRaisesRegex(ValueError, "does not replay"):
                verify()


if __name__ == "__main__":
    unittest.main()
