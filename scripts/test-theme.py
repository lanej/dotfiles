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
        self.assertEqual(colors["git.file.modified"], "#EBCB8B")
        self.assertEqual(colors["git.file.stashed"], "#E5E9F0")

    def test_invalid_definitions(self):
        base = theme.read(theme.SOURCE / "themes/nord.json")
        for changes in ({"accent": {"ansi": 16}}, {"accent": {"ansi": True}}, {"accent": "@missing"}, {"accent": "@accent"}, {"accent": "#123456"}, {"accent": {"mix": ["@surface", "@text"], "amount": 2}}):
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

    def test_ansi_cycles_preserve_outputs(self):
        with tempfile.TemporaryDirectory(prefix="theme-ansi-") as directory:
            source, output = Path(directory) / "source", Path(directory) / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            command = ["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)]
            subprocess.run(command, check=True)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            original = theme.read(source / "themes/nord.json")
            for slots in ({3: {"ansi": 3}}, {3: {"ansi": 4}, 4: {"ansi": 3}}, {3: "@git.file.modified"}):
                data = copy.deepcopy(original)
                for slot, definition in slots.items():
                    data["ansi"][slot] = definition
                (source / "themes/nord.json").write_text(json.dumps(data))
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

    def test_ascii_representation_and_validation_preserve_outputs(self):
        with tempfile.TemporaryDirectory(prefix="theme-ascii-") as directory:
            source, output = Path(directory) / "source", Path(directory) / "output"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            command = ["python3", str(ROOT / "scripts/theme.py"), "--source", str(source), "--output-dir", str(output)]
            (source / "config.json").write_text(json.dumps({"theme": "nord", "symbols": "ascii"}))
            subprocess.run(command, check=True)
            catalog = theme.read(output / "tokens.json")
            self.assertEqual(catalog["symbols"], "ascii")
            self.assertEqual(catalog["git_states"]["git.file.modified"]["symbol"], "~")
            self.assertEqual(catalog["git_states"]["git.file.staged"]["symbol"], "")
            self.assertTrue(all(token["resolved"].isascii() and len(token["resolved"]) <= 1 for name, token in catalog["presentation"].items() if name.startswith("symbol.")))
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            shared = theme.read(source / "tokens.json")
            for invalid in (None, "wide", "é", "\n"):
                shared["presentation"]["symbol.git.file.modified"]["ascii"] = invalid
                (source / "tokens.json").write_text(json.dumps(shared))
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ASCII fallback", result.stderr)
                self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

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
            self.assertEqual((home / ".config/eza/theme.yml").resolve(), theme.SOURCE / "generated/eza.yml")
            self.assertTrue((home / ".config/bat/themes/Dotfiles.tmTheme").is_file())
            self.assertEqual((home / ".config/glow/theme.json").resolve(), theme.SOURCE / "generated/glow.json")

    @unittest.skipUnless(shutil.which("eza"), "native eza is not installed")
    def test_eza_roles_and_git_states_through_native_consumers(self):
        with tempfile.TemporaryDirectory(prefix="theme-eza-") as directory:
            work = Path(directory)
            source, output, home = work / "source", work / "output", work / "home"
            shutil.copytree(theme.SOURCE, source, ignore=shutil.ignore_patterns("generated", "baselines"))
            preset = theme.read(source / "themes/nord.json")
            preset["roles"]["file.directory"] = "@status.attention"
            preset["roles"]["git.file.modified"] = "@accent.secondary"
            (source / "themes/nord.json").write_text(json.dumps(preset))
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
