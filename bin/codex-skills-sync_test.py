"""One detector for making shared dotfiles skills discoverable by Codex."""

from pathlib import Path
import re
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
    source = repo / "ai/skills/shared-workflow"
    source.mkdir(parents=True)
    (source / "SKILL.md").symlink_to(instruction)
    (source / "references").symlink_to(external / "references")
    architecture = repo / "ai/skills/pragmatic-hexagonal"
    shutil.copytree(ROOT / "ai/skills/pragmatic-hexagonal", architecture)
    (repo / "scripts").mkdir()
    (repo / "scripts/install-software-standard.py").symlink_to(ROOT / "scripts/install-software-standard.py")
    (repo / "bin").mkdir()
    (repo / "bin/sync-codex-skills").symlink_to(ROOT / "bin/sync-codex-skills")
    local = home / ".agents/skills/local-workflow/SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("Local instructions.\n")
    # Shared data may live on another volume; repeat installation must still
    # recognize its own links after resolving the .local parent.
    data = tmp_path / "user-data"
    data.mkdir()
    (home / ".local").symlink_to(data, target_is_directory=True)
    cache = home / ".codex/dotfiles-skills"
    cache.mkdir(parents=True)
    global_file = home / ".codex/AGENTS.md"
    global_file.write_text("Keep my existing global preferences.\n")
    local_rule = home / ".claude/rules/local.md"
    local_rule.parent.mkdir(parents=True)
    local_rule.write_text("Keep my local rule.\n")
    (cache / "shared-workflow").symlink_to(repo / "claude/skills/shared-workflow")
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
    architecture_installed = home / ".agents/skills/dotfiles/pragmatic-hexagonal"
    assert (architecture_installed / "references/standard.md").read_bytes() == (architecture / "references/standard.md").read_bytes()
    assert (architecture_installed / "scripts/operations.py").read_bytes() == (architecture / "scripts/operations.py").read_bytes()
    assert local.read_text() == "Local instructions.\n"
    package = (home / ".local/share/software-standards/pragmatic-hexagonal").resolve()
    assert architecture_installed.resolve() == package
    assert (home / ".claude/skills/pragmatic-hexagonal").resolve() == package
    assert (home / ".claude/rules/pragmatic-hexagonal.md").read_bytes() == (package / "references/instructions.md").read_bytes()
    assert global_file.read_text().endswith("Keep my existing global preferences.\n")
    assert local_rule.read_text() == "Keep my local rule.\n"
    guidance = global_file.read_text()

    instruction.write_text(instruction.read_text() + "Use the latest guide.\n")
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert (installed / "SKILL.md").read_text() == instruction.read_text()
    assert local.read_text() == "Local instructions.\n"

    # A copied skill package must not depend on the dotfiles checkout layout.
    portable = tmp_path / "portable"
    shutil.copytree(architecture_installed, portable)
    assert global_file.read_text() == guidance, "repeat install changed global instructions"
    shutil.rmtree(repo)
    assert (architecture_installed / "references/standard.md").is_file()
    assert (home / ".claude/skills/pragmatic-hexagonal/references/standard.md").is_file()
    for document in (portable / "SKILL.md", portable / "references/standard.md"):
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if "://" not in target and not target.startswith("#"):
                assert (document.parent / target.split("#")[0]).is_file(), target
