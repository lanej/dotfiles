#!/usr/bin/env python3
"""One setup workflow: native baseline, additions, dependency repair, safe rerun."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib


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
        # Exercise supported local Codex preferences even in a clean CI checkout.
        local_guidance = repo / "codex/AGENTS.local.md"
        if not local_guidance.exists():
            local_guidance.write_text("Keep fixture-local Codex preferences.\n")
        # Only base utilities are available; optional tools cannot leak in from
        # the developer machine or CI runner. Network boundaries stay offline.
        for name in ("awk", "basename", "bash", "cat", "cp", "dirname", "find",
                     "grep", "head", "ln", "make", "mkdir", "mktemp", "mv",
                     "pwd", "readlink", "rm", "sed", "sort", "tail", "touch", "tr",
                     "uname", "wc"):
            (executables / name).symlink_to(shutil.which(name))
        git = executables / "git"
        git.write_text('#!/bin/sh\nif [ "$1" = clone ]; then\n'
                       '  echo "Fixture network unavailable" >&2; exit 1\nfi\n'
                       f'exec "{shutil.which("git")}" "$@"\n')
        git.chmod(0o755)
        broker = executables / "agent-status-broker"
        broker.write_text('#!/bin/sh\n[ "$1" = install ] || exit 1\n'
                          'case " $* " in\n'
                          '  *" --no-start "*) ;;\n'
                          '  *) touch "$HOME/broker-started" ;;\n'
                          'esac\ntouch "$HOME/broker-installed"\n')
        broker.chmod(0o755)
        subprocess.run([shutil.which("git"), "init", "-q", str(repo)], check=True)
        machine_config = home / ".config/dotfiles/config.toml"
        env = {"HOME": str(home), "PATH": str(executables), "TERM": "xterm-256color",
               "CLICOLOR_FORCE": "1", "LC_ALL": "C", "UV": "uv",
               "AGENT_STATUS_BIN": str(broker),
               "SETUP_TMUX_STATE": str(temporary / "tmux-session")}
        command = [shutil.which("make"), "--no-print-directory"]

        # Basic linking must work before bootstrap provides Python. Use the
        # same restricted PATH on developer machines and CI runners alike.
        minimal_home = temporary / "minimal-home"
        minimal_home.mkdir()
        minimal_env = {**env, "HOME": str(minimal_home)}
        minimal_preview = subprocess.run([*command, "-n", "shell", "git"], cwd=repo, env=minimal_env,
                                         capture_output=True, text=True, timeout=30)
        assert minimal_preview.returncode == 0, minimal_preview.stdout + minimal_preview.stderr
        assert snapshot(minimal_home) == {}, "make -n must not install configuration"
        minimal = subprocess.run([*command, "shell", "git"], cwd=repo, env=minimal_env,
                                 capture_output=True, text=True, timeout=30)
        assert minimal.returncode == 0, minimal.stdout + minimal.stderr
        assert (minimal_home / ".bashrc").resolve() == repo / "bash/bashrc"
        assert (minimal_home / ".gitconfig").resolve() == repo / "git/gitconfig"

        dry_run = subprocess.run([*command, "-n"], cwd=repo, env=env,
                                 capture_output=True, text=True, timeout=30)
        assert dry_run.returncode == 0, dry_run.stdout + dry_run.stderr
        assert snapshot(home) == {}, "make -n must not install configuration"

        # Default Make configures the native baseline without Python, package
        # managers, or downloaders available on PATH.
        native = subprocess.run(command, cwd=repo, env=env,
                                capture_output=True, text=True, timeout=30)
        assert native.returncode == 0, native.stdout + native.stderr
        native_path = ".config/yabai/yabairc" if sys.platform == "darwin" else ".xinitrc"
        assert (home / native_path).is_symlink()
        assert machine_config.is_file(), "Default make must initialize the machine TOML."
        platform_set = "macos" if sys.platform == "darwin" else "linux"
        assert tomllib.loads(machine_config.read_text()) == {"sets": [platform_set]}
        assert not (home / ".bashrc").exists()
        assert not (home / ".config/nvim").exists()

        # Local choices survive another Python-free default make before the
        # full configuration stage reads them.
        machine_config.write_text('# Local preferences\nsets = ["shell"]\n[tools]\nmermaid = false\n')
        local_config = machine_config.read_bytes()
        native_again = subprocess.run(command, cwd=repo, env=env,
                                      capture_output=True, text=True, timeout=30)
        assert native_again.returncode == 0, native_again.stdout + native_again.stderr
        assert machine_config.read_bytes() == local_config

        (executables / "python3").symlink_to(sys.executable)
        # Configure adds the chosen bundles to that same baseline.
        configure = [*command, "configure"]
        selected_only = subprocess.run(configure, cwd=repo, env=env,
                                       capture_output=True, text=True, timeout=30)
        assert (home / ".bashrc").is_symlink(), selected_only.stdout + selected_only.stderr
        assert not (home / ".config/nvim").exists()
        assert not (home / ".tmux.conf").exists()
        assert not (home / "broker-installed").exists()
        machine_config.write_text('sets = ["workstation"]\n')

        # The opt-in multiplexer can be configured before its binary is
        # installed, without pulling in tmux plugins or unrelated integrations.
        zellij = subprocess.run([*command, "zellij"], cwd=repo, env=env,
                                capture_output=True, text=True, timeout=30)
        assert zellij.returncode == 0, zellij.stdout + zellij.stderr
        assert (home / ".config/zellij/config.kdl").resolve() == repo / "zellij/config.kdl"
        assert (home / ".config/zellij/layouts/tmux.kdl").resolve() == repo / "zellij/layouts/tmux.kdl"
        picker = home / ".local/bin/zellij-picker"
        assert picker.resolve() == repo / "bin/zellij-picker" and os.access(picker, os.X_OK)

        # Missing required source is an incomplete step, not a successful skip.
        # The actual setup runner must still complete independent configuration.
        entrypoint = repo / "ai/skills/builder/SKILL.md"
        entrypoint_bytes = entrypoint.read_bytes()
        entrypoint.unlink()
        missing = subprocess.run(configure, cwd=repo, env=env,
                                 capture_output=True, text=True, timeout=30)
        assert missing.returncode != 0, missing.stdout + missing.stderr
        assert "\033[31m✗\033[0m software-standard" in missing.stdout, missing.stdout
        assert "missing package resource" in missing.stdout and "SKILL.md" in missing.stdout
        assert "\033[32m✓\033[0m cargo" in missing.stdout, missing.stdout
        assert not (home / ".local/share/software-standards/builder").exists()
        entrypoint.write_bytes(entrypoint_bytes)

        partial = subprocess.run(configure, cwd=repo, env=env,
                                 capture_output=True, text=True, timeout=30)
        assert partial.returncode != 0, partial.stdout + partial.stderr
        assert "\033[31m✗\033[0m tmux-plugins" in partial.stdout, partial.stdout + partial.stderr
        assert "Missing dependency: tmux." in partial.stdout, partial.stdout
        assert "\033[32m✓\033[0m cargo" in partial.stdout, partial.stdout
        assert "\033[32m✓\033[0m tmux-config" in partial.stdout, partial.stdout
        assert "\033[32m✓\033[0m agent-status-broker" in partial.stdout, partial.stdout
        assert (home / "broker-installed").is_file()
        assert not (home / "broker-started").exists(), "default make started the broker"
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
        expected_guidance = (repo / "codex/AGENTS.md").read_bytes() + local_guidance.read_bytes()
        assert (home / ".codex/AGENTS.md").read_bytes() == expected_guidance
        skill = home / ".agents/skills/dotfiles/builder"
        source = repo / "ai/skills/builder"
        assert (skill / "SKILL.md").read_bytes() == (source / "SKILL.md").read_bytes()
        assert (skill / "references/standard.md").read_bytes() == (repo / "docs/pragmatic-hexagonal-architecture.md").read_bytes()
        assert (skill / "references/construction.md").read_bytes() == (repo / "docs/software-construction.md").read_bytes()
        assert (skill / "scripts/check_examples.py").is_file()
        package = home / ".local/share/software-standards/builder"
        claude_skill = home / ".claude/skills/builder"
        rule = home / ".claude/rules/builder.md"
        assert skill.resolve() == package
        assert claude_skill.resolve() == package
        assert not (package / "references/standard.md").is_symlink()
        assert rule.read_bytes() == (source / "references/instructions.md").read_bytes()
        # Guidance installs even while optional tools and network are absent.
        assert (home / ".codex/agents/code-reviewer.toml").is_file()
        assert not (home / ".tmux/plugins/tpm").exists()
        # Local cache budgets are deliberately editable and must survive reruns.
        budgets = home / ".config/dev-cache-budgets.json"
        budgets.write_text('{"local": "retained"}\n')
        local_layout = home / ".config/zellij/layouts/local.kdl"
        local_layout.write_text("layout { pane }\n")

        # Install the missing dependency and fixture TPM at their external
        # boundaries, then retry through the same make configure entrypoint.
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
        repaired = subprocess.run(configure, cwd=repo, env=env,
                                  capture_output=True, text=True, timeout=30)
        assert "\033[32m✓\033[0m tmux-plugins" in repaired.stdout, repaired.stdout
        assert local_plugin.read_text() == "user-managed plugin configuration\n"
        assert local_layout.read_text() == "layout { pane }\n"
        assert not Path(env["SETUP_TMUX_STATE"]).exists(), "bootstrap session leaked"
        strategy = home / ".config/tmux/plugins/tmux-resurrect/strategies/claude.sh"
        assert strategy.resolve() == repo / "bin/tmux-resurrect-claude"
        installed = snapshot(home)

        # A subsequent run must leave a user's existing tmux session and all
        # installed file contents/symlink destinations unchanged.
        Path(env["SETUP_TMUX_STATE"]).write_text("user-session")
        repeated = subprocess.run(configure, cwd=repo, env={**env, "NO_COLOR": "1"},
                                  capture_output=True, text=True, timeout=30)
        assert repeated.returncode == repaired.returncode
        assert "✓ tmux-plugins" in repeated.stdout, repeated.stdout
        assert "\033[" not in repeated.stdout, repeated.stdout
        assert snapshot(home) == installed, "rerun changed installed configuration"
        assert Path(env["SETUP_TMUX_STATE"]).read_text() == "user-session"
        assert not (home / "broker-started").exists(), "rerun started the broker"
        print("PASS: make configures the native baseline, make configure adds selected bundles, and retries preserve installed configuration and user sessions.")


if __name__ == "__main__":
    main()
