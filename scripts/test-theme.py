#!/usr/bin/env python3
"""Exercise theme compilation, invalid inputs and native configuration wiring."""

import copy
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import xml.etree.ElementTree as ET
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("theme", ROOT / "scripts/theme.py")
theme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(theme)



def write_definition(path, data):
    """Write fixture TOML without introducing a production writer dependency."""
    def encode(value):
        if isinstance(value, dict):
            return "{ " + ", ".join(json.dumps(k) + " = " + encode(v) for k, v in value.items()) + " }"
        if isinstance(value, list):
            return "[" + ", ".join(encode(v) for v in value) + "]"
        if value is None:
            return "false"  # TOML has no null; this is still invalid for a string token.
        return json.dumps(value, ensure_ascii=False)
    path.write_text("".join(json.dumps(k) + " = " + encode(v) + "\n" for k, v in ({"items": data} if isinstance(data, list) else data).items()))


class ThemeTests(unittest.TestCase):
    def test_canonical_palette_and_aliases(self):
        data = theme.read(theme.SOURCE / "themes/nord.toml")
        colors, value = theme.resolve(data, theme.read(theme.SOURCE / "tokens.toml")["roles"])
        self.assertEqual(colors["surface"], "#2E3440")
        self.assertEqual(colors["accent"], "#88C0D0")
        self.assertEqual(colors["focus"], "#B48EAD")
        self.assertEqual(colors["tab.active.bg"], "#B48EAD")
        self.assertEqual(colors["tab.active.fg"], "#2E3440")
        self.assertEqual(colors["diff.add"], "#A3BE8C")
        self.assertEqual(value("default"), "default")
        self.assertEqual(colors["diff.add.bg"], "#414A4C")
        self.assertEqual(colors["git.file.modified"], "#EBCB8B")
        self.assertEqual(colors["git.file.stashed"], "#E5E9F0")

    def test_sage_preset_contrast_and_native_outputs(self):
        def luminance(color):
            channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))

        def contrast(a, b):
            low, high = sorted((luminance(a), luminance(b)))
            return (high + 0.05) / (low + 0.05)

        for symbols in ("unicode", "ascii"):
            with self.subTest(symbols=symbols):
                outputs = theme.compile_theme(theme.SOURCE, "sage", symbols)
                self.assertEqual(set(outputs), {p.name for p in (theme.SOURCE / "generated").iterdir()})
                self.assertEqual(outputs, theme.compile_theme(theme.SOURCE, "sage", symbols))
                resolved = json.loads(outputs["colors.json"])
                self.assertEqual(resolved["theme"], "sage")
                self.assertEqual(resolved["symbols"], symbols)
                self.assertEqual(len(resolved["ansi"]), 16)
                colors = resolved["roles"]
                self.assertEqual(colors["surface"], "#0D1513")
                self.assertEqual(colors["surface.raised"], "#17231E")
                self.assertEqual(colors["surface.selected"], "#26352D")
                self.assertEqual(colors["accent"], "#ACC8B7")
                self.assertEqual(colors["focus"], "#C4B2D9")
                self.assertEqual(colors["status.error"], "#F18C96")
                self.assertEqual(colors["text.subtle"], "#909F95")
                self.assertEqual(colors["status.off"], colors["text.subtle"])
                self.assertEqual(colors["border"], "#6B8575")
                self.assertEqual(colors["diff.add.emph.bg"], "#2C3A29")
                self.assertEqual(colors["diff.delete.emph.bg"], "#3B2D2D")
                self.assertEqual(colors["diff.add"], colors["status.success"])
                self.assertEqual(colors["diff.delete"], colors["status.error"])
                self.assertEqual(colors["git.file.staged"], colors["status.success"])
                self.assertEqual(colors["git.file.modified"], colors["status.warning"])
                self.assertEqual(colors["git.file.deleted"], colors["status.error"])
                self.assertEqual(colors["tab.active.bg"], colors["focus"])
                self.assertEqual(len({colors[r] for r in ("accent", "focus", "status.success",
                                                          "status.warning", "status.error",
                                                          "status.info", "status.attention")}), 7)
                for background in ("surface", "surface.raised", "surface.selected"):
                    for foreground in ("text", "text.strong", "text.muted", "accent",
                                       "accent.secondary", "focus", "status.success",
                                       "status.warning", "status.error", "status.info",
                                       "status.attention", "status.idle",
                                       *(r for r in colors if r.startswith("syntax."))):
                        with self.subTest(background=background, foreground=foreground):
                            self.assertGreaterEqual(contrast(colors[background], colors[foreground]), 4.5)
                self.assertGreaterEqual(contrast(colors["tab.active.bg"], colors["tab.active.fg"]), 4.5)
                self.assertGreaterEqual(contrast(colors["status.error"], colors["surface"]), 4.5)
                self.assertGreaterEqual(contrast(colors["accent"], colors["surface.selected"]), 3)
                self.assertGreaterEqual(contrast(colors["accent"], colors["text.subtle"]), 1.5)
                self.assertGreater(contrast(colors["text.muted"], colors["text.subtle"]), 1)
                for background in ("surface", "surface.raised", "surface.selected"):
                    self.assertGreaterEqual(contrast(colors["border"], colors[background]), 3)
                for background in ("diff.add.bg", "diff.delete.bg", "diff.change.bg",
                                   "diff.add.emph.bg", "diff.delete.emph.bg"):
                    for foreground in ("text", "status.error", *(r for r in colors if r.startswith("syntax."))):
                        with self.subTest(diff_background=background, foreground=foreground):
                            self.assertGreaterEqual(contrast(colors[background], colors[foreground]), 4.5)
                for group in theme.read(theme.SOURCE / "semantic-states.toml"):
                    for state in group["states"]:
                        for background in ("surface", "surface.raised", "surface.selected"):
                            with self.subTest(state=state["id"], background=background):
                                self.assertGreaterEqual(contrast(colors[state["role"]], colors[background]), 4.5)

    def test_sage_native_contrast_contract(self):
        """Check actual filled styles, text roles and essential non-text indicators."""
        def luminance(color):
            channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))

        def check(label, fg, bg, minimum=4.5):
            low, high = sorted((luminance(fg), luminance(bg)))
            with self.subTest(pair=label, fg=fg, bg=bg, minimum=minimum):
                self.assertGreaterEqual((high + 0.05) / (low + 0.05), minimum)

        outputs = theme.compile_theme(theme.SOURCE, "sage")
        resolved = json.loads(outputs["colors.json"])
        c = resolved["roles"]
        surfaces = [c[name] for name in ("surface", "surface.raised", "surface.selected")]
        for bg in surfaces:
            check("readable off/trace/metadata", c["status.off"], bg)
            check("inactive frame text", c["frame.inactive.fg"], bg)
            check("required border", c["border"], bg, 3)
            check("selection pointer", c["accent"], bg, 3)
            check("solid selection fill", c["selection.solid.bg"], bg, 3)
            for role, color in c.items():
                if role.startswith("git.file."):
                    check(role, color, bg)
                if role.startswith("diff.") and role.endswith(".dim"):
                    check(role, color, bg, 3)

        preset = theme.read(theme.SOURCE / "themes/sage.toml")
        _, value = theme.resolve(preset, theme.read(theme.SOURCE / "tokens.toml")["roles"])
        check("inverse selection text", c["selection.solid.fg"], c["selection.solid.bg"])
        check("bat gutter text", c["gutter.text"], c["surface"])
        check("bat gutter geometry", c["gutter.border"], c["surface"], 3)
        import plistlib
        settings = plistlib.loads(outputs["Dotfiles.tmTheme"].encode())["settings"][0]["settings"]
        self.assertEqual(settings["gutterForeground"], c["gutter.text"])
        self.assertEqual(settings["gutter"], c["surface"])
        for name, role in (("left", "gutter.border"), ("right", "gutter.border"),
                           ("zero", "gutter.text"), ("minus", "status.error"), ("plus", "status.success")):
            self.assertIn(f'line-numbers-{name}-style = "{c[role]}"', outputs["delta.gitconfig"])
            check("delta gutter " + name, c[role], c["surface"], 3 if name in ("left", "right") else 4.5)
        check("tmux inactive pane title", c["text.on.border"], c["border"])
        self.assertIn(f'#[bg={c["border"]}]#[fg={c["text.on.border"]}]', outputs["tmux.conf"])
        states = theme.expand(theme.read(theme.SOURCE / "adapters/tmux-states.toml"), value)
        for name, style in states.items():
            check("tmux state " + name, style["fg"], style["bg"])
        self.assertEqual(states["failed"]["fg"], c["text.inverse"])
        # Only the active tab label is filled; state markers are separate
        # readable foreground colors on the dark status surface.
        for name, style in states.items():
            marker = style["fg"] if name in ("idle", "dormant") else style["bg"]
            check("tmux compact state marker " + name, marker, c["surface"])
        check("tmux active label", c["tab.active.fg"], c["tab.active.bg"])
        check("tmux active fill", c["tab.active.bg"], c["surface"], 3)
        check("tmux inactive label", c["text.muted"], c["surface"])
        self.assertIn("window-status-separator \"  \"", outputs["tmux.conf"])
        self.assertIn(" #I:#W ", outputs["tmux.conf"])
        self.assertIn("window-status-format", outputs["tmux.conf"])
        self.assertTrue(json.loads(outputs["tokens.json"])["presentation"]["tmux.tabs.compact"]["resolved"])

        glow = json.loads(outputs["glow.json"])
        for label, style in (("Glow h1", glow["h1"]), ("Glow inline code", glow["code"]),
                             ("Glow error", glow["code_block"]["chroma"]["error"])):
            check(label, style["color"], style["background_color"])

        kitty = dict(line.split() for line in outputs["kitty.conf"].splitlines() if not line.startswith("#"))
        check("Kitty selection ink", kitty["selection_foreground"], kitty["selection_background"])
        check("Kitty selection fill", kitty["selection_background"], kitty["background"], 3)
        check("Kitty active tab", kitty["active_tab_foreground"], kitty["active_tab_background"])
        check("Kitty inactive tab", kitty["inactive_tab_foreground"], kitty["inactive_tab_background"])

        bottom = tomllib.loads(outputs["bottom.toml"])["styles"]["widgets"]
        selected = bottom["selected_text"]
        self.assertEqual(selected["color"], c["selection.row.fg"])
        self.assertEqual(selected["bg_color"], c["selection.row.bg"])
        self.assertNotEqual(selected["bg_color"], c["selection.solid.bg"])
        self.assertEqual(selected["color"], c["text.strong"])
        check("bottom selected row", selected["color"], selected["bg_color"])
        for surface in ("surface", "surface.raised"):
            check("bottom selected fill on " + surface, selected["bg_color"], c[surface], 3)
        # Keep the selection readable without turning a full-width row into
        # an accent banner. White ink and the text floor bound the fill luminance.
        self.assertLess(luminance(selected["bg_color"]), luminance(c["accent"]))
        nord = tomllib.loads(theme.compile_theme(theme.SOURCE, "nord")["bottom.toml"])
        self.assertEqual(nord["styles"]["widgets"]["selected_text"],
                         {"color": "#ECEFF4", "bg_color": "#434C5E"})

        neovim = theme.read(theme.SOURCE / "adapters/neovim.toml")
        for name in ("LineNr", "FoldColumn", "SignColumn", "SpecialKey", "Conceal"):
            style = theme.expand(neovim[name], value)
            for bg in surfaces:
                check("Neovim " + name, style["fg"], bg)
        for name in ("Visual", "VisualNOS", "PmenuSel", "QuickFixLine"):
            style = theme.expand({k: v for k, v in neovim[name].items() if k != "component"}, value)
            check("Neovim " + name, style["fg"], style["bg"])
            for bg in surfaces:
                check("Neovim " + name + " fill", style["bg"], bg, 3)
            self.assertIn(f'["{name}"] = ' + theme.lua(style), outputs["neovim.lua"])
        check("Neovim scrollbar thumb", value(neovim["PmenuThumb"]["bg"]),
              value(neovim["PmenuSbar"]["bg"]), 3)

        zellij = theme.read(theme.SOURCE / "adapters/zellij.toml")
        for name in ("text_selected", "list_selected", "table_cell_selected", "ribbon_selected"):
            style = {k: value("@" + role) for k, role in zellij[name].items()}
            for field in ("base", "emphasis_0", "emphasis_1", "emphasis_2", "emphasis_3"):
                check("Zellij " + name + " " + field, style[field], style["background"])
            for bg in surfaces:
                check("Zellij " + name + " fill", style["background"], bg, 3)

        pi = json.loads(outputs["pi.json"])["colors"]
        for bg in (c["surface"], pi["userMessageBg"], pi["selectedBg"]):
            check("Pi thinking off", pi["thinkingOff"], bg)
        check("Pi tool error output", pi["toolOutput"], pi["toolErrorBg"])
        check("Pi tool error status", pi["error"], pi["toolErrorBg"])

    def test_atuin_semantic_theme(self):
        adapter = theme.read(theme.SOURCE / "adapters/atuin.toml")
        for preset in ("nord", "sage"):
            outputs = theme.compile_theme(theme.SOURCE, preset)
            colors = json.loads(outputs["colors.json"])["roles"]
            native = tomllib.loads(outputs["atuin.toml"])
            self.assertEqual(native["theme"]["name"], "dotfiles")
            self.assertEqual(native["colors"], {name: colors[role] for name, role in adapter.items()})
        config = tomllib.loads((ROOT / "sh/atuin.toml").read_text())
        self.assertEqual(config["theme"]["name"], "dotfiles")
        self.assertTrue(config["auto_sync"])

    def test_universal_role_schema(self):
        shared = theme.read(theme.SOURCE / "tokens.toml")
        expected = set(shared["roles"]) | set(shared["required_roles"])
        for name in ("nord", "sage"):
            data = theme.read(theme.SOURCE / "themes" / f"{name}.toml")
            colors, value = theme.resolve(data, shared["roles"])
            self.assertEqual(set(colors), expected)
            self.assertEqual(value("@text.on.error"), colors["text.on.error"])
            self.assertEqual(theme.render_roles("{{text.on.error}}", colors), colors["text.on.error"])
            with self.assertRaises(KeyError):
                value("@missing")
            with self.assertRaises(KeyError):
                value("@text.on.error|text.strong")

    def test_compiler_rejects_invalid_role_schema(self):
        with tempfile.TemporaryDirectory(prefix="theme-role-schema-") as directory:
            source = Path(directory) / "source"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            path = source / "themes/nord.toml"
            original = theme.read(path)
            for mutation in ("missing", "unknown"):
                data = copy.deepcopy(original)
                if mutation == "missing":
                    del data["roles"]["surface"]
                else:
                    data["roles"]["unregistered.role"] = "@text"
                write_definition(path, data)
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "theme role schema mismatch"):
                    theme.compile_theme(source, "nord")

    def test_semantic_state_review_catalog(self):
        groups = theme.read(theme.SOURCE / "semantic-states.toml")
        self.assertEqual([group["id"] for group in groups],
                         ["configuration", "severity", "execution", "health",
                          "interaction", "connectivity", "data", "access"])
        sage = theme.read(theme.SOURCE / "themes/sage.toml")
        nord = theme.read(theme.SOURCE / "themes/nord.toml")
        shared = theme.read(theme.SOURCE / "tokens.toml")["roles"]
        sage_roles, _ = theme.resolve(sage, shared)
        nord_roles, _ = theme.resolve(nord, shared)
        seen = set()
        for group in groups:
            for state in group["states"]:
                with self.subTest(group=group["id"], state=state["id"]):
                    key = (group["id"], state["id"])
                    self.assertNotIn(key, seen)
                    seen.add(key)
                    self.assertIn(state["role"], sage_roles)
                    self.assertIn(state["role"], nord_roles)
                    self.assertTrue(state["label"] and state["description"] and state["example"])
                    self.assertEqual(len(state["glyph"]), 1)
                    self.assertEqual(len(state["ascii"]), 1)
                    self.assertTrue(32 <= ord(state["ascii"]) <= 126)
        mapping = {(group["id"], state["id"]): state["role"]
                   for group in groups for state in group["states"]}
        self.assertEqual(mapping["configuration", "on"], "accent")
        self.assertEqual(mapping["configuration", "off"], "text.subtle")
        self.assertEqual(mapping["severity", "trace"], "text.subtle")
        self.assertEqual(mapping["severity", "debug"], "text.muted")
        self.assertEqual(mapping["severity", "info"], "status.info")
        self.assertEqual(mapping["severity", "warning"], "status.warning")
        self.assertEqual(mapping["severity", "error"], "status.error")
        self.assertEqual(mapping["execution", "succeeded"], "status.success")
        self.assertEqual(mapping["execution", "input"], "status.attention")
        self.assertEqual(mapping["health", "unknown"], "text.muted")
        self.assertEqual(len(mapping), 39)
        self.assertEqual(mapping["interaction", "focused"], "focus")
        self.assertEqual(mapping["interaction", "selected"], "accent")
        connecting = next(s for g in groups if g["id"] == "connectivity"
                          for s in g["states"] if s["id"] == "connecting")
        self.assertEqual((connecting["glyph"], connecting["ascii"]), ("◐", "~"))
        self.assertEqual(mapping["connectivity", "connected"], "accent.secondary")
        self.assertEqual(mapping["connectivity", "lost"], "status.error")
        self.assertEqual(mapping["data", "missing"], "text.muted")
        self.assertEqual(mapping["data", "stale"], "status.warning")
        self.assertEqual(mapping["access", "approval"], "status.attention")
        self.assertEqual(mapping["access", "approved"], "accent")
        approved = next(s for g in groups if g["id"] == "access"
                        for s in g["states"] if s["id"] == "approved")
        self.assertEqual((approved["glyph"], approved["ascii"]), ("✓", "+"))
        self.assertNotEqual(mapping["access", "approved"], mapping["execution", "succeeded"])
        self.assertEqual(mapping["execution", "retrying"], "status.warning")

    def test_semantic_state_tokens_are_exported_for_every_preset_and_symbol_mode(self):
        groups = theme.read(theme.SOURCE / "semantic-states.toml")
        shared = theme.read(theme.SOURCE / "tokens.toml")["roles"]
        for name in ("nord", "sage"):
            preset = theme.read(theme.SOURCE / "themes" / f"{name}.toml")
            colors, _ = theme.resolve(preset, shared)
            for symbols in ("unicode", "ascii"):
                with self.subTest(preset=name, symbols=symbols):
                    outputs = theme.compile_theme(theme.SOURCE, name, symbols)
                    exported = json.loads(outputs["tokens.json"])["semantic_states"]
                    self.assertEqual(len(exported), 39)
                    for group in groups:
                        for state in group["states"]:
                            key = group["id"] + "." + state["id"]
                            token = exported[key]
                            role = state["role"]
                            self.assertEqual(token["fg"], colors[role])
                            self.assertEqual(token["color_role"], "@" + role)
                            self.assertEqual(token["symbol"], state["ascii"] if symbols == "ascii" else state["glyph"])
                            self.assertEqual(token["bold"], state.get("bold", False))
                            self.assertEqual(token["label"], state["label"])
                            self.assertEqual(token["description"], state["description"])
                    self.assertEqual(exported["configuration.off"]["color_role"],
                                     "@text.subtle")

    def test_semantic_state_token_validation_rejects_invalid_declarations(self):
        groups = theme.read(theme.SOURCE / "semantic-states.toml")
        colors, _ = theme.resolve(theme.read(theme.SOURCE / "themes/sage.toml"),
                                  theme.read(theme.SOURCE / "tokens.toml")["roles"])
        duplicate = copy.deepcopy(groups)
        duplicate[0]["states"].append(copy.deepcopy(duplicate[0]["states"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate semantic state"):
            theme.compile_semantic_states(duplicate, colors, "unicode")
        with self.assertRaisesRegex(ValueError, "duplicate semantic family"):
            theme.compile_semantic_states(groups + [groups[0]], colors, "unicode")
        for changes, error in [
            ({"id": "bad.id"}, ValueError),
            ({"role": "missing"}, KeyError),
            ({"fallback_role": "missing"}, ValueError),
            ({"glyph": "wide"}, ValueError),
            ({"glyph": "界"}, ValueError),
            ({"ascii": "é"}, ValueError),
            ({"bold": "true"}, ValueError),
            ({"label": ""}, ValueError),
        ]:
            bad = copy.deepcopy(groups)
            bad[0]["states"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(error):
                theme.compile_semantic_states(bad, colors, "unicode")

    def test_invalid_definitions(self):
        base = theme.read(theme.SOURCE / "themes/nord.toml")
        for changes in ({"accent": {"ansi": 16}}, {"accent": {"ansi": True}}, {"accent": "@missing"}, {"accent": "@accent"}, {"accent": "#123456"}, {"accent": {"mix": ["@surface", "@text"], "amount": 2}}):
            data = copy.deepcopy(base)
            data["roles"].update(changes)
            with self.subTest(changes=changes), self.assertRaises((KeyError, ValueError)):
                theme.resolve(data, theme.read(theme.SOURCE / "tokens.toml")["roles"])

    def test_deterministic_check_and_no_writes_on_invalid_source(self):
        with tempfile.TemporaryDirectory(prefix="theme-compile-") as directory:
            work = Path(directory)
            source, output = work / "source", work / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            command = ["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)]
            subprocess.run(command, check=True)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            subprocess.run([*command, "--check"], check=True)
            (output / "kitty.conf").write_text("broken\n")
            result = subprocess.run([*command, "--check"], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((output / "kitty.conf").read_text(), "broken\n")
            subprocess.run(command, check=True)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
            data = theme.read(source / "themes/nord.toml")
            data["roles"]["accent"] = "@missing"
            write_definition(source / "themes/nord.toml", data)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_ansi_cycles_preserve_outputs(self):
        with tempfile.TemporaryDirectory(prefix="theme-ansi-") as directory:
            source, output = Path(directory) / "source", Path(directory) / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            command = ["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)]
            subprocess.run(command, check=True)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            original = theme.read(source / "themes/nord.toml")
            for slots in ({3: {"ansi": 3}}, {3: {"ansi": 4}, 4: {"ansi": 3}}, {3: "@git.file.modified"}):
                data = copy.deepcopy(original)
                for slot, definition in slots.items():
                    data["ansi"][slot] = definition
                write_definition(source / "themes/nord.toml", data)
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertRegex(result.stderr, "cyclic (ANSI slot|role)")
                self.assertNotIn("RecursionError", result.stderr)
                self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_selected_preset_has_no_downstream_naming_dependency(self):
        with tempfile.TemporaryDirectory(prefix="theme-preset-") as directory:
            work = Path(directory)
            source, output = work / "source", work / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            original = source / "themes/nord.toml"
            data = json.loads(json.dumps(theme.read(original)).replace("$nord", "$swatch"))
            data["name"] = "forest"
            data["palette"] = {key.replace("nord", "swatch"): value for key, value in data["palette"].items()}
            data["palette"]["swatch8"] = "#74B87A"
            data["palette"]["swatch12"] = "#C3A568"
            write_definition(source / "themes/forest.toml", data)
            original.unlink()
            write_definition(source / "config.toml", {"theme": "forest"})
            command = ["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)]
            subprocess.run(command, check=True)
            subprocess.run([*command, "--check"], check=True)
            self.assertEqual({p.name for p in output.iterdir()}, {p.name for p in (theme.SOURCE / "generated").iterdir()})
            resolved = json.loads((output / "colors.json").read_text())
            self.assertEqual(resolved["theme"], "forest")
            self.assertEqual(resolved["roles"]["accent"], "#74B87A")
            self.assertEqual(resolved["roles"]["status.attention"], "#C3A568")
            colored = subprocess.check_output([str(ROOT / "bin/dotfiles-theme"), "--color=always"], text=True, env={**os.environ, "DOTFILES_THEME_DIR": str(output)})
            self.assertIn("\x1b[38;2;116;184;122m", colored)
            self.assertIn("\x1b[38;2;195;165;104m", colored)
            for artifact in output.iterdir():
                self.assertNotIn("nord", artifact.read_text().lower())

    def test_ascii_representation_and_validation_preserve_outputs(self):
        with tempfile.TemporaryDirectory(prefix="theme-ascii-") as directory:
            source, output = Path(directory) / "source", Path(directory) / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            command = ["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)]
            write_definition(source / "config.toml", {"theme": "nord", "symbols": "ascii"})
            subprocess.run(command, check=True)
            catalog = theme.read(output / "tokens.json")
            self.assertEqual(catalog["symbols"], "ascii")
            self.assertEqual(catalog["git_states"]["git.file.modified"]["symbol"], "~")
            self.assertEqual(catalog["git_states"]["git.file.staged"]["symbol"], "")
            self.assertTrue(all(token["resolved"].isascii() and len(token["resolved"]) <= 1 for name, token in catalog["presentation"].items() if name.startswith("symbol.")))
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            shared = theme.read(source / "tokens.toml")
            for invalid in (None, "wide", "é", "\n"):
                shared["presentation"]["symbol.git.file.modified"]["ascii"] = invalid
                write_definition(source / "tokens.toml", shared)
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ASCII fallback", result.stderr)
                self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_composition_rejects_missing_and_cyclic_references(self):
        with tempfile.TemporaryDirectory(prefix="theme-catalog-") as directory:
            source = Path(directory)
            for catalog in ([{"id": "a", "level": "atom", "composes": ["absent"]}], [{"id": "a", "level": "atom", "composes": ["a"]}]):
                write_definition(source / "catalog.toml", catalog)
                with self.assertRaises((KeyError, ValueError)):
                    theme.validate_catalog(source)

    def test_source_entrypoints_before_runtime_build(self):
        with tempfile.TemporaryDirectory(prefix="theme-entrypoints-") as directory:
            root = Path(directory)
            source, commands = root / "design-system", root / "bin"
            source.mkdir()
            commands.mkdir()
            (commands / "script").write_text("print('fixture')\n")
            (commands / "alias").symlink_to("build/not-yet-built")
            (commands / "directory").mkdir()
            with mock.patch.object(theme, "ROOT", root):
                for name, accepted in (("script", True), ("alias", True), ("missing", False), ("directory", False)):
                    for location in ("catalog", "integration"):
                        paths = ["bin/" + name]
                        write_definition(source / "catalog.toml", [{"id": "fixture", "level": "atom", "sources": paths if location == "catalog" else []}])
                        write_definition(source / "integrations.toml", [{"sources": paths if location == "integration" else []}])
                        with self.subTest(name=name, location=location):
                            if accepted:
                                theme.validate_catalog(source)
                            else:
                                with self.assertRaisesRegex(ValueError, "missing " + location + " source"):
                                    theme.validate_catalog(source)

    def test_presentation_validation_and_failure_preserve_outputs(self):
        with tempfile.TemporaryDirectory(prefix="theme-tokens-") as directory:
            work = Path(directory)
            source, output = work / "source", work / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            command = ["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)]
            subprocess.run(command, check=True)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            preset = theme.read(source / "themes/nord.toml")
            for override in ({"symbol.separator.section.left": "%Y"}, {"missing": True}, {"emphasis.heading": 1}, {"space.inline": True}, {"space.inline": -1}, {"symbol.git.file.modified": "bad\nline"}, {"emphasis.heading": {"token": "space.inline"}}, {"emphasis.heading": {"token": "emphasis.heading"}}, {"emphasis.heading": {"token": "missing"}}):
                with self.subTest(override=override):
                    write_definition(source / "themes/nord.toml", {**preset, "presentation": override})
                    self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
                    self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
            write_definition(source / "themes/nord.toml", preset)
            shared = theme.read(source / "tokens.toml")
            shared["presentation"]["space.inline"]["unit"] = "row"
            write_definition(source / "tokens.toml", shared)
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expected unit cell", result.stderr)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_presentation_alias_types_units_and_empty_symbols(self):
        tokens = theme.Presentation({"a": {"type": "dimension", "unit": "cell", "value": 1}, "b": {"type": "dimension", "unit": "cell", "value": {"token": "a"}}, "empty": {"type": "string", "value": ""}}, {"a": 2})
        self.assertEqual(tokens.reference({"token": "b", "as": "spaces"}, "glow"), "  ")
        self.assertEqual(tokens.get("empty"), "")
        with self.assertRaises(ValueError):
            theme.Presentation({"a": {"type": "dimension", "unit": "pixel", "value": 1}}, {})
        with self.assertRaises(ValueError):
            tokens.reference({"token": "empty", "as": "spaces"}, "glow")

    def test_configuration_links_without_generator_or_applications(self):
        with tempfile.TemporaryDirectory(prefix="theme-config-") as directory:
            home = Path(directory)
            for target in ("shell", "tmux-config", "kitty-config"):
                subprocess.run(["bash", str(ROOT / "scripts/make/config.sh"), target, str(ROOT), str(home), "uv", "Darwin"], check=True, capture_output=True)
            self.assertEqual((home / ".config/dotfiles/theme").resolve(), theme.SOURCE / "generated")
            self.assertEqual((home / ".config/bottom/bottom.toml").resolve(), theme.SOURCE / "generated/bottom.toml")
            self.assertEqual((home / ".config/atuin/themes/dotfiles.toml").resolve(), theme.SOURCE / "generated/atuin.toml")
            self.assertEqual((home / ".config/eza/theme.yml").resolve(), theme.SOURCE / "generated/eza.yml")
            self.assertTrue((home / ".config/bat/themes/Dotfiles.tmTheme").is_file())
            self.assertEqual((home / ".config/glow/theme.json").resolve(), theme.SOURCE / "generated/glow.json")

    @unittest.skipUnless(shutil.which("eza"), "native eza is not installed")
    def test_eza_roles_and_git_states_through_native_consumers(self):
        with tempfile.TemporaryDirectory(prefix="theme-eza-") as directory:
            work = Path(directory)
            source, output, home = work / "source", work / "output", work / "home"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            preset = theme.read(source / "themes/nord.toml")
            preset["roles"]["file.directory"] = "@status.attention"
            preset["roles"]["git.file.modified"] = "@accent.secondary"
            write_definition(source / "themes/nord.toml", preset)
            subprocess.run(["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)], check=True)
            configuration = home / ".config/eza"
            configuration.mkdir(parents=True)
            (configuration / "theme.yml").symlink_to(output / "eza.yml")
            repository = work / "project with ' quote"
            repository.mkdir()
            folder = repository / "source files"
            folder.mkdir()
            modified, staged = folder / "modified.txt", folder / "staged.txt"
            modified.write_text("before\n")
            staged.write_text("before\n")
            def git(*args):
                subprocess.run(["git", "-C", str(repository), *args], check=True, capture_output=True)
            git("init", "-q")
            git("add", ".")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Initial files")
            modified.write_text("after\n")
            staged.write_text("after\n")
            git("add", ".")
            modified.write_text("unstaged\n")
            untracked = folder / "bytes.bin"
            untracked.write_bytes(b"x" * 12288)
            environment = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "EZA_CONFIG_DIR": str(configuration), "LS_COLORS": "di=31", "EZA_COLORS": "di=31", "TERM": "xterm-256color"}
            environment.pop("NO_COLOR", None)
            command = ["bash", "-c", """shopt -s expand_aliases; source "$1/sh/alias"; eval 'll --color=always --icons=never "$2"'""", "fixture", str(ROOT), str(untracked)]
            listing = subprocess.check_output(command, text=True, env=environment)
            plain = re.sub(r"\x1b\[[0-9;]*m", "", listing)
            self.assertRegex(plain, r"12,?288")
            preview = subprocess.check_output([str(ROOT / "bin/fzf-path-preview"), str(repository)], text=True, env=environment)
            plain = re.sub(r"\x1b\[[0-9;]*m", "", preview)
            self.assertIn("MM", plain)
            self.assertIn("M-", plain)
            self.assertIn("-N", plain)
            self.assertIn("38;2;208;135;112m", preview)
            self.assertIn("38;2;143;188;187m", preview)
            # WHY: The native letters and index/worktree columns are eza-owned, not glyph tokens.
            self.assertIn("modified.txt", plain)

    def test_fzf_wrapper_keeps_arguments_and_native_exit_status(self):
        with tempfile.TemporaryDirectory(prefix="theme-fzf-") as directory:
            work = Path(directory)
            proxy = work / "fzf"
            proxy.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\nexit 130\n')
            proxy.chmod(0o755)
            result = subprocess.run([str(ROOT / "bin/dotfiles-fzf"), "--header=A name", "--no-multi"], env={**os.environ, "PATH": str(work) + os.pathsep + os.environ["PATH"], "DOTFILES_THEME_DIR": str(theme.SOURCE / "generated")}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 130)
            self.assertEqual(result.stdout.splitlines()[-2:], ["--header=A name", "--no-multi"])
            self.assertTrue(result.stdout.startswith("--color=dark,"))

    def test_native_review_uses_observed_cell_geometry(self):
        from theme_review import render_svg
        theme_data = json.loads(theme.compile_theme(theme.SOURCE, "sage")["colors.json"])
        def cell(data, **styles):
            return {"data": data, "fg": "default", "bg": "default",
                    "bold": False, "italics": False, "reverse": False,
                    "underscore": False, **styles}
        rows = [
            [cell("A\u0301"), cell("界"), cell(""), cell("\ue0b0", fg="acc8b7", bg="c4b2d9"),
             cell("─"), cell(" ", bg="26352d"), cell(" ")],
            [cell(" ") for _ in range(7)],
        ]
        svg = render_svg("geometry", rows, theme_data)
        root = ET.fromstring(svg)
        ns = {"s": "http://www.w3.org/2000/svg"}
        self.assertEqual(root.get("width"), str(6 * 9 + 24))
        self.assertEqual(root.get("height"), str(20 + 24))
        self.assertNotIn("textLength", svg)
        self.assertNotIn("\ue0b0", svg)
        labels = {node.text: node for node in root.findall(".//s:text", ns)}
        self.assertEqual(labels["A\u0301"].get("x"), "16.5")
        self.assertEqual(labels["界"].get("x"), "30")
        self.assertIn('transform="translate(39 12)" fill="#ACC8B7"', svg)
        self.assertIn('width="9" height="20" fill="#26352D"', svg)
        full = ET.fromstring(render_svg("full", rows, theme_data, trim=False))
        self.assertEqual(full.get("width"), str(7 * 9 + 24))
        self.assertEqual(full.get("height"), str(2 * 20 + 24))

    def test_terminal_color_queries_across_split_reads(self):
        from theme_review import TerminalColorQueries
        query = TerminalColorQueries({"roles": {"text": "#D7DFD9", "surface": "#0D1513"}})
        self.assertEqual(query.feed(b"hello\x1b]1"), [])
        self.assertEqual(query.feed(b"1;?\x1b"), [])
        self.assertEqual(query.feed(b"\\"), [b"\x1b]11;rgb:0d0d/1515/1313\x1b\\"])
        self.assertEqual(query.feed(b"\x1b]10;?\x07"), [b"\x1b]10;rgb:d7d7/dfdf/d9d9\x07"])
        self.assertEqual(query.feed(b"\x1b]11;?\x07\x1b["), [b"\x1b]11;rgb:0d0d/1515/1313\x07"])
        self.assertEqual(query.feed(b"5"), [])
        self.assertEqual(query.feed(b"n"), [b"\x1b[0n"])
        self.assertEqual(query.feed(b"\x1b[5n\x1b]11;?\x07"), [b"\x1b[0n", b"\x1b]11;rgb:0d0d/1515/1313\x07"])
        self.assertEqual(query.feed(b"ordinary text"), [])

    def test_review_metadata_filter_preserves_hyperlink_labels(self):
        from theme_review import TerminalMetadata
        stream = TerminalMetadata()
        parts = [
            "before \x1b]8;;file:///tmp/service",
            ".lua\x1b",
            "\\service.lua\x1b]8;;\x07 after",
            "\x1bPignored",
            "\x1b\\\x1b[31mred\x1b[0m",
        ]
        self.assertEqual("".join(stream.feed(part) for part in parts),
                         "before service.lua after\x1b[31mred\x1b[0m")
        self.assertEqual(stream.pending, "")

    def test_sage_retains_explicit_delta_markers(self):
        sage = theme.compile_theme(theme.SOURCE, "sage")
        nord = theme.compile_theme(theme.SOURCE, "nord")
        self.assertIn("keep-plus-minus-markers = true", sage["delta.gitconfig"])
        self.assertNotIn("keep-plus-minus-markers", nord["delta.gitconfig"])
        with tempfile.TemporaryDirectory() as directory:
            for name in ("colors.json", "tokens.json"):
                (Path(directory) / name).write_text(sage[name])
            env = {**os.environ, "DOTFILES_THEME_DIR": directory}
            command = [str(ROOT / "bin/dotfiles-theme"), "--catalog"]
            plain = subprocess.check_output([*command, "--color=never"], env=env, text=True)
            self.assertNotIn("\x1b", plain)
            self.assertIn("◐ CONNECTING", plain)
            self.assertIn("✓ APPROVED", plain)
            colored = subprocess.check_output([*command, "--color=always"], env=env, text=True)
            self.assertIn("\x1b[38;2;172;200;183m✓ APPROVED", colored)

    def test_cli_preserves_meaning_without_color(self):
        command = [str(ROOT / "bin/dotfiles-theme")]
        plain = subprocess.check_output(command, text=True, env={**os.environ, "NO_COLOR": "1"})
        self.assertNotIn("\x1b", plain)
        self.assertIn("ERROR    Failed", plain)
        self.assertIn("UNKNOWN  No observation", plain)
        colored = subprocess.check_output([*command, "--color=always"], text=True)
        self.assertIn("\x1b[38;2;191;97;106mERROR", colored)


if __name__ == "__main__":
    unittest.main()
