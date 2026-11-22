"""Exercise coordinator guidance installation in isolated Git repositories."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GIT = shutil.which("git")
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
        for name in ("bash", "git", "dirname", "mkdir", "cp", "cmp"):
            (self.bin / name).symlink_to(shutil.which(name))
        self.octo = self.bin / "octo-manager"
        self.octo.write_text("#!/bin/sh\nexit 99\n")
        self.octo.chmod(0o755)
        self.dest = self.root / "notes"
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
            [str(ROOT / "init.sh"), str(self.dest)],
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
        self.assertIn(str(self.dest / "PR-WORKFLOW.md"), result.stdout)

    def test_fresh_setup_tracks_the_guides_and_is_repeatable(self):
        self.assert_ready(self.initialize())
        guides = {"README.md", "LESSONS.md", "INSTRUCTIONS.md", "PR-WORKFLOW.md"}
        self.assertEqual({p.name for p in self.dest.iterdir()}, guides | {".git"})
        self.assertEqual(set(self.git("ls-files").splitlines()), guides)
        before = self.git("rev-parse", "HEAD")
        self.assert_ready(self.initialize())
        self.assertEqual(self.git("rev-parse", "HEAD"), before)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_refresh_updates_workflow_and_preserves_notes_archives_and_staging(self):
        self.assert_ready(self.initialize())
        workflow = self.dest / "PR-WORKFLOW.md"
        workflow.write_text("old managed workflow\n")
        self.git("commit", "-qm", "earlier workflow", "--", workflow.name)

        # Stage a note independently of its working copy, as a partial commit would.
        instructions = self.dest / "INSTRUCTIONS.md"
        working_copy = instructions.read_bytes()
        instructions.write_text("staged operator instruction\n")
        self.git("add", "--", instructions.name)
        instructions.write_bytes(working_copy)
        (self.dest / "unrelated.md").write_text("staged separately\n")
        self.git("add", "--", "unrelated.md")
        retained = {
            "README.md": "operator introduction\n",
            "LESSONS.md": "local lessons\n",
            "STATE.md": "handwritten history\n",
            "initiatives/work.md": "operator’s initiative\n",
            "bin/commit-state": "customized old helper\n",
        }
        for name, content in retained.items():
            path = self.dest / name
            path.parent.mkdir(exist_ok=True)
            path.write_text(content)
        self.assert_ready(self.initialize())
        for name, content in retained.items():
            self.assertEqual((self.dest / name).read_text(), content, name)
        self.assertEqual(
            workflow.read_bytes(), (ROOT / "templates" / workflow.name).read_bytes()
        )
        self.assertEqual(
            self.git("diff", "--name-only", "HEAD^", "HEAD"), workflow.name
        )
        self.assertEqual(
            self.git("diff", "--cached", "--name-only").splitlines(),
            [instructions.name, "unrelated.md"],
        )
        self.assertEqual(
            self.git("show", ":INSTRUCTIONS.md"), "staged operator instruction"
        )
        self.assertEqual(instructions.read_bytes(), working_copy)
        before = self.git("rev-parse", "HEAD")
        self.assert_ready(self.initialize())
        self.assertEqual(self.git("rev-parse", "HEAD"), before)

    def test_staged_workflow_requires_the_operator_to_finish_the_edit(self):
        self.assert_ready(self.initialize())
        workflow = self.dest / "PR-WORKFLOW.md"
        workflow.write_text("staged version\n")
        self.git("add", "--", workflow.name)
        workflow.write_text("additional edit\n")
        result = self.initialize()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(workflow), result.stderr)
        self.assertEqual(self.git("show", ":PR-WORKFLOW.md"), "staged version")
        self.assertEqual(workflow.read_text(), "additional edit\n")

    def test_missing_octo_is_reported_before_writing(self):
        self.octo.unlink()
        result = self.initialize()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("octo-manager is required", result.stderr)
        self.assertFalse(self.dest.exists(), "unexpected partial notes installation")

    def test_retired_helpers_block_upgrade_without_deleting_work(self):
        self.assert_ready(self.initialize())
        (self.dest / "bin").mkdir()
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

    def test_failed_initial_commit_can_be_retried(self):
        shim = self.bin / "git"
        shim.unlink()
        shim.write_text(
            '#!/bin/sh\nfor arg do [ "$arg" != commit ] || exit 17; done\n'
            + f'exec "{GIT}" "$@"\n'
        )
        shim.chmod(0o755)
        failed = self.initialize()
        self.assertEqual(failed.returncode, 17, failed.stdout + failed.stderr)
        self.assertNotIn("guidance ready", failed.stdout)
        shim.unlink()
        shim.symlink_to(GIT)
        self.assert_ready(self.initialize())
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "1")
        self.assertEqual(self.git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
