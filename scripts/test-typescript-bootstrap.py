#!/usr/bin/env python3
"""Exercise TypeScript adoption through the real repository installer, offline."""
import json
import os
import re
import shlex
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]


def command(root, *argv, ok=True):
    result = subprocess.run(argv, cwd=root, text=True, capture_output=True)
    if ok and result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    if not ok and not result.returncode:
        raise AssertionError("command unexpectedly passed: " + " ".join(argv))
    return result


class TypeScriptBootstrap(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        command(self.root, "git", "init", "-q")
        (self.root / "package.json").write_text('{"scripts":{"test":"node --test","lint":"echo project lint"}}\n')
        (self.root / "tsconfig.json").write_text('// preserve comments\n{"compilerOptions":{"strict":false},"include":["src"]}\n')
        (self.root / "eslint.config.mjs").write_text('export default [];\n')
        (self.root / "src").mkdir()
        (self.root / "src/main.ts").write_text('export const value = 1;\n')
        command(self.root, "git", "add", ".")
        command(self.root, "git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "initial")

    def install(self, *args, ok=True):
        return command(self.root, "python3", str(SOURCE / "bin/source-code"), "setup", "--repo", str(self.root),
                       "--authority", "owned", "--adoption", "new",
                       "--skills", "typescript", "--no-go", "--agents", "codex", "--pr-template", "none",
                       "--typescript", *args, ok=ok)

    def test_adoption_preserves_source_and_project_policy(self):
        names = ["package.json", "tsconfig.json", "eslint.config.mjs", "src/main.ts"]
        before = {name: (self.root / name).read_bytes() for name in names}
        self.install("--dry-run")
        self.assertFalse((self.root / ".agents").exists())
        self.install()
        self.assertTrue((self.root / ".agents/skills/library-code-comments/SKILL.md").is_file())
        self.assertTrue((self.root / ".agents/skills/code-comments/references/standard.md").is_file())
        settings = json.loads((self.root / ".typescript-quality.json").read_text())
        self.assertEqual(settings["rollout"], "ratchet")
        self.assertIn(["npm", "run", "lint"], settings["commands"]["legacy"])
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in names})
        self.assertFalse((self.root / ".typescript-quality/node_modules").exists())
        self.assertIn("already current", self.install().stdout)
        self.install("--typescript-rollout", "strict")
        self.assertTrue((self.root / ".agents/skills/library-code-comments/SKILL.md").is_file())
        self.assertEqual(json.loads((self.root / ".typescript-quality.json").read_text())["rollout"], "strict")

    def test_bun_adoption_installs_the_declared_runtime_and_preserves_application_lock(self):
        package = {"packageManager": "bun@1.4.4", "scripts": {"test": "bun test", "lint": "echo project lint"}}
        (self.root / "package.json").write_text(json.dumps(package))
        lock = self.root / "bun.lock"
        lock.write_text("fixture application lock\n")
        before = lock.read_bytes()
        self.install()
        settings = json.loads((self.root / ".typescript-quality.json").read_text())
        self.assertEqual(settings["commands"]["test"], ["bun", "run", "test"])
        self.assertEqual(settings["commands"]["audit"], ["bun", "audit"])
        workflow = (self.root / ".github/workflows/typescript-quality.yml").read_text()
        steps = re.findall(r"^      - run: (.+)$", workflow, re.MULTILINE)
        install = next(shlex.split(step) for step in steps if shlex.split(step)[0] == "bun")
        binary = self.root / "bin"
        binary.mkdir()
        (binary / "bun").write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
        (binary / "bun").chmod(0o755)
        result = subprocess.run(install, cwd=self.root, env={**os.environ, "PATH": str(binary)}, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.splitlines(), ["install", "--frozen-lockfile", "--ignore-scripts"])
        self.assertEqual(lock.read_bytes(), before)
        self.assertFalse((self.root / "package-lock.json").exists())
        self.assertIn("already current", self.install().stdout)

    def test_go_profile_provisions_bun_for_mixed_runtime_tests(self):
        package = {"packageManager": "bun@1.4.4", "scripts": {"test": "bun test", "lint": "echo project lint"}}
        (self.root / "package.json").write_text(json.dumps(package))
        (self.root / "go.mod").write_text("module example.invalid/mixed\n\ngo 1.26.0\n")
        self.install("--go", "--go-rollout", "strict")
        workflow = (self.root / ".github/workflows/go-quality.yml").read_text()
        steps = re.findall(r"^      - run: (.+)$", workflow, re.MULTILINE)
        install = next(shlex.split(step) for step in steps if shlex.split(step)[0] == "bun")
        self.assertEqual(install, ["bun", "install", "--frozen-lockfile", "--ignore-scripts"])
        self.assertIn("already current", self.install("--go").stdout)

    def test_bun_lockfiles_select_bun_for_setup_without_a_runtime_pin(self):
        manifest = self.root / "package.json"
        package = json.loads(manifest.read_text())
        package["engines"] = {"bun": ">=1.4.4"}
        manifest.write_text(json.dumps(package))
        lock = self.root / "bun.lockb"
        lock.write_bytes(b"legacy lock fixture")
        (self.root / "go.mod").write_text("module example.invalid/mixed\n\ngo 1.26.0\n")
        self.install("--go", "--go-rollout", "strict")
        settings = self.root / ".typescript-quality.json"
        before = settings.read_bytes()
        self.assertEqual(json.loads(before)["commands"]["legacy"], [["bun", "run", "lint"]])
        self.assertEqual(json.loads(before)["commands"]["test"], ["bun", "run", "test"])

        lock = lock.rename(self.root / "bun.lock")
        self.install("--go", "--go-rollout", "strict")
        for language in ("go", "typescript"):
            workflow = (self.root / f".github/workflows/{language}-quality.yml").read_text()
            self.assertIn("uses: oven-sh/setup-bun@v2\n", workflow)
            self.assertIn("run: bun install --frozen-lockfile --ignore-scripts\n", workflow)
            self.assertNotIn("bun-version:", workflow)
            self.assertNotIn("run: npm ci\n", workflow)
        self.assertEqual(settings.read_bytes(), before)
        self.assertEqual(lock.read_bytes(), b"legacy lock fixture")

    def test_declared_package_manager_resolves_conflicting_lockfiles(self):
        (self.root / "bun.lock").touch()
        (self.root / "package-lock.json").touch()
        self.assertIn("multiple package managers", self.install(ok=False).stderr)
        self.assertFalse((self.root / ".agents").exists())
        manifest = self.root / "package.json"
        package = json.loads(manifest.read_text())
        package["packageManager"] = "npm@11.0.0"
        manifest.write_text(json.dumps(package))
        self.install()
        settings = json.loads((self.root / ".typescript-quality.json").read_text())
        self.assertEqual(settings["commands"]["test"], ["npm", "run", "test"])
        workflow = (self.root / ".github/workflows/typescript-quality.yml").read_text()
        self.assertIn("run: npm ci\n", workflow)
        self.assertNotIn("setup-bun", workflow)

    def test_local_install_hides_generated_baseline_and_lock(self):
        self.install("--mode", "local")
        for name in (".typescript-quality-baseline.json", ".typescript-quality/package-lock.json"):
            command(self.root, "git", "check-ignore", name)
        self.assertFalse(command(self.root, "git", "status", "--porcelain").stdout)

    def test_unsafe_destination_fails_before_writes(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / ".typescript-quality").symlink_to(outside, target_is_directory=True)
            self.assertIn("linked parent", self.install(ok=False).stderr)
            self.assertFalse((self.root / ".agents").exists())
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_existing_lint_policy_requires_nonmutating_gate(self):
        (self.root / "package.json").write_text('{"scripts":{"lint":"eslint --fix ."}}')
        self.assertIn("mutating gate", self.install(ok=False).stderr)
        self.assertFalse((self.root / ".agents").exists())
        (self.root / "package.json").write_text('{}')
        self.assertIn("lint script", self.install(ok=False).stderr)


if __name__ == "__main__":
    unittest.main()
