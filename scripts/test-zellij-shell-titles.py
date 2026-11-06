#!/usr/bin/env python3
"""Exercise installed cd/Ctrl-B tab titles in an isolated native Zellij session."""

import importlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


workflow = importlib.import_module("test-zellij")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


def main():
    binary, shell = shutil.which("zellij"), shutil.which("zsh")
    assert binary and shell, "Install Zellij and Zsh before testing shell tab titles"
    with tempfile.TemporaryDirectory(prefix="zj-shell-titles-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        home, runtime, selection = work / "home", work / "run", work / "project" / "child"
        home.mkdir()
        runtime.mkdir(mode=0o700)
        selection.mkdir(parents=True)
        subprocess.run(["git", "init", "-b", "main", str(selection.parent)],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(selection.parent), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "fixture"],
                       capture_output=True, check=True)
        env = {**os.environ, "HOME": str(home), "SHELL": shell,
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_CACHE_HOME": str(work / "cache"),
               "XDG_DATA_HOME": str(work / "data"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(work),
               "SSH_CONNECTION": "isolated-title-test", "TITLE_SELECTION": str(selection),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV", "ZDOTDIR"):
            env.pop(key, None)
        # Isolate host-wide startup (including compinit) while retaining the
        # installed user configuration in every shell, including new splits.
        zdot = work / "zdot"
        zdot.mkdir()
        (zdot / ".zshenv").write_text('unsetopt GLOBAL_RCS\nsource "$HOME/.zshenv"\n')
        (zdot / ".zshrc").write_text('source "$HOME/.zshrc"\n')
        env["ZDOTDIR"] = str(zdot)
        (home / ".files").symlink_to(ROOT)
        subprocess.run(["make", "--no-print-directory", "zsh-config", "zellij"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        # Simulate an existing shell installation being upgraded via make zellij.
        (home / ".local/share/zsh/zellij-auto-title.zsh").unlink()
        subprocess.run(["make", "--no-print-directory", "zellij"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        shell_config = home / ".zshrc"
        configured = shell_config.read_text()
        shell_config.unlink()
        shell_config.write_text(configured + "\nPS1=" + shlex.quote(PROMPT.decode()) + "\n"
                                '_title_test_prompt_done() {\n'
                                '  [[ -z "$TITLE_PROOF" ]] || touch "$TITLE_PROOF"\n'
                                '}\nadd-zsh-hook precmd _title_test_prompt_done\n')
        # Only picker selection is simulated. The installed key binding, zz,
        # shell cd hooks and native tab names are exercised end to end.
        tools = home / ".local/bin"
        fzf = tools / "fzf"
        fzf.write_text('''#!/bin/sh
[ "$*" = --zsh ] || exit 1
printf '%s\n' 'fzf-completion() { :; }' 'zle -N fzf-completion' '__fzf_defaults() { print -r -- "$*"; }'
''')
        fzf.chmod(0o755)
        fd = tools / "fd"
        fd.write_text("#!/bin/sh\nexit 0\n")
        fd.chmod(0o755)
        picker = tools / "sk"
        picker.write_text('#!/bin/sh\ncat >/dev/null\nprintf "%s\\n" "$TITLE_SELECTION"\n')
        picker.chmod(0o755)
        config = work / "config.kdl"
        config.write_text('default_mode "locked"\nshow_startup_tips false\n'
                          'show_release_notes false\nsession_serialization false\n')
        layout = work / "layout.kdl"
        layout.write_text("layout { pane; }\n")
        name = "shell-" + work.name
        terminal = Terminal(binary, env, name, [
            binary, "--config", str(config), "--new-session-with-layout", str(layout),
            "--session", name,
        ], install_navigation=False)
        try:
            terminal.until("the installed shell names its initial tab", lambda:
                           PROMPT in terminal.output and terminal.tabs()[0]["name"] == "home")
            tab_id = terminal.tabs()[0]["tab_id"]

            def title():
                return next(tab["name"] for tab in terminal.tabs() if tab["tab_id"] == tab_id)

            terminal.send(("cd " + shlex.quote(str(selection.parent)) + "\r").encode())
            terminal.until("cd adds the directory and branch", lambda: title() == "project [main]")
            terminal.send(b"git switch -c topic\r")
            terminal.until("the prompt notices branch changes", lambda: title() == "project [topic]")
            terminal.send(b"\x02")
            terminal.until("Ctrl-B renames the tab after selecting a directory", lambda:
                           title() == "child [topic]")
            original = terminal.terminals()[0]["id"]
            terminal.action("new-pane", "--direction", "right", "--cwd", str(home), "--", shell)
            terminal.until("a new active shell takes over the shared automatic title", lambda:
                           len(terminal.terminals()) == 2 and title() == "home")
            proof = home / "inactive-done"
            terminal.action("write-chars", "--pane-id", str(original),
                            "cd " + shlex.quote(str(selection.parent)) + "; TITLE_PROOF=" + shlex.quote(str(proof)) + "\r")
            terminal.until("the inactive shell finishes its directory change", proof.exists)
            assert title() == "home", "An inactive split stole the tab title"
            terminal.action("rename-tab", "--tab-id", str(tab_id), "Review")
            terminal.send(("cd " + shlex.quote(str(selection)) + "; TITLE_PROOF=" + shlex.quote(str(home / "manual-done")) + "\r").encode())
            terminal.until("the explicitly named tab's shell finishes cd", (home / "manual-done").exists)
            assert title() == "Review", "An automatic title replaced the explicit name"
            print("PASS: installed cd/Ctrl-B hooks name tabs for directory and branch; "
                  "active splits share ownership and preserve explicit names.")
        finally:
            subprocess.run([binary, "kill-session", name], env=env,
                           capture_output=True, timeout=5)
            terminal.close()


if __name__ == "__main__":
    main()
