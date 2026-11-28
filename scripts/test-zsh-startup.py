#!/usr/bin/env python3
"""Exercise Zsh startup, optional integrations, and transient prompt redraws."""
import fcntl
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import tempfile
import termios
import time


ROOT = Path(__file__).resolve().parent.parent


def test_transient_prompt(temporary, env, executables):
    home = temporary / "prompt-home"
    project = home / "projects" / "field-notes"
    project.mkdir(parents=True)
    (home / ".zshrc").symlink_to(ROOT / "zsh/zshrc")
    git = shutil.which("git")
    (executables / "git").symlink_to(git)
    shortpath = executables / "shortpath"
    shortpath.write_text("#!/bin/sh\n"
                         '[ "$PWD" = "$HOME" ] && [ "$*" = "--null -- projects/field-notes" ] || exit 1\n'
                         "printf 'proj/field-notes\\0'\n")
    shortpath.chmod(0o755)

    def git_run(*args):
        subprocess.run([git, "-c", "user.name=Prompt fixture", "-c", "user.email=fixture@example.invalid", *args],
                       cwd=project, check=True, capture_output=True)

    git_run("init", "-qb", "main")
    (project / "changed.md").write_text("Original\n")
    (project / "mixed.md").write_text("Original\n")
    git_run("add", ".")
    git_run("commit", "-qm", "Start")
    git_run("switch", "-qc", "upstream")
    git_run("commit", "--allow-empty", "-qm", "Upstream change")
    git_run("switch", "-q", "main")
    git_run("commit", "--allow-empty", "-qm", "Local change")
    git_run("branch", "--set-upstream-to=upstream")
    (project / "mixed.md").write_text("Staged\n")
    git_run("add", "mixed.md")
    (project / "mixed.md").write_text("Working copy\n")
    (project / "changed.md").write_text("Updated\n")
    (project / "another\nline.md").write_text("New\n")
    shell = shutil.which("zsh")
    child, terminal = pty.fork()
    if child == 0:
        os.chdir(project)
        os.execve(shell, [shell, "-d", "-i"], {
            **env, "HOME": str(home), "ZDOTDIR": str(home), "TERM": "xterm-256color",
            "DOTFILES_ZSH_PROMPT": "transient", "DOTFILES_THEME_DIR": str(ROOT / "design-system/generated"),
        })

    def read_until(marker=b"\x1b[?2004h"):
        output = b""
        deadline = time.monotonic() + 5
        while marker not in output:
            remaining = deadline - time.monotonic()
            assert remaining > 0 and select.select([terminal], [], [], remaining)[0], output
            chunk = os.read(terminal, 65536)
            assert chunk, output
            output += chunk
        return output

    def has_error_color(output):
        return b"\x1b[91m" in output or b"\x1b[38;5;9m" in output

    escape = re.compile(rb"\x1b(?:\[[0-?]*[ -/]*[@-~]|\([A-Za-z0-9])")
    try:
        fcntl.ioctl(terminal, termios.TIOCSWINSZ, struct.pack("HHHH", 18, 84, 0, 0))
        initial = read_until()
        expected = "~/proj/field-notes   main 1 1  1+ 2 1 ".encode()
        assert expected in escape.sub(b"", initial), initial
        assert b"\x1b[48;" not in initial.split(b"~/proj/field-notes", 1)[0], initial
        branch_boundary = initial.split(b"~/proj/field-notes", 1)[1]
        assert re.match(
            rb"(?:\x1b\[[0-9;]*m)* \x1b\[38;(?P<fill>[0-9;]+)m\x1b\[7m"
            + "".encode() + rb"\x1b\[27m(?:\x1b\[[0-9;]*m)*\x1b\[48;(?P=fill)m ",
            branch_boundary,
        ), initial
        assert not has_error_color(initial), initial
        os.write(terminal, b"false\r")
        after_failure = read_until()
        assert after_failure.count(b"~/proj/field-notes") == 1, after_failure
        plain = escape.sub(b"", after_failure)
        assert b"$ false" in plain, after_failure
        assert plain.count(expected) == 1, after_failure
        assert has_error_color(after_failure.rsplit(b"~/proj/field-notes", 1)[-1]), after_failure
        shortpath.unlink()
        os.write(terminal, b"true\r")
        after_success = read_until()
        assert b"~/projects/field-notes" in after_success, after_success
        live_prompt = after_success.rsplit(b"~/projects/field-notes", 1)[-1]
        assert b"main" in live_prompt and not has_error_color(live_prompt), after_success
        os.write(terminal, b"print aborted-fixture")
        read_until(b"print aborted-fixture")
        os.write(terminal, b"\x03")
        read_until()
        os.write(terminal, b'print -r -- "$ZLE_LINE_ABORTED"\r')
        after_abort = read_until()
        plain = escape.sub(b"", after_abort)
        assert b'$ print -r -- "$ZLE_LINE_ABORTED"' in plain, after_abort
        assert b"print aborted-fixture" in plain, after_abort
        assert plain.count(b"~/projects/field-notes") == 1, after_abort
    finally:
        os.close(terminal)
        try:
            os.kill(child, signal.SIGTERM)
        except ProcessLookupError:
            pass
        os.waitpid(child, 0)


