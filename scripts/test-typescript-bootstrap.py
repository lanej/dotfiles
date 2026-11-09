#!/usr/bin/env python3
"""Exercise TypeScript adoption through the real repository installer, offline."""
import json
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
        return command(self.root, "python3", str(SOURCE / "bin/repo-bootstrap"), "--repo", str(self.root),
                       "--skills", "typescript", "--no-go", "--agents", "codex", "--pr-template", "none",
                       "--typescript", *args, ok=ok)

    def test_adoption_preserves_source_and_project_policy(self):
        names = ["package.json", "tsconfig.json", "eslint.config.mjs", "src/main.ts"]
        before = {name: (self.root / name).read_bytes() for name in names}
        self.install("--dry-run")
        self.assertFalse((self.root / ".agents").exists())
        self.install()
        settings = json.loads((self.root / ".typescript-quality.json").read_text())
        self.assertEqual(settings["rollout"], "ratchet")
        self.assertIn(["npm", "run", "lint"], settings["commands"]["legacy"])
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in names})
        self.assertFalse((self.root / ".typescript-quality/node_modules").exists())
        self.assertIn("already current", self.install().stdout)
        self.install("--typescript-rollout", "strict")
        self.assertEqual(json.loads((self.root / ".typescript-quality.json").read_text())["rollout"], "strict")

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
