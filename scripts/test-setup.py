#!/usr/bin/env python3
"""One default-setup workflow: partial install, dependency repair, safe rerun."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent


def snapshot(home):
    return {str(path.relative_to(home)): (
        os.readlink(path) if path.is_symlink() else path.read_bytes()
    ) for path in home.rglob("*") if path.is_symlink() or path.is_file()}


def main():
    with tempfile.TemporaryDirectory(prefix="dotfiles-setup-") as temporary:
        temporary = Path(temporary).resolve()
        repo = temporary / "dotfiles"
        home = temporary / "home"
        executables = temporary / "bin"
        home.mkdir()
        executables.mkdir()
        shutil.copytree(ROOT, repo, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        # Only base utilities are available; optional tools cannot leak in from
        # the developer machine or CI runner. Network boundaries stay offline.
        for name in ("awk", "basename", "bash", "cat", "cp", "dirname", "find",
                     "grep", "head", "ln", "make", "mkdir", "mktemp", "mv",
                     "pwd", "readlink", "rm", "sed", "sort", "tail", "touch", "tr",
                     "uname", "wc"):
            (executables / name).symlink_to(shutil.which(name))
        (executables / "python3").symlink_to(sys.executable)
        git = executables / "git"
        git.write_text('#!/bin/sh\nif [ "$1" = clone ]; then\n'
                       '  echo "Fixture network unavailable" >&2; exit 1\nfi\n'
                       f'exec "{shutil.which("git")}" "$@"\n')
        git.chmod(0o755)
        subprocess.run([shutil.which("git"), "init", "-q", str(repo)], check=True)
        env = {"HOME": str(home), "PATH": str(executables), "TERM": "xterm-256color",
               "CLICOLOR_FORCE": "1", "LC_ALL": "C", "UV": "uv",
               "SETUP_TMUX_STATE": str(temporary / "tmux-session")}
        command = [shutil.which("make"), "--no-print-directory"]
        dry_run = subprocess.run([*command, "-n"], cwd=repo, env=env,
                                 capture_output=True, text=True, timeout=30)
        assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
        assert snapshot(home) == {}, "make -n must not install configuration"

        partial = subprocess.run(command, cwd=repo, env=env,
                                 capture_output=True, text=True, timeout=30)
        assert partial.returncode != 0, partial.stdout + partial.stderr
        assert "\033[31m✗\033[0m tmux-plugins" in partial.stdout, partial.stdout + partial.stderr
        assert "Missing dependency: tmux." in partial.stdout, partial.stdout
        assert "\033[32m✓\033[0m cargo" in partial.stdout, partial.stdout
        assert "\033[32m✓\033[0m tmux-config" in partial.stdout, partial.stdout
        assert "incomplete" in partial.stdout
        assert "instruction-size" not in partial.stdout and "audit-skills" not in partial.stdout
        assert "test-ui-review" not in partial.stdout
        assert "test-pragmatic-hexagonal" not in partial.stdout
        if sys.platform == "darwin":
            assert (home / ".config/yabai/yabairc").is_symlink()
            assert not (home / "Documents/superwhisper").exists()
            assert "superwhisper" not in partial.stdout
            assert not (home / ".config/polybar").exists()
            assert not (home / ".xinitrc").exists()
            assert not (home / ".config/bspwm").exists()
            assert "polybar" not in partial.stdout and "bspwm" not in partial.stdout
            unsupported_target, required_os = "polybar", "Linux"
        else:
            assert (home / ".config/polybar").resolve() == repo / "polybar"
            assert (home / ".xinitrc").is_symlink()
            assert (home / ".config/bspwm/bspwmrc").is_symlink()
            assert not (home / ".config/yabai").exists()
            assert not (home / "Documents/superwhisper").exists()
            assert "yabai" not in partial.stdout and "superwhisper" not in partial.stdout
            unsupported_target, required_os = "yabai", "Darwin"
        before_explicit = snapshot(home)
        unsupported = subprocess.run([*command, unsupported_target], cwd=repo, env=env,
                                     capture_output=True, text=True, timeout=30)
        assert unsupported.returncode != 0, unsupported.stdout + unsupported.stderr
        assert f"requires {required_os}" in unsupported.stderr, unsupported.stderr
        assert snapshot(home) == before_explicit, "unsupported target wrote configuration"
        assert (home / ".tmux.conf").resolve() == repo / "rc/tmux.conf"
        assert (home / ".config/nvim").resolve() == repo / "nvim"
        assert (home / ".config/kitty/kitty.conf").is_symlink()
        assert (home / ".claude/CLAUDE.md").is_symlink()
        assert (home / ".codex/AGENTS.md").read_bytes() == (repo / "codex/AGENTS.md").read_bytes()
        skill = home / ".agents/skills/dotfiles/pragmatic-hexagonal"
        source = repo / "ai/skills/pragmatic-hexagonal"
        assert (skill / "SKILL.md").read_bytes() == (source / "SKILL.md").read_bytes()
        assert (skill / "references/standard.md").read_bytes() == (repo / "docs/pragmatic-hexagonal-architecture.md").read_bytes()
        assert (skill / "scripts/check_examples.py").is_file()
        # Guidance installs even while optional tools and network are absent.
        assert (home / ".codex/agents/code-reviewer.toml").is_file()
        assert not (home / ".tmux/plugins/tpm").exists()
        # Local cache budgets are deliberately editable and must survive reruns.
        budgets = home / ".config/dev-cache-budgets.json"
        budgets.write_text('{"local": "retained"}\n')

        # Install the missing dependency and fixture TPM at their external
        # boundaries, then retry through the same default make entrypoint.
        tmux = executables / "tmux"
        tmux.write_text('#!/bin/sh\ncase "$1" in\n'
                        '  list-sessions) test -f "$SETUP_TMUX_STATE" ;;\n'
                        '  new-session) echo "$4" > "$SETUP_TMUX_STATE" ;;\n'
                        '  kill-session) rm "$SETUP_TMUX_STATE" ;;\n'
                        '  *) exit 1 ;;\nesac\n')
        tmux.chmod(0o755)
        installer = home / ".tmux/plugins/tpm/bin/install_plugins"
        installer.parent.mkdir(parents=True)
        installer.write_text('#!/bin/sh\n'
                             'mkdir -p "$HOME/.config/tmux/plugins/tmux-resurrect/.git"\n')
        installer.chmod(0o755)
        local_plugin = home / ".config/tmux/plugins/local-plugin/settings.conf"
        local_plugin.parent.mkdir(parents=True)
        local_plugin.write_text("user-managed plugin configuration\n")
        repaired = subprocess.run(command, cwd=repo, env=env,
                                  capture_output=True, text=True, timeout=30)
        assert "\033[32m✓\033[0m tmux-plugins" in repaired.stdout, repaired.stdout
        assert local_plugin.read_text() == "user-managed plugin configuration\n"
        assert not Path(env["SETUP_TMUX_STATE"]).exists(), "bootstrap session leaked"
        strategy = home / ".config/tmux/plugins/tmux-resurrect/strategies/claude.sh"
        assert strategy.resolve() == repo / "bin/tmux-resurrect-claude"
        installed = snapshot(home)

        # A subsequent run must leave a user's existing tmux session and all
        # installed file contents/symlink destinations unchanged.
        Path(env["SETUP_TMUX_STATE"]).write_text("user-session")
        repeated = subprocess.run(command, cwd=repo, env={**env, "NO_COLOR": "1"},
                                  capture_output=True, text=True, timeout=30)
        assert repeated.returncode == repaired.returncode
        assert "✓ tmux-plugins" in repeated.stdout, repeated.stdout
        assert "\033[" not in repeated.stdout, repeated.stdout
        assert snapshot(home) == installed, "rerun changed installed configuration"
        assert Path(env["SETUP_TMUX_STATE"]).read_text() == "user-session"
        print("PASS: default make gates OS tools, reports partial setup, and preserves installed configuration, local plugins, and user sessions on retry.")


if __name__ == "__main__":
    main()
