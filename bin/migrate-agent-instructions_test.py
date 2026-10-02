"""Exercise the migration through its command-line entrypoint."""

from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("migrate-agent-instructions")


class MigrationTest(unittest.TestCase):
    def test_shared_guidance_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = "# CLAUDE.md\n\nRepository guidance.\n"
            memory = "<claude-mem-context>old notes</claude-mem-context>\n"
            (root / "CLAUDE.md").write_text(source)
            (root / "AGENTS.md").write_text(memory)
            (root / ".gitignore").write_text("AGENTS.md\n.claude/\n")

            def run(*args):
                return subprocess.run(
                    [str(SCRIPT), str(root), *args],
                    capture_output=True, text=True, check=True,
                )

            run("--dry-run")
            self.assertEqual((root / "AGENTS.md").read_text(), memory)
            self.assertFalse((root / "CLAUDE.md").is_symlink())
            run()
            self.assertEqual(
                (root / "AGENTS.md").read_text(),
                "# AGENTS.md\n\nRepository guidance.\n",
            )
            self.assertEqual((root / "CLAUDE.md").readlink(), Path("AGENTS.md"))
            self.assertEqual((root / "CLAUDE.md").read_text(), (root / "AGENTS.md").read_text())
            self.assertEqual((root / "AGENTS.md.pre-migration").read_text(), memory)
            self.assertEqual((root / ".gitignore").read_text(), ".claude/\n")
            run()
            self.assertFalse((root / "AGENTS.md.pre-migration.1").exists())


if __name__ == "__main__":
    unittest.main()
