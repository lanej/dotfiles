#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Protect generation, conflict reporting and bounded native-source inventory."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("keybindings.py")
BEGIN = "# BEGIN generated keybindings (scripts/keybindings.py)"
END = "# END generated keybindings"
REGISTRY = '''version = 1
[[binding]]
id = "kitty.links"
app = "kitty"
chord = "cmd+shift+u"
action = "kitten hints --type hyperlink"
description = "Select a labeled link."
'''


class KeybindingsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("config", "kitty", "yabai"):
            (self.root / directory).mkdir()
        self.write("config/keybindings.toml", REGISTRY)
        self.kitty = f"# user settings\nfont_size 13\n{BEGIN}\n{END}\nmap cmd+n new_tab\n"
        self.write("kitty/kittyconf", self.kitty)
        self.write("yabai/skhdrc", "# navigation\nalt - h : focus west;\\\n  echo done\n")

    def write(self, path, text):
        (self.root / path).write_text(text)

    def run_cli(self, *args, status=0):
        result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def test_generate_preserves_unmanaged_content_and_detects_drift(self):
        self.run_cli("generate", "--check", status=1)
        self.run_cli("generate")
        generated = (self.root / "kitty/kittyconf").read_text()
        self.assertTrue(generated.startswith("# user settings\nfont_size 13\n" + BEGIN))
        self.assertTrue(generated.endswith(END + "\nmap cmd+n new_tab\n"))
        self.assertIn("map shift+super+u kitten hints --type hyperlink\n", generated)
        self.assertEqual((self.root / "yabai/skhdrc").read_text(), "# navigation\nalt - h : focus west;\\\n  echo done\n")
        self.run_cli("generate", "--check")
        self.assertEqual(self.run_cli("generate").stdout, "")
        report = json.loads(self.run_cli("check", "--json").stdout)
        self.assertEqual(report["conflicts"], [])
        self.assertEqual(len(report["bindings"]), 3)
        self.assertEqual(report["bindings"][-1]["action"], "focus west; echo done")
        self.write("kitty/kittyconf", generated.replace("hints --type hyperlink", "hints --type url"))
        self.run_cli("check", status=1)
        self.run_cli("generate", "--check", status=1)

    def test_global_overlap_normalizes_aliases_and_preserves_provenance(self):
        self.write("yabai/skhdrc", "shift + command - u : move east\n")
        report = json.loads(self.run_cli("check", "--json", status=1).stdout)
        conflict, = report["conflicts"]
        self.assertEqual(conflict["chord"], "shift+cmd+u")
        self.assertEqual(conflict["kind"], "global-overlap")
        self.assertEqual([(b["source"], b["line"]) for b in conflict["bindings"]],
                         [("config/keybindings.toml", 2), ("yabai/skhdrc", 1)])
        before = (self.root / "kitty/kittyconf").read_text()
        self.run_cli("generate", status=2)
        self.assertEqual((self.root / "kitty/kittyconf").read_text(), before)
        query = json.loads(self.run_cli("list", "--chord", "super+shift+u", "--json").stdout)
        self.assertEqual(len(query["bindings"]), 2)
        self.assertIn("macOS system shortcuts", query["coverage"]["excluded"])

    def test_same_application_duplicate_and_native_generation_for_skhd(self):
        self.write("config/keybindings.toml", REGISTRY + '''
[[binding]]
id = "desktop.focus"
app = "skhd"
chord = "alt+h"
action = "focus west"
description = "Focus west."
''')
        self.write("yabai/skhdrc", f"{BEGIN}\n{END}\n")
        self.run_cli("generate")
        self.assertIn("alt - h : focus west\n", (self.root / "yabai/skhdrc").read_text())
        self.write("kitty/kittyconf", (self.root / "kitty/kittyconf").read_text() + "map super+shift+u something_else\n")
        report = json.loads(self.run_cli("check", "--json", status=1).stdout)
        self.assertEqual(report["conflicts"][0]["kind"], "duplicate")

    def test_unsupported_native_syntax_is_an_error_with_location(self):
        for path, entry in [("kitty/kittyconf", "map --mode resize ctrl+a noop"),
                            ("kitty/kittyconf", "map ctrl+x>ctrl+y noop"),
                            ("yabai/skhdrc", "resize < alt - h : focus west"),
                            ("yabai/skhdrc", 'alt - h [ "kitty" : focus west ]')]:
            with self.subTest(entry=entry):
                self.write("kitty/kittyconf", self.kitty)
                self.write("yabai/skhdrc", "")
                self.write(path, (self.root / path).read_text() + entry + "\n")
                result = self.run_cli("check", status=2)
                self.assertIn(path + ":", result.stderr)

    def test_key_aliases_overlap_and_serialize_to_native_names(self):
        self.write("kitty/kittyconf", self.kitty + "map cmd+page_up previous_tab\n")
        self.write("yabai/skhdrc", "cmd - pageup : echo next\n")
        report = json.loads(self.run_cli("check", "--json", status=1).stdout)
        self.assertEqual([entry["chord"] for entry in report["conflicts"]], ["cmd+page_up"])
        self.write("kitty/kittyconf", self.kitty)
        self.write("yabai/skhdrc", f"{BEGIN}\n{END}\n")
        for key, native in [("return", "return"), ("page_up", "pageup"), ("pgdn", "pagedown")]:
            with self.subTest(key=key):
                self.write("config/keybindings.toml", REGISTRY.replace('app = "kitty"', 'app = "skhd"')
                           .replace('chord = "cmd+shift+u"', f'chord = "cmd+{key}"'))
                self.run_cli("generate")
                self.assertIn(f"cmd - {native} : kitten hints --type hyperlink\n",
                              (self.root / "yabai/skhdrc").read_text())
                self.run_cli("check")
        self.write("kitty/kittyconf", self.kitty + "map cmd+unknown_key noop\n")
        self.assertIn("unsupported key", self.run_cli("check", status=2).stderr)

    def test_invalid_registry_and_broken_markers_do_not_write(self):
        for invalid in [REGISTRY.replace('app = "kitty"', 'app = "tmux"'),
                        REGISTRY.replace('chord = "cmd+shift+u"', 'chord = "cmd+hyper+u"'),
                        REGISTRY + REGISTRY.removeprefix("version = 1\n")]:
            self.write("config/keybindings.toml", invalid)
            self.run_cli("generate", status=2)
            self.assertEqual((self.root / "kitty/kittyconf").read_text(), self.kitty)
        self.write("config/keybindings.toml", REGISTRY)
        self.write("kitty/kittyconf", self.kitty.replace(END, ""))
        self.assertIn("markers", self.run_cli("generate", status=2).stderr)


if __name__ == "__main__":
    unittest.main()
