"""One detector for exposing shared skills and migrating the Builder package."""

from pathlib import Path
import json
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def test_selective_workflow_install_survives_checkout_removal_and_preserves_local_skills(tmp_path):
    source = tmp_path / "checkout/ai/skills"
    source.mkdir(parents=True)
    names = json.loads((ROOT / "ai/skills/portable-workflows.json").read_text())
    shutil.copyfile(ROOT / "ai/skills/portable-workflows.json", source / "portable-workflows.json")
    for name in names:
        shutil.copytree(ROOT / "ai/skills" / name, source / name)
    home = tmp_path / "user"
    local = home / ".agents/skills/personal/SKILL.md"
    local.parent.mkdir(parents=True)
    local.write_text("Personal workflow.\n")
    command = [sys.executable, str(ROOT / "bin/sync-codex-skills"),
               "--source", str(source), "--home", str(home)]
    resources = {
        "socrates": {
            "dialogue.txt": ROOT / "claude/commands/socrates/dialogue.txt",
            "spec-scaffold.tpl": ROOT / "claude/commands/socrates/spec-scaffold.tpl",
            "phases-2-3.txt": ROOT / "claude/commands/socrates/phases-2-3.txt",
        },
        "reflection": {"reflection.md": ROOT / "ai/agents/reflection.md"},
    }
    for _ in range(2):
        subprocess.run(command + ["--only", "shape"], check=True, capture_output=True, text=True)
        for name in names:
            installed = home / ".agents/skills/dotfiles" / name
            assert installed.is_dir() and not installed.is_symlink()
            assert (installed / "SKILL.md").read_bytes() == (source / name / "SKILL.md").read_bytes()
        for name, references in resources.items():
            installed = home / ".agents/skills/dotfiles" / name
            entrypoint = installed / "SKILL.md"
            assert entrypoint.is_file() and not entrypoint.is_symlink()
            assert entrypoint.read_bytes() == (ROOT / "ai/skills" / name / "SKILL.md").read_bytes()
            for filename, resource in references.items():
                assert (installed / "references" / filename).read_bytes() == resource.read_bytes()
        assert local.read_text() == "Personal workflow.\n"
    unrelated = home / ".codex/dotfiles-skills/unrelated/SKILL.md"
    unrelated.parent.mkdir()
    unrelated.write_text("Keep this installed entry.\n")
    subprocess.run(command + ["--only", *names], check=True, capture_output=True, text=True)
    assert unrelated.read_text() == "Keep this installed entry.\n"
    shutil.rmtree(source.parent.parent)
    for name in names:
        installed = home / ".agents/skills/dotfiles" / name
        for document in installed.rglob("*"):
            assert not document.is_symlink(), document
        for target in re.findall(r"\]\(([^)]+)\)", (installed / "SKILL.md").read_text()):
            if "://" not in target and not target.startswith("#"):
                assert (installed / target).is_file(), target
    helper = home / ".agents/skills/dotfiles/handoff/scripts/transcript.py"
    subprocess.run([sys.executable, str(helper), "--help"], check=True, capture_output=True)


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
    obsolete = repo / "ai/skills/paseo-plugin"
    obsolete.mkdir()
    (obsolete / "SKILL.md").write_text("Retired instructions.\n")
    builder = repo / "ai/skills/builder"
    shutil.copytree(ROOT / "ai/skills/builder", builder)
    shutil.copyfile(ROOT / "ai/skills/project-only.json", repo / "ai/skills/project-only.json")
    project_names = json.loads((repo / "ai/skills/project-only.json").read_text())
    for name in project_names:
        directory = repo / "ai/skills" / name
        if not directory.exists():
            directory.mkdir()
            (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Project-only guidance.\n---\n")
    construction = builder / "references/construction.md"
    construction_text = construction.read_text()
    (repo / "ai/agents").mkdir()
    (repo / "scripts").mkdir()
    (repo / "scripts/install-software-standard.py").symlink_to(ROOT / "scripts/install-software-standard.py")
    (repo / "bin").mkdir()
    (repo / "bin/sync-codex-skills").symlink_to(ROOT / "bin/sync-codex-skills")
    (repo / "bin/sync-claude-shared").symlink_to(ROOT / "bin/sync-claude-shared")
    (repo / "bin/sync-agent-status-hooks").symlink_to(ROOT / "bin/sync-agent-status-hooks")
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
    for name in project_names:
        if name != "builder":
            (old_sources / name).symlink_to(repo / "ai/skills" / name)
        (cache / name).symlink_to(repo / "ai/skills" / name)
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
    subprocess.run([sys.executable, str(repo / "scripts/install-software-standard.py"), "--source", str(builder), "--home", str(home)], check=True, capture_output=True)
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)

    installed = home / ".agents/skills/dotfiles/shared-workflow"
    assert (home / ".agents/skills/dotfiles").is_symlink()
    assert (installed / "SKILL.md").read_text() == instruction.read_text()
    assert not (installed / "SKILL.md").is_symlink()
    assert (installed / "references/guide.md").read_text() == "Review guide.\n"
    builder_installed = home / ".agents/skills/dotfiles/builder"
    for base in (home / ".agents/skills/dotfiles", home / ".claude/skills"):
        for name in project_names:
            assert not (base / name).exists() and not (base / name).is_symlink()
    assert not builder_installed.exists() and not builder_installed.is_symlink()
    assert local.read_text() == "Local instructions.\n"
    assert not (home / ".agents/skills/dotfiles/paseo-plugin").exists()
    assert not (home / ".claude/skills/paseo-plugin").exists()
    assert (obsolete / "SKILL.md").read_text() == "Retired instructions.\n"
    package = (home / ".local/share/software-standards/builder").resolve()
    assert (package / "references/construction.md").read_text() == construction_text
    assert not (home / ".claude/skills/builder").exists()
    assert not old_claude.parent.is_symlink()
    assert (home / ".claude/skills/personal").resolve() == personal
    assert (old_sources / "pragmatic-hexagonal").readlink() == legacy
    assert builder.is_dir() and not builder.is_symlink(), "migration replaced the source skill"
    assert not (home / ".claude/rules/builder.md").exists()
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
    assert "<!-- builder:start -->" not in guidance
    assert "<!-- pragmatic-hexagonal:start -->" not in guidance

    instruction.write_text(instruction.read_text() + "Use the latest guide.\n")
    construction_text += "Protect retained behavior during the next increment.\n"
    construction.write_text(construction_text)
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert (installed / "SKILL.md").read_text() == instruction.read_text()
    assert local.read_text() == "Local instructions.\n"
    assert not (home / ".agents/skills/dotfiles/paseo-plugin").exists()
    assert not (home / ".claude/skills/paseo-plugin").exists()

    assert (alias / "references/construction.md").read_text() == construction_text
    assert reference_alias.read_bytes() == (package / "references/instructions.md").read_bytes()

    # A copied skill package must not depend on the dotfiles checkout layout.
    portable = tmp_path / "portable"
    shutil.copytree(package, portable)
    assert global_file.read_text() == guidance, "repeat install changed global instructions"
    shutil.rmtree(repo)
    assert not builder_installed.exists()
    assert (package / "references/construction.md").read_text() == construction_text
    assert (home / ".claude/skills/personal/SKILL.md").read_text() == "Keep my external skill.\n"
    assert (alias / "references/construction.md").read_text() == construction_text
    assert reference_alias.read_bytes() == (package / "references/instructions.md").read_bytes()
    for document in (portable / "SKILL.md", portable / "references/standard.md",
                     portable / "references/construction.md"):
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if "://" not in target and not target.startswith("#"):
                assert (document.parent / target.split("#")[0]).is_file(), target
