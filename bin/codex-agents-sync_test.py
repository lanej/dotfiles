"""One detector for sharing Claude agents with Codex through make."""

from pathlib import Path
import shutil
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parent.parent


def test_make_codex_agents_refreshes_shared_agents_and_preserves_local_agents(tmp_path):
    repo = tmp_path / "dotfiles"
    home = tmp_path / "user"
    source = repo / "claude/agents"
    source.mkdir(parents=True)
    external = tmp_path / "reviewer.md"
    # Representative legacy source: a symlink, Claude model/tools, and no
    # closing frontmatter delimiter, as in the installed shared agent tree.
    external.write_text(
        "---\nname: reviewer\ndescription: 'Review the user''s changes.'\n"
        "model: opus\ntools: Read, Glob, Grep\n"
        'Review correctness — include paths and literal """ when relevant.\n'
    )
    (source / "reviewer.md").symlink_to(external)
    (repo / "bin").mkdir()
    (repo / "bin/sync-codex-agents").symlink_to(ROOT / "bin/sync-codex-agents")
    local = home / ".codex/agents/local.toml"
    local.parent.mkdir(parents=True)
    local.write_text('name = "local"\n')
    executables = tmp_path / "bin"
    executables.mkdir()
    (executables / "python3").symlink_to(sys.executable)
    command = [shutil.which("make"), "-f", str(ROOT / "Makefile"), "codex-agents",
               f"DOTFILES={repo}", f"HOME={home}"]
    env = {"PATH": f"{executables}:/usr/bin:/bin"}
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)

    target = home / ".codex/agents/reviewer.toml"
    agent = tomllib.loads(target.read_text())
    assert agent == {
        "name": "reviewer",
        "description": "Review the user's changes.",
        "developer_instructions":
            'Review correctness — include paths and literal """ when relevant.',
        "sandbox_mode": "read-only",
    }
    assert local.read_text() == 'name = "local"\n'

    external.write_text(external.read_text() + "Check the latest changes.\n")
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert tomllib.loads(target.read_text())["developer_instructions"].endswith(
        "Check the latest changes."
    )
    (source / "reviewer.md").unlink()
    subprocess.run(command, cwd=repo, env=env, check=True, capture_output=True, text=True)
    assert not target.exists()
    assert local.read_text() == 'name = "local"\n'