def main():
    with tempfile.TemporaryDirectory(prefix="dotfiles-zsh-") as temporary:
        temporary = Path(temporary).resolve()
        home = temporary / "home"
        executables = temporary / "bin"
        home.mkdir()
        executables.mkdir()
        for name in ("awk", "basename", "cat", "chmod", "date", "grep", "head", "mkdir",
                     "mktemp", "mv", "pwd", "rm", "rmdir", "sed", "sort", "uname"):
            (executables / name).symlink_to(shutil.which(name))
        for name in ("zshrc", "zshenv", "zlogin", "zlogout"):
            (home / ("." + name)).symlink_to(ROOT / "zsh" / name)
        env = {"HOME": str(home), "ZDOTDIR": str(home), "PATH": str(executables),
               "TERM": "dumb", "LC_ALL": "C", "TMPDIR": str(temporary)}
        remote_home = temporary / "remote-home"
        remote_bin = remote_home / ".local/bin"
        remote_bin.mkdir(parents=True)
        (remote_home / ".zshenv").symlink_to(ROOT / "zsh/zshenv")
        remote_intent = remote_bin / "intent"
        remote_intent.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$*" "$INTENT_APPROVAL_SOCKET"\n')
        remote_intent.chmod(0o755)
        approval_environment = remote_home / ".intent-approval/environment"
        approval_environment.parent.mkdir()
        approval_environment.write_text(
            'export INTENT_APPROVAL_SOCKET="$HOME/.intent-approval/approval.sock"\n')
        remote = subprocess.run(
            [shutil.which("zsh"), "-d", "-c",
             'intent lifecycle inventory --directory "$HOME/.intent-approval"'],
            cwd=remote_home,
            env={**env, "HOME": str(remote_home), "ZDOTDIR": str(remote_home),
                 "PATH": "/usr/bin:/bin", "SSH_CONNECTION": "fixture"},
            capture_output=True, text=True, timeout=15)
        assert remote.returncode == 0, remote.stderr
        assert remote.stdout.splitlines() == [
            f"lifecycle inventory --directory {remote_home}/.intent-approval",
            f"{remote_home}/.intent-approval/approval.sock"], remote
        assert remote.stderr == "", remote
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
printf '%s\n' 'fzf-completion() { :; }' 'zle -N fzf-completion' 'fzf-cd-widget() { :; }' 'zle -N fzf-cd-widget' '__fzf_defaults() { print -r -- "$*"; }'
''')
        fzf.chmod(0o755)
        fd = executables / "fd"
        fd.write_text("#!/bin/sh\nexit 0\n")
        fd.chmod(0o755)
        enabled = subprocess.run([*shell, probe + '''
(( $+widgets[fzf-file-widget-toggle] )) || exit 14
[[ $(bindkey '^G') == *fzf-completion* ]] || exit 15
[[ $(bindkey '^[w') == *zworktree* ]] || exit 16
[[ $(bindkey '^B') == *zzz* ]] || exit 17
TMUX=fixture
source "$HOME/.local/share/zsh/tmux-auto-title.zsh"
mkdir -p "$HOME/selected/next"
_fixture_title=zsh
_fixture_auto=""
tmux() {
    case "$*" in
        *'#{window_index}'*) print 0 ;;
        *'#{pane_active}'*) print 1 ;;
        *'#{window_name}'*) print -r -- "$_fixture_title" ;;
        *'@auto_titled_name') print -r -- "$_fixture_auto" ;;
        rename-window*) _fixture_title="$4" ;;
        set-option*) _fixture_auto="$4" ;;
    esac
}
zle() { :; }
zz() { builtin cd -- "$HOME/selected"; }
_tmux_last_cmd=vim
zzz || exit 18
[[ $_fixture_title == selected ]] || exit 19
_fixture_title=review
zz() { builtin cd -- "$HOME/selected/next"; }
zzz || exit 20
[[ $_fixture_title == review ]] || exit 21
_tmux_last_cmd=vim
zz() { return 130; }
zzz
[[ $? == 130 && $_tmux_last_cmd == vim && $_fixture_title == review ]] || exit 22
'''], cwd=home, env=env, capture_output=True, text=True, timeout=15)
        assert enabled.returncode == 0, enabled.stderr
        assert enabled.stdout == "READY\n" and enabled.stderr == "", enabled
        assert (home / ".zsh/cache/fzf-init.zsh").is_file()
        test_transient_prompt(temporary, env, executables)
        print("PASS: noninteractive remote Zsh resolves installed Intent and its approval endpoint; "
              "partial zsh setup starts silently; installed fzf activates its widgets; "
              "Ctrl-B updates automatic tmux titles after Vim and preserves manual names and cancellation "
              "(controlled tmux and ZLE boundaries); native Zsh collapses accepted prompts and shows failures.")


if __name__ == "__main__":
    main()
