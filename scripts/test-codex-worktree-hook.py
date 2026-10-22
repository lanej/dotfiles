#!/usr/bin/env python3
"""Exercise repository config bootstrapping through the installed hook."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def main():
    source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "bin/codex-worktree-config"
    uv = shutil.which("uv")
    cache = subprocess.check_output([uv, "cache", "dir"], text=True).strip()
    with tempfile.TemporaryDirectory(prefix="codex-worktree-hook-") as folder:
        temporary = Path(folder).resolve()
        home = temporary / "home"
        dotfiles = home / ".files"
        (dotfiles / "bin").mkdir(parents=True)
        shutil.copy2(source, dotfiles / "bin/codex-worktree-config")
        codex_home = home / ".codex"
        codex_home.mkdir()
        user_config = '[desktop]\ngit-worktree-root = "/explicit/global/root"\n'
        (codex_home / "config.toml").write_text(user_config)
        existing_hook = {"hooks": [{"type": "command", "command": "true", "timeout": 3}]}
        hook_file = codex_home / "hooks.json"
        hook_file.write_text(json.dumps({"hooks": {"SessionStart": [existing_hook]}}))
        env = {
            **os.environ,
            "HOME": str(home),
            "CODEX_HOME": str(codex_home),
            "UV_CACHE_DIR": cache,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        }

        def run(command, **kwargs):
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30, **kwargs)
            assert result.returncode == 0, result.stdout + result.stderr
            return result.stdout

        setup = ["make", "codex-worktree-hook", f"DOTFILES={dotfiles}", f"UV={uv}"]
        run(setup, cwd=ROOT)
        installed = hook_file.read_bytes()
        run(setup, cwd=ROOT)
        assert hook_file.read_bytes() == installed
        assert (codex_home / "config.toml").read_text() == user_config
        groups = json.loads(installed)["hooks"]["SessionStart"]
        assert groups[0] == existing_hook
        handler = groups[-1]["hooks"][0]["command"]

        repo = temporary / "team project"
        repo.mkdir()
        run(["git", "init", "-q", "--initial-branch=main", str(repo)])
        run(["git", "-C", str(repo), "-c", "user.name=Hook check",
             "-c", "user.email=hook@example.invalid", "-c", "commit.gpgsign=false",
             "commit", "--allow-empty", "-qm", "Initialize fixture"])
        nested = repo / "src"
        nested.mkdir()

        def start(cwd):
            return run(handler, shell=True, cwd=cwd, input=json.dumps({
                "hook_event_name": "SessionStart", "source": "startup", "cwd": str(cwd),
            }))

        assert start(nested) == ""
        config = repo / ".codex/config.toml"
        expected = str(repo / ".worktrees")
        assert tomllib.loads(config.read_text())["desktop"]["git-worktree-root"] == expected
        configured = config.read_bytes()
        assert start(nested) == ""
        assert config.read_bytes() == configured

        # An owner adds other settings but leaves the worktree root unspecified.
        original = '# Keep this comment.\nmodel_reasoning_effort = "high"\n[desktop]\nambient-suggestions-enabled = true\n'
        config.write_text(original)
        assert start(nested) == ""
        assert config.read_text().startswith(original)
        parsed = tomllib.loads(config.read_text())
        assert parsed["model_reasoning_effort"] == "high"
        assert parsed["desktop"] == {
            "ambient-suggestions-enabled": True, "git-worktree-root": expected,
        }
        explicit = '[desktop]\ngit-worktree-root = "" # Deliberate owner choice.\n'
        config.write_text(explicit)
        assert start(nested) == ""
        assert config.read_text() == explicit

        # Starting in a linked checkout uses the primary path, not a nested root.
        linked = repo / ".worktrees/task"
        run(["git", "-C", str(repo), "worktree", "add", "--detach", str(linked)])
        assert start(linked) == ""
        assert tomllib.loads((linked / ".codex/config.toml").read_text())["desktop"]["git-worktree-root"] == expected
        (linked / ".codex/config.toml").unlink()
        (linked / ".codex").rmdir()
        run(["git", "-C", str(repo), "worktree", "remove", str(linked)])
        assert start(home) == ""
        assert (codex_home / "config.toml").read_text() == user_config
    print("Codex repository worktree hook check passed.")


if __name__ == "__main__":
    main()
