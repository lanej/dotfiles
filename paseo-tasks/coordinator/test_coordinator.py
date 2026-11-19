"""Exercise memory initialization and upgrade boundaries against real local Git."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GIT = shutil.which("git")
BASH = shutil.which("bash")
POLICY = "Read PR-WORKFLOW.md before PR work. It governs the PR lifecycle when older local instructions disagree."
RETIRED = (
    "merge-seq.sh",
    "merge-seq.py",
    "resolve-golangci.py",
    "normalize-golangci.py",
)


class Coordinator(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coordinator-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "tools"
        self.bin.mkdir()
        # An isolated PATH makes missing-tool evidence independent of the host install.
        for name in (
            "git",
            "dirname",
            "mkdir",
            "cp",
            "chmod",
            "grep",
            "mktemp",
            "cat",
            "mv",
        ):
            (self.bin / name).symlink_to(shutil.which(name))
        self.octo = self.bin / "octo-manager"
        self.octo.write_text("#!/bin/sh\nexit 99\n")
        self.octo.chmod(0o755)
        self.dest = self.root / "memory"
        self.env = dict(
            os.environ,
            PATH=str(self.bin),
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Fixture",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_NAME="Fixture",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
            GIT_CONFIG_COUNT="2",
            GIT_CONFIG_KEY_0="core.hooksPath",
            GIT_CONFIG_VALUE_0=os.devnull,
            GIT_CONFIG_KEY_1="commit.gpgsign",
            GIT_CONFIG_VALUE_1="false",
        )

    def initialize(self):
        return subprocess.run(
            [BASH, str(ROOT / "init.sh"), str(self.dest)],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )

    def git(self, *args):
        return subprocess.run(
            [GIT, "-C", str(self.dest), *args],
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    def assert_ready(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("coordinator state ready:", result.stdout)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_fresh_install_persists_memory_and_only_state_helper(self):
        self.assert_ready(self.initialize())
        self.assertEqual(
            sorted(p.name for p in (self.dest / "bin").iterdir()), ["commit-state"]
        )
        self.assertEqual(
            (self.dest / "PR-WORKFLOW.md").read_text(),
            (ROOT / "templates/PR-WORKFLOW.md").read_text(),
        )
        self.assertIn(POLICY, (self.dest / "INSTRUCTIONS.md").read_text())
        before = self.git("rev-parse", "HEAD")
        self.assert_ready(self.initialize())
        self.assertEqual(self.git("rev-parse", "HEAD"), before)

    def test_upgrade_preserves_authored_state_and_refreshes_workflow(self):
        self.assert_ready(self.initialize())
        retained = {
            "STATE.md": "operator state and authorizations\n",
            "INSTRUCTIONS.md": "local standing instructions\n",
            "LESSONS.md": "local lessons\n",
            "initiatives/work.md": "valuable current work\n",
            "bin/custom-helper": "operator-owned script\n",
        }
        for name, content in retained.items():
            (self.dest / name).write_text(content)
        (self.dest / "PR-WORKFLOW.md").write_text("old managed workflow\n")
        self.assert_ready(self.initialize())
        for name, content in retained.items():
            expected = (
                POLICY + "\n\n" + content if name == "INSTRUCTIONS.md" else content
            )
            self.assertEqual((self.dest / name).read_text(), expected, name)
        self.assertEqual(
            (self.dest / "PR-WORKFLOW.md").read_text(),
            (ROOT / "templates/PR-WORKFLOW.md").read_text(),
        )
        self.assert_ready(self.initialize())
        self.assertEqual((self.dest / "INSTRUCTIONS.md").read_text().count(POLICY), 1)

    def test_missing_octo_is_reported_before_writing(self):
        self.octo.unlink()
        result = self.initialize()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("octo-manager is required", result.stderr)
        self.assertFalse(
            self.dest.exists(), "missing integration must not seed partial state"
        )

    def test_retired_helpers_block_upgrade_without_deleting_work(self):
        self.assert_ready(self.initialize())
        state = self.dest / "STATE.md"
        state.write_text("uncommitted operator work\n")
        before = self.git("rev-parse", "HEAD")
        for name in RETIRED:
            with self.subTest(helper=name):
                path = self.dest / "bin" / name
                path.write_text("potentially customized legacy helper\n")
                failed = self.initialize()
                self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
                self.assertIn(str(path), failed.stderr)
                self.assertNotIn("coordinator state ready:", failed.stdout)
                self.assertEqual(
                    path.read_text(), "potentially customized legacy helper\n"
                )
                self.assertEqual(state.read_text(), "uncommitted operator work\n")
                self.assertEqual(self.git("rev-parse", "HEAD"), before)
                path.unlink()
        path.symlink_to(self.root / "absent-target")
        failed = self.initialize()
        self.assertNotEqual(failed.returncode, 0, failed.stdout + failed.stderr)
        self.assertTrue(path.is_symlink(), "even dangling legacy links need inspection")

    def test_persistence_failure_propagates_and_preserves_state(self):
        self.assert_ready(self.initialize())
        (self.dest / "STATE.md").write_text("new state needing persistence\n")
        before = self.git("rev-parse", "HEAD")
        shim = self.bin / "git"
        shim.unlink()
        shim.write_text(
            '#!/bin/sh\nfor arg do [ "$arg" != commit ] || exit 17; done\n'
            + f'exec "{GIT}" "$@"\n'
        )
        shim.chmod(0o755)
        failed = self.initialize()
        self.assertEqual(failed.returncode, 17, failed.stdout + failed.stderr)
        self.assertNotIn("coordinator state ready:", failed.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual(
            (self.dest / "STATE.md").read_text(), "new state needing persistence\n"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
