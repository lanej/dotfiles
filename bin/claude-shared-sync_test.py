"""One detector for migrating Claude's shared links without changing local entries."""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def test_make_claude_shared_migrates_links_and_preserves_local_entries(tmp_path):
    repo = tmp_path / "dotfiles"
    home = tmp_path / "user"
    skill = repo / "ai/skills/shared-workflow"
    skill.mkdir(parents=True)
    instruction = skill / "SKILL.md"
    instruction.write_text("Shared instructions.\n")
    shutil.copytree(ROOT / "ai/skills/builder", repo / "ai/skills/builder")
    (repo / "scripts").mkdir()
    (repo / "scripts/install-software-standard.py").symlink_to(ROOT / "scripts/install-software-standard.py")
    agents = repo / "ai/agents"
    agents.mkdir(parents=True)
    external = tmp_path / "reviewer.md"
    external.write_text("Review instructions.\n")
    (agents / "reviewer.md").symlink_to(external)
    installed_skills = home / ".claude/skills"
    installed_skills.mkdir(parents=True)
    (installed_skills / "shared-workflow").symlink_to(repo / "claude/skills/shared-workflow")
    alias = installed_skills / "my-workflow"
    alias.symlink_to(repo / "claude/skills/shared-workflow")
    retired = installed_skills / "retired"
    retired.symlink_to(repo / "claude/skills/retired")
    local = installed_skills / "local-workflow/SKILL.md"
    local.parent.mkdir()
    local.write_text("Local instructions.\n")
    (repo / "ai/skills/local-workflow").mkdir()
    (repo / "ai/skills/local-workflow/SKILL.md").write_text("Other instructions.\n")
    installed_agents = home / ".claude/agents"
    installed_agents.mkdir()
    (installed_agents / "reviewer.md").symlink_to(repo / "claude/agents/reviewer.md")
    local_agent = installed_agents / "local.md"
    local_agent.write_text("Local agent.\n")
    (agents / "local.md").write_text("Other agent.\n")
    (repo / "bin").mkdir()
    (repo / "bin/sync-claude-shared").symlink_to(ROOT / "bin/sync-claude-shared")
    executables = tmp_path / "bin"
    executables.mkdir()
    (executables / "python3").symlink_to(sys.executable)
    command = [shutil.which("make"), "-f", str(ROOT / "Makefile"), "claude-shared",
               f"DOTFILES={repo}", f"HOME={home}"]
    env = {"PATH": f"{executables}:/usr/bin:/bin"}
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)

    assert (installed_skills / "shared-workflow").readlink() == skill
    assert (installed_skills / "shared-workflow/SKILL.md").read_text() == instruction.read_text()
    assert alias.readlink() == skill
    assert (installed_agents / "reviewer.md").readlink() == agents / "reviewer.md"
    assert (installed_agents / "reviewer.md").read_text() == external.read_text()
    assert not retired.is_symlink()
    assert local.read_text() == "Local instructions.\n"
    assert local_agent.read_text() == "Local agent.\n"

    instruction.write_text("Updated shared instructions.\n")
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert (installed_skills / "shared-workflow/SKILL.md").read_text() == instruction.read_text()
    assert alias.readlink() == skill
    assert local.read_text() == "Local instructions.\n"
    assert local_agent.read_text() == "Local agent.\n"
