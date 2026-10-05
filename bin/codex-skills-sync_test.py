"""One detector for making shared dotfiles skills discoverable by Codex."""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def test_make_codex_skills_exposes_linked_entrypoint_and_preserves_local_skills(tmp_path):
    repo = tmp_path / "dotfiles"
    home = tmp_path / "user"
    external = tmp_path / "external"
    external.mkdir()
    instruction = external / "workflow.md"
    instruction.write_text("---\nname: shared-workflow\ndescription: Use when reviewing shared work.\n---\nReview the work.\n")
    (external / "references").mkdir()
    (external / "references/guide.md").write_text("Review guide.\n")
    source = repo / "claude/skills/shared-workflow"
    source.mkdir(parents=True)
    (source / "SKILL.md").symlink_to(instruction)
    (source / "references").symlink_to(external / "references")
    (repo / "bin").mkdir()
    (repo / "bin/sync-codex-skills").symlink_to(ROOT / "bin/sync-codex-skills")
    local = home / ".agents/skills/local-workflow/SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("Local instructions.\n")
    executables = tmp_path / "bin"
    executables.mkdir()
    (executables / "python3").symlink_to(sys.executable)
    command = [shutil.which("make"), "-f", str(ROOT / "Makefile"), "codex-skills",
               f"DOTFILES={repo}", f"HOME={home}"]
    env = {"PATH": f"{executables}:/usr/bin:/bin"}
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)

    installed = home / ".agents/skills/dotfiles/shared-workflow"
    assert (home / ".agents/skills/dotfiles").is_symlink()
    assert (installed / "SKILL.md").read_text() == instruction.read_text()
    assert not (installed / "SKILL.md").is_symlink()
    assert (installed / "references/guide.md").read_text() == "Review guide.\n"
    assert local.read_text() == "Local instructions.\n"

    instruction.write_text(instruction.read_text() + "Use the latest guide.\n")
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert (installed / "SKILL.md").read_text() == instruction.read_text()
    assert local.read_text() == "Local instructions.\n"
