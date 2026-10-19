"""One detector for exposing shared skills and migrating the Builder package."""

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
    builder = repo / "ai/skills/builder"
    shutil.copytree(ROOT / "ai/skills/builder", builder)
    construction = builder / "references/construction.md"
    construction_text = construction.read_text()
    (repo / "ai/agents").mkdir()
    (repo / "scripts").mkdir()
    (repo / "scripts/install-software-standard.py").symlink_to(ROOT / "scripts/install-software-standard.py")
    (repo / "bin").mkdir()
    (repo / "bin/sync-codex-skills").symlink_to(ROOT / "bin/sync-codex-skills")
    (repo / "bin/sync-claude-shared").symlink_to(ROOT / "bin/sync-claude-shared")
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
    previous_guidance = (
        "Keep my leading preferences.\n"
        "<!-- pragmatic-hexagonal:start -->\nRead\n"
        "`~/.local/share/software-standards/pragmatic-hexagonal/references/instructions.md`\n"
        "<!-- pragmatic-hexagonal:end -->\n"
        "Keep my existing global preferences.\n"
    )
    global_file.write_text(previous_guidance)
    local_rule = home / ".claude/rules/local.md"
    local_rule.parent.mkdir(parents=True)
    local_rule.write_text("Keep my local rule.\n")
    (cache / "shared-workflow").symlink_to(repo / "claude/skills/shared-workflow")
    # Model the previous managed install at its filesystem boundary.
    legacy = home / ".local/share/software-standards/pragmatic-hexagonal"
    (legacy / "references").mkdir(parents=True)
    (legacy / ".dotfiles-managed").write_text("Installed by dotfiles install-software-standard.py\n")
    (legacy / "SKILL.md").write_text("---\nname: pragmatic-hexagonal\n---\n")
    (legacy / "references/instructions.md").write_text("Old architecture guidance.\n")
    old_claude = home / ".claude/skills/pragmatic-hexagonal"
    # Older setups linked the whole skills directory. Migrate that layout
    # before the shared sync runs, retaining external per-user skill links.
    old_sources = repo / "claude/skills"
    old_sources.mkdir(parents=True)
    old_claude.parent.symlink_to(old_sources, target_is_directory=True)
    personal = external / "personal"
    personal.mkdir()
    (personal / "SKILL.md").write_text("Keep my external skill.\n")
    (old_sources / "personal").symlink_to(personal)
    old_claude.symlink_to(legacy)
    old_rule = home / ".claude/rules/pragmatic-hexagonal.md"
    old_rule.symlink_to(legacy / "references/instructions.md")
    (cache / "pragmatic-hexagonal").symlink_to(legacy)
    # Custom aliases can target the package or a resource within it, including
    # from user-owned trees that the installer must not traverse or rewrite.
    alias = old_claude.with_name("my-architecture")
    alias.symlink_to(legacy)
    reference_alias = personal / "architecture.md"
    reference_alias.symlink_to(legacy / "references/instructions.md")
    assert (alias / "SKILL.md").is_file() and reference_alias.is_file()
    executables = tmp_path / "bin"
    executables.mkdir()
    (executables / "python3").symlink_to(sys.executable)
    command = [shutil.which("make"), "-f", str(ROOT / "Makefile"), "codex-skills", "claude-shared",
               f"DOTFILES={repo}", f"HOME={home}"]
    env = {"PATH": f"{executables}:/usr/bin:/bin"}

    # An incomplete update must not replace the working managed installation.
    construction.unlink()
    rejected = subprocess.run(command, cwd=repo, env=env, capture_output=True, text=True)
    assert rejected.returncode != 0
    assert "missing package resource" in rejected.stderr and "construction.md" in rejected.stderr
    assert global_file.read_text() == previous_guidance
    assert old_claude.resolve() == legacy.resolve() and old_rule.is_file()
    assert old_claude.parent.is_symlink(), "rejected update migrated the directory"
    assert not (home / ".local/share/software-standards/builder").exists()
    construction.write_text(construction_text)
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)

    installed = home / ".agents/skills/dotfiles/shared-workflow"
    assert (home / ".agents/skills/dotfiles").is_symlink()
    assert (installed / "SKILL.md").read_text() == instruction.read_text()
    assert not (installed / "SKILL.md").is_symlink()
    assert (installed / "references/guide.md").read_text() == "Review guide.\n"
    builder_installed = home / ".agents/skills/dotfiles/builder"
    assert (builder_installed / "references/standard.md").read_bytes() == (builder / "references/standard.md").read_bytes()
    assert (builder_installed / "references/construction.md").read_text() == construction_text
    assert (builder_installed / "scripts/operations.py").read_bytes() == (builder / "scripts/operations.py").read_bytes()
    assert re.search(r"^name: builder$", (builder_installed / "SKILL.md").read_text(), re.M)
    assert local.read_text() == "Local instructions.\n"
    package = (home / ".local/share/software-standards/builder").resolve()
    assert builder_installed.resolve() == package
    assert (home / ".claude/skills/builder").resolve() == package
    assert not old_claude.parent.is_symlink()
    assert (home / ".claude/skills/personal").resolve() == personal
    assert (old_sources / "pragmatic-hexagonal").readlink() == legacy
    assert builder.is_dir() and not builder.is_symlink(), "migration replaced the source skill"
    assert (home / ".claude/rules/builder.md").read_bytes() == (package / "references/instructions.md").read_bytes()
    assert not old_claude.is_symlink() and not old_rule.is_symlink()
    assert (alias / "SKILL.md").read_bytes() == (builder / "SKILL.md").read_bytes()
    assert reference_alias.read_bytes() == (package / "references/instructions.md").read_bytes()
    assert reference_alias.readlink() == legacy / "references/instructions.md"
    assert not (cache / "pragmatic-hexagonal").is_symlink()
    assert legacy.is_symlink() and legacy.resolve() == package
    assert global_file.read_text().startswith("Keep my leading preferences.\n")
    assert global_file.read_text().endswith("Keep my existing global preferences.\n")
    assert local_rule.read_text() == "Keep my local rule.\n"
    guidance = global_file.read_text()
    # Follow the actual installed instruction path, without claiming model loading.
    target, = re.findall(r"`(~\/[^`]+)`", guidance)
    assert (home / target[2:]).read_bytes() == (package / "references/instructions.md").read_bytes()

    instruction.write_text(instruction.read_text() + "Use the latest guide.\n")
    construction_text += "Protect retained behavior during the next increment.\n"
    construction.write_text(construction_text)
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert (installed / "SKILL.md").read_text() == instruction.read_text()
    assert local.read_text() == "Local instructions.\n"

    assert (alias / "references/construction.md").read_text() == construction_text
    assert reference_alias.read_bytes() == (package / "references/instructions.md").read_bytes()

    # A copied skill package must not depend on the dotfiles checkout layout.
    portable = tmp_path / "portable"
    shutil.copytree(builder_installed, portable)
    assert global_file.read_text() == guidance, "repeat install changed global instructions"
    shutil.rmtree(repo)
    assert (builder_installed / "references/standard.md").is_file()
    assert (home / ".claude/skills/builder/references/construction.md").read_text() == construction_text
    assert (home / ".claude/skills/personal/SKILL.md").read_text() == "Keep my external skill.\n"
    assert (alias / "references/construction.md").read_text() == construction_text
    assert reference_alias.read_bytes() == (package / "references/instructions.md").read_bytes()
    for document in (portable / "SKILL.md", portable / "references/standard.md",
                     portable / "references/construction.md"):
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if "://" not in target and not target.startswith("#"):
                assert (document.parent / target.split("#")[0]).is_file(), target
