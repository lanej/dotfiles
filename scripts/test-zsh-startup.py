#!/usr/bin/env python3
"""Start a real login shell through partial setup, then enable fzf integration."""
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent


def main():
    with tempfile.TemporaryDirectory(prefix="dotfiles-zsh-") as temporary:
        temporary = Path(temporary).resolve()
        home = temporary / "home"
        executables = temporary / "bin"
        home.mkdir()
        executables.mkdir()
        for name in ("awk", "cat", "chmod", "date", "grep", "head", "mkdir",
                     "mktemp", "mv", "pwd", "rm", "sed", "sort", "uname"):
            (executables / name).symlink_to(shutil.which(name))
        for name in ("zshrc", "zshenv", "zlogin", "zlogout"):
            (home / ("." + name)).symlink_to(ROOT / "zsh" / name)
        env = {"HOME": str(home), "ZDOTDIR": str(home), "PATH": str(executables),
               "TERM": "dumb", "LC_ALL": "C", "TMPDIR": str(temporary)}
        shell = [shutil.which("zsh"), "-d", "-i", "-l", "-c"]
        probe = '''
[[ -n $PS1 ]] || exit 10
[[ $(bindkey '^R') == *history-incremental-search-backward* ]] || exit 11
for hook in $precmd_functions; do "$hook"; done
print -r -- READY
'''
        early = subprocess.run([*shell, probe], cwd=home, env=env,
                               capture_output=True, text=True, timeout=15)
        assert early.returncode == 0, early.stderr
        assert early.stdout == "READY\n" and early.stderr == "", early

        (home / ".files").symlink_to(ROOT)
        subprocess.run([shutil.which("make"), "zsh-config", f"HOME={home}"],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        # Machine-wide package prefixes are external boundaries. Keep macOS's
        # preinstalled Homebrew tools and other system plugins out of this home.
        profile = home / ".profile"
        isolated = profile.read_text().replace("/opt/", str(temporary / "opt") + "/")
        isolated = isolated.replace("/usr/local/", str(temporary / "usr-local") + "/")
        isolated = isolated.replace("/usr/share/", str(temporary / "usr-share") + "/")
        profile.unlink()
        profile.write_text(isolated)
        # SHELL is intentionally unset; dircolors must select a compatible
        # output format itself when the optional command is available.
        if dircolors := shutil.which("dircolors"):
            (executables / "dircolors").symlink_to(dircolors)
        (home / ".oh-my-zsh").mkdir()  # interrupted framework installation
        partial = subprocess.run([*shell, probe + '''
(( ! $+widgets[fzf-completion] )) || exit 12
(( ! $+functions[zsh_gh_copilot_suggest] )) || exit 13
'''], cwd=home, env=env, capture_output=True, text=True, timeout=15)
        assert partial.returncode == 0, partial.stderr
        assert partial.stdout == "READY\n" and partial.stderr == "", partial
        assert not (home / ".ssh/agent-env").exists()

        # Once fzf and fd become available, startup should activate the widgets
        # rather than suppressing output by disabling all optional integrations.
        fzf = executables / "fzf"
        fzf.write_text('''#!/bin/sh
[ "$*" = --zsh ] || exit 1
printf '%s\n' 'fzf-completion() { :; }' 'zle -N fzf-completion' '__fzf_defaults() { print -r -- "$*"; }'
''')
        fzf.chmod(0o755)
        fd = executables / "fd"
        fd.write_text("#!/bin/sh\nexit 0\n")
        fd.chmod(0o755)
        enabled = subprocess.run([*shell, probe + '''
(( $+widgets[fzf-file-widget-toggle] )) || exit 14
[[ $(bindkey '^G') == *fzf-completion* ]] || exit 15
'''], cwd=home, env=env, capture_output=True, text=True, timeout=15)
        assert enabled.returncode == 0, enabled.stderr
        assert enabled.stdout == "READY\n" and enabled.stderr == "", enabled
        assert (home / ".zsh/cache/fzf-init.zsh").is_file()
        print("PASS: partial zsh setup starts silently with a working prompt and native history; installed fzf activates its widgets.")


if __name__ == "__main__":
    main()
