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
        "syntax.member": "#8FB9A8", "syntax.string": "#B7CB91",
        "syntax.variable": "#D7DFD9", "syntax.type": "#B7BDE3",
        "syntax.number": "#C4B2D9", "syntax.operator": "#95B5D3", "syntax.special": "#E8C88B",
        "syntax.keyword": "#95B5D3",
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
    cells = row(" fixture  0:Editor  ◐  1:Publisher   2:Checks   3:Shell")
    paint(cells, "0:Editor", roles["text.inverse"], roles["focus"])
    for label in ("1:Publisher", "2:Checks", "3:Shell"):
        paint(cells, label, roles["text.muted"], roles["surface"])
    for glyph, role in (("◐", "status.info"), ("", "status.error"), ("", "status.attention")):
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
        paint(specimen[-1], "", "#A3B1A7", "#0D1513")
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

    def test_language_profile_and_monochrome_negative_control(self):
        self.assertEqual(len(POLICY["languages"]), 9)
        for language, fixture in POLICY["languages"].items():
            self.assertTrue((review.ROOT / fixture["file"]).is_file())
            for app in ("neovim", "bat"):
                surface = f"{app}-code-{language}"
                self.assertIn(surface, POLICY["profiles"]["theme"])
                self.assertIn(surface, POLICY["surfaces"])
        surface = "bat-code-rust"
        anchors = POLICY["surfaces"][surface]["anchors"]
        specimen = [row(anchor) for anchor in anchors]
        self.assertIn(surface + ".syntax-diversity", failures(report(surface, specimen)))
        for i, color in enumerate(("#95B5D3", "#8CC5CC", "#B7CB91"), start=1):
            paint(specimen[i], anchors[i], color, "#0D1513")
        specimen.extend([
            row("attempt: u32) -> Option<u64>"),
            row("Some(ms) if n < 3 => Outcome::Retry(ms)"),
            row("-> Outcome<'a>"),
        ])
        for label in ("u32", "Option", "u64"):
            paint(specimen[-3], label, "#B7BDE3", "#0D1513")
        for label, color in (("Some", "#B7BDE3"), ("3", "#C4B2D9"), ("=>", "#95B5D3"), ("Outcome", "#B7BDE3")):
            paint(specimen[-2], label, color, "#0D1513")
        paint(specimen[-1], "Outcome", "#B7BDE3", "#0D1513")
        paint(specimen[-1], "'a", "#E8C88B", "#0D1513")
        trait_bound = row("&impl Policy, n: u32")
        paint(trait_bound, "impl", "#95B5D3", "#0D1513")
        paint(trait_bound, "Policy", "#B7BDE3", "#0D1513")
        specimen.append(trait_bound)
        declaration = row("let retry = match outcome")
        paint(declaration, "let", "#95B5D3", "#0D1513")
        specimen.append(declaration)
        self.assertEqual(report(surface, specimen)["status"], "pass")

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

    def test_syntax_roles_reject_readable_but_wrong_ink(self):
        surface = "bat-code-json"
        rule = POLICY["surfaces"][surface]
        specimen = [row(anchor) for anchor in rule["anchors"]]
        for label, fg in (("true", "#C4B2D9"), ("delays_ms", "#8FB9A8"), ("null", "#C4B2D9")):
            cells = next(cells for cells in specimen if review.span(cells, label))
            paint(cells, label, fg, "#0D1513")
        pair = row('"state": "blocked"')
        paint(pair, "state", "#8FB9A8", "#0D1513")
        paint(pair, "blocked", "#B7CB91", "#0D1513")
        specimen.append(pair)
        self.assertEqual(report(surface, specimen)["status"], "pass")
        check_id = surface + ".syntax-roles.key-and-value"
        for bad in (specimen[:-1], specimen + [copy.deepcopy(pair)]):
            self.assertEqual(failures(report(surface, bad)), {check_id})
        paint(pair, "state", "#B7CB91", "#0D1513")
        audit = report(surface, specimen)
        self.assertEqual(failures(audit), {check_id})
        check = next(check for check in audit["checks"] if check["id"] == check_id)
        self.assertEqual(check["expected"]["tokens"]["state"], {"role": "syntax.member", "fg": "#8FB9A8"})
        self.assertEqual(check["observed"]["tokens"]["state"]["cells"][0], {"column": 2, "fg": "#B7CB91"})

        collapsed = copy.deepcopy(THEME)
        collapsed["roles"]["syntax.member"] = collapsed["roles"]["syntax.string"]
        self.assertEqual(failures(review.audit_capture(surface, specimen, collapsed, POLICY)), {check_id})

    def test_treesitter_role_checks_run_only_in_the_requested_engine(self):
        policy = copy.deepcopy(POLICY)
        surface = "neovim-code-example"
        policy["surfaces"][surface] = {"anchors": ["self.value"], "primitives": [{
            "kind": "syntax-roles", "name": "member", "anchor": "self.value",
            "tokens": {"value": "syntax.member"}, "treesitter_only": True,
        }]}
        cells = [row("self.value")]
        self.assertEqual(review.audit_capture(surface, cells, THEME, policy)["status"], "pass")
        self.assertEqual(failures(review.audit_capture(surface, cells, THEME, policy, neovim_syntax="treesitter")),
                         {surface + ".syntax-roles.member"})

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
            with self.assertRaisesRegex(ValueError, "requires Neovim language captures from Tree-sitter"):
                verify(require_treesitter=True)
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
