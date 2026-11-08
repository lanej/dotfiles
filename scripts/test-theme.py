#!/usr/bin/env python3
"""Exercise theme compilation, invalid inputs and native configuration wiring."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("theme", ROOT / "scripts/theme.py")
theme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(theme)


class ThemeTests(unittest.TestCase):
    def test_canonical_palette_and_aliases(self):
        data = theme.read(theme.SOURCE / "themes/nord.json")
        colors, value = theme.resolve(data, theme.read(theme.SOURCE / "tokens.json")["roles"])
        self.assertEqual(colors["surface"], "#2E3440")
        self.assertEqual(colors["accent"], "#88C0D0")
        self.assertEqual(colors["diff.add"], "#A3BE8C")
        self.assertEqual(value("default"), "default")
        self.assertEqual(colors["diff.add.bg"], "#414A4C")

    def test_invalid_definitions(self):
        base = theme.read(theme.SOURCE / "themes/nord.json")
        for changes in ({"accent": "@missing"}, {"accent": "@accent"}, {"accent": "#123456"}, {"accent": {"mix": ["@surface", "@text"], "amount": 2}}):
            data = copy.deepcopy(base)
            data["roles"].update(changes)
            with self.subTest(changes=changes), self.assertRaises((KeyError, ValueError)):
                theme.resolve(data, theme.read(theme.SOURCE / "tokens.json")["roles"])

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
            data = theme.read(source / "themes/nord.json")
            data["roles"]["accent"] = "@missing"
            (source / "themes/nord.json").write_text(json.dumps(data))
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_selected_preset_has_no_downstream_naming_dependency(self):
        with tempfile.TemporaryDirectory(prefix="theme-preset-") as directory:
            work = Path(directory)
            source, output = work / "source", work / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            original = source / "themes/nord.json"
            data = json.loads(original.read_text().replace("$nord", "$swatch"))
            data["name"] = "forest"
            data["palette"] = {key.replace("nord", "swatch"): value for key, value in data["palette"].items()}
            data["palette"]["swatch8"] = "#74B87A"
            data["palette"]["swatch12"] = "#C3A568"
            (source / "themes/forest.json").write_text(json.dumps(data))
            original.unlink()
            (source / "config.json").write_text(json.dumps({"theme": "forest"}))
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

    def test_composition_rejects_missing_and_cyclic_references(self):
        with tempfile.TemporaryDirectory(prefix="theme-catalog-") as directory:
            source = Path(directory)
            for catalog in ([{"id": "a", "level": "atom", "composes": ["absent"]}], [{"id": "a", "level": "atom", "composes": ["a"]}]):
                (source / "catalog.json").write_text(json.dumps(catalog))
                with self.assertRaises((KeyError, ValueError)):
                    theme.validate_catalog(source)

    def test_presentation_validation_and_failure_preserve_outputs(self):
        with tempfile.TemporaryDirectory(prefix="theme-tokens-") as directory:
            work = Path(directory)
            source, output = work / "source", work / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            command = ["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)]
            subprocess.run(command, check=True)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            preset = theme.read(source / "themes/nord.json")
            for override in ({"symbol.separator.section.left": "%Y"}, {"missing": True}, {"emphasis.heading": 1}, {"space.inline": True}, {"space.inline": -1}, {"symbol.git.file.modified": "bad\nline"}, {"emphasis.heading": {"token": "space.inline"}}, {"emphasis.heading": {"token": "emphasis.heading"}}, {"emphasis.heading": {"token": "missing"}}):
                with self.subTest(override=override):
                    (source / "themes/nord.json").write_text(json.dumps({**preset, "presentation": override}))
                    self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
                    self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
            (source / "themes/nord.json").write_text(json.dumps(preset))
            shared = theme.read(source / "tokens.json")
            shared["presentation"]["space.inline"]["unit"] = "row"
            (source / "tokens.json").write_text(json.dumps(shared))
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
            self.assertTrue((home / ".config/bat/themes/Dotfiles.tmTheme").is_file())
            self.assertEqual((home / ".config/glow/theme.json").resolve(), theme.SOURCE / "generated/glow.json")

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
