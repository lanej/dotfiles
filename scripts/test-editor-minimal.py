#!/usr/bin/env python3
"""Configure a remote editor, edit offline with Vim and Neovim, preserve local files."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    vim, nvim = shutil.which("vim"), shutil.which("nvim")
    assert vim and nvim, "Install Vim and Neovim to run make test-editor-minimal."
    with tempfile.TemporaryDirectory(prefix="dotfiles-editor-minimal-") as temporary:
        temporary = Path(temporary).resolve()
        home, executables = temporary / "home", temporary / "bin"
        home.mkdir()
        executables.mkdir()
        # No downloader, package manager, language runtime, or plugin tool can
        # leak in from the runner. Python is removed after TOML configuration.
        for name in ("bash", "ln", "make", "mkdir", "mktemp", "rm", "uname"):
            (executables / name).symlink_to(shutil.which(name))
        python = executables / "python3"
        python.symlink_to(sys.executable)
        config_home = home / "settings"
        env = {"HOME": str(home), "XDG_CONFIG_HOME": str(config_home),
               "PATH": str(executables), "TERM": "xterm", "LC_ALL": "C"}

        def run(*args, check=True):
            result = subprocess.run(args, cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=30)
            if check and result.returncode != 0:
                error = home / "editor-error"
                raise AssertionError(result.stdout + result.stderr + (error.read_text() if error.exists() else ""))
            return result

        config = config_home / "dotfiles/config.toml"
        config.parent.mkdir(parents=True)
        # A later editor set chooses the full setup; select minimal instead
        # before applying anything on this remote host.
        desktop_off = '\n[tools]\nx11 = false\npolybar = false\nbspwm = false\nyabai = false\nskhd = false\n'
        config.write_text('sets = ["editor-minimal", "editor"]\n' + desktop_off)
        full = json.loads(run("make", "--no-print-directory", "plan").stdout)
        assert "neovim" in {tool["name"] for tool in full["tools"]}
        assert "editor-minimal" not in {tool["name"] for tool in full["tools"]}
        minimal_config = 'sets = ["editor", "editor-minimal"]\n' + desktop_off
        config.write_text(minimal_config)
        minimal = json.loads(run("make", "--no-print-directory", "plan").stdout)
        assert [tool["name"] for tool in minimal["tools"]] == ["editor-minimal"]
        assert minimal["setup"] == ["editor-minimal"]
        assert not minimal["prepare"] and not minimal["post"]

        # Switch away from workstation symlinks without writing through them.
        vimrc, nvim_config = home / ".vimrc", config_home / "nvim"
        vimrc.symlink_to(ROOT / "vim/init.vim")
        nvim_config.symlink_to(ROOT / "nvim", target_is_directory=True)
        full_init = (ROOT / "nvim/init.lua").read_bytes()
        poison = 'command RemotePluginLeak throw "Cached workstation plugin loaded"\n'
        vim_plugin = home / ".vim/plugin/leak.vim"
        vim_plugin.parent.mkdir(parents=True)
        vim_plugin.write_text(poison)
        nvim_plugin = home / ".local/share/nvim/site/pack/old/start/leak/plugin/leak.vim"
        nvim_plugin.parent.mkdir(parents=True)
        nvim_plugin.write_text(poison)
        run("make", "--no-print-directory", "configure")
        assert vimrc.resolve() == ROOT / "editor-minimal/init.vim"
        assert nvim_config.resolve() == ROOT / "editor-minimal"
        assert (ROOT / "nvim/init.lua").read_bytes() == full_init

        # The direct target also works on a box without Python/TOML support.
        python.unlink()
        run("make", "--no-print-directory", "editor-minimal")
        document = home / "example.py"
        document.write_text("before\n")
        script = home / "edit.vim"
        script.write_text('''
try
  if !&number || !&expandtab || &filetype !=# 'python'
    throw printf('Minimal editing defaults did not load: number=%d expandtab=%d filetype=%s', &number, &expandtab, &filetype)
  endif
  if exists(':RemotePluginLeak') || exists(':Lazy') || exists(':Mason')
    throw 'Third-party plugins loaded'
  endif
  execute "normal ggccprint('minimal')\\<Esc>"
  normal ,w
  if &modified
    throw 'The comma-w save mapping did not write the file'
  endif
catch
  call writefile([v:exception, v:throwpoint], $HOME . '/editor-error')
  cquit
endtry
qa!
''')
        # Automatic startup uses the installed links, without -u overrides.
        run(vim, "--not-a-term", "-N", "-n", "-i", "NONE", str(document), "-S", str(script))
        assert document.read_text() == "print('minimal')\n"
        document.write_text("before neovim\n")
        run(nvim, "--headless", "-n", "-i", "NONE", str(document), "-S", str(script))
        assert document.read_text() == "print('minimal')\n"

        # Preserve a real user config and reject contradictory machine choices
        # before applying either editor profile.
        nvim_config.unlink()
        nvim_config.mkdir()
        local_config = nvim_config / "init.lua"
        local_config.write_text("-- User configuration\n")
        vimrc.unlink()
        vimrc.symlink_to(ROOT / "vim/init.vim")
        rejected = run("make", "--no-print-directory", "editor-minimal", check=False)
        assert rejected.returncode != 0 and "Preserving existing configuration" in rejected.stderr
        assert local_config.read_text() == "-- User configuration\n"
        assert vimrc.resolve() == ROOT / "vim/init.vim"
        python.symlink_to(sys.executable)
        config.write_text(minimal_config + "neovim = true\n")
        conflict = run("make", "--no-print-directory", "configure", check=False)
        assert conflict.returncode != 0 and "conflicts with tools.neovim" in conflict.stderr, conflict.stdout + conflict.stderr
        assert local_config.read_text() == "-- User configuration\n"
        print("PASS: minimal set configures existing Vim/Neovim, edits without plugins or Python, and preserves user files.")


if __name__ == "__main__":
    main()
