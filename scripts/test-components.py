#!/usr/bin/env python3
"""Exercise ownership, historical selection, and the real installation entrypoint."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import components
import component_sandbox


REPO = Path(__file__).resolve().parents[1]


class ComponentContract(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="component-contract-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "checkout with spaces"
        self.root.mkdir()
        (self.root / "config").mkdir()
        (self.root / "scripts/make").mkdir(parents=True)
        shutil.copy2(REPO / "scripts/make/components-install.sh", self.root / "scripts/make/components-install.sh")
        self.write_component("cleanup")
        self.write_component("launchers", ["cleanup"])
        self.git("init", "-q", "-b", "main")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), "-c", "user.name=Component test",
                                        "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
                                        *args], text=True).strip()

    def write_component(self, name, dependencies=()):
        base = self.root / "components" / name
        (base / "bin").mkdir(parents=True, exist_ok=True)
        (base / "bin" / name).write_text("#!/bin/sh\nprintf 'installed %s\\n' " + name + "\n")
        (base / "bin" / name).chmod(0o755)
        (base / "component.toml").write_text(
            f'version = 1\ndependencies = {json.dumps(list(dependencies))}\nlegacy_inputs = []\n'
            f'platforms = ["linux", "darwin"]\ntools = ["sh"]\n[install]\n"bin/{name}" = ".local/bin/{name}"\n'
            '[suites]\nacceptance = ["sh", "-c", "exit 0"]\n')

    def graph(self):
        return components.load(components.Tree(self.root))

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def test_selection_has_independent_expected_consumers(self):
        graph = self.graph()
        examples = [
            ("components/cleanup/bin/new-command", {"cleanup", "launchers"}),
            ("components/launchers/tests/new-test.py", {"launchers"}),
            ("bin/cleanup", {"cleanup", "launchers"}),
            ("bin/launchers", {"launchers"}),
            ("legacy/unclassified", {"cleanup", "launchers"}),
            ("scripts/components.py", {"cleanup", "launchers"}),
        ]
        for changed, expected in examples:
            with self.subTest(path=changed):
                selected = components.select([graph, graph], [changed])
                self.assertEqual(set(selected), expected)
                self.assertTrue(all(changed in reasons for reasons in selected.values()))
        self.assertEqual(components.select([graph, graph], []), {})

    def test_history_preserves_removed_edges_deletions_and_renames(self):
        base = self.commit()
        self.write_component("launchers", [])
        (self.root / "components/cleanup/bin/cleanup").rename(self.root / "components/cleanup/bin/renamed")
        manifest = self.root / "components/cleanup/component.toml"
        manifest.write_text(manifest.read_text().replace('"bin/cleanup"', '"bin/renamed"'))
        head = self.commit()
        result = components.plan(self.root, base, head)
        self.assertEqual(set(result["selected"]), {"cleanup", "launchers"})
        self.assertIn("components/cleanup/bin/cleanup", result["selected"]["launchers"])
        self.assertEqual(len(result["matrix"]["include"]), 4)
        self.assertEqual(result["head"], head)

    def test_installation_works_without_python_and_converges(self):
        graph = self.graph()
        graph["launchers"]["install"]["bin/launchers"] = ".launcher"
        (self.root / components.TABLE).write_text(components.install_table(graph))
        home = Path(self.temporary.name) / "home with spaces"
        home.mkdir()
        (home / "keep").write_text("user data")
        tools = Path(self.temporary.name) / "tools"
        tools.mkdir()
        for name in ("mkdir", "ln"):
            (tools / name).symlink_to(shutil.which(name))
        command = ["/bin/bash", str(self.root / "scripts/make/components-install.sh"), str(self.root), str(home)]
        for _ in range(2):
            subprocess.run(command, env={"PATH": str(tools)}, check=True)
        result = subprocess.check_output([str(home / ".local/bin/cleanup")], text=True)
        self.assertEqual(result, "installed cleanup\n")
        self.assertEqual((home / "keep").read_text(), "user data")
        (self.root / "components/launchers/bin/launchers").unlink()
        (home / ".local/bin/cleanup").unlink()
        failed = subprocess.run(command, env={"PATH": str(tools)}, capture_output=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse((home / ".local/bin/cleanup").exists())

    def test_undeclared_dependency_link_is_rejected(self):
        link = self.root / "components/launchers/bin/cleanup"
        link.symlink_to("../../cleanup/bin/cleanup")
        self.graph()
        self.write_component("launchers", [])
        with self.assertRaisesRegex(ValueError, "undeclared input symlink"):
            self.graph()

    def test_invalid_contracts_fail_before_execution(self):
        manifest = self.root / "components/launchers/component.toml"
        original = manifest.read_text()
        cases = [
            (original + 'unknown = "field"\n', "argument arrays"),
            (original.replace('["cleanup"]', '["missing"]'), "unknown dependency"),
            (original.replace('.local/bin/launchers', '.local/bin/cleanup'), "duplicate installation"),
            (original.replace('.local/bin/launchers', '../outside'), "unsafe relative path"),
            (original.replace('version = 1', 'version = true'), "version 1"),
        ]
        for content, message in cases:
            with self.subTest(message=message):
                manifest.write_text(content)
                with self.assertRaisesRegex(ValueError, message):
                    self.graph()
        manifest.write_text(original)
        self.write_component("cleanup", ["launchers"])
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            self.graph()

    def test_projection_installs_only_declared_inputs(self):
        (self.root / "undeclared").write_text("must not appear")
        graph = self.graph()
        stage = Path(self.temporary.name) / "projection/source"
        stage.mkdir(parents=True)
        home = components.project(components.Tree(self.root), graph, "launchers", stage)
        self.assertFalse((stage / "undeclared").exists())
        for name in ("cleanup", "launchers"):
            self.assertEqual(subprocess.check_output([str(home / ".local/bin" / name)], text=True), f"installed {name}\n")

    def test_missing_native_isolation_is_an_error_on_both_platforms(self):
        for platform in ("linux", "darwin"):
            with self.subTest(platform=platform), patch.object(component_sandbox.sys, "platform", platform), patch.object(component_sandbox.shutil, "which", return_value=None):
                with self.assertRaisesRegex(ValueError, "required"):
                    component_sandbox.sandbox_command([], [], self.root, {})


if __name__ == "__main__":
    unittest.main()
