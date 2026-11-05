#!/usr/bin/env python3
"""Exercise zj and zssh through their shell entrypoints with simulated transports."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent


def main():
    zsh = shutil.which("zsh")
    if not zsh:
        raise SystemExit("Missing dependency: zsh. Install it and rerun make test-zellij-attach.")
    with tempfile.TemporaryDirectory(prefix="zj-attach-") as temporary:
        work = Path(temporary)
        proxy = work / "zellij"
        proxy.write_text(f"#!{sys.executable}\n" + '''
import json
import os
from pathlib import Path
import subprocess
import sys

args = sys.argv[1:]
if args == ["setup", "--check"]:
    print("[CACHE DIR]: " + str(Path(os.environ["HOME"]) / "zellij-cache"))
    raise SystemExit(0)
if args[:2] == ["action", "new-tab"]:
    Path(os.environ["TAB"]).write_text(json.dumps(args[:args.index("--")]))
    raise SystemExit(subprocess.run(args[args.index("--") + 1:]).returncode)
if os.environ.get("ATTACH_FAIL"):
    print("attachment failed", file=sys.stderr)
    raise SystemExit(17)
Path(os.environ["ATTACHED"]).write_text(json.dumps(args))
Path(os.environ["ATTACHED_ENV"]).write_text(json.dumps({
    "tty": os.isatty(0), "socket": os.environ.get("SSH_AUTH_SOCK"),
}))
''')
        proxy.chmod(0o755)
        ssh = work / "ssh"
        ssh.write_text(f"#!{sys.executable}\n" + '''
import errno
import os
import pty
import sys

assert sys.argv[1:3] == ["-t", "fixture-host"], sys.argv
# SSH starts a noninteractive remote shell, without the local session or PATH.
env = dict(os.environ)
env.pop("ZELLIJ", None)
env["HOME"] = env.pop("REMOTE_HOME")
env["ZDOTDIR"] = env["HOME"]
env["SHELL"] = env.pop("REMOTE_SHELL")
env["SSH_CONNECTION"] = "127.0.0.1 1234 127.0.0.1 22"
env["SSH_AUTH_SOCK"] = env.pop("REMOTE_AUTH_SOCK")
env["PATH"] = os.defpath
# -t supplies the controlling terminal needed by an interactive login shell.
pid, terminal = pty.fork()
if pid == 0:
    os.execve(env["SHELL"], [env["SHELL"], "-c", sys.argv[3]], env)
while True:
    try:
        output = os.read(terminal, 65536)
        if not output:
            break
        os.write(1, output)
    except OSError as error:
        if error.errno != errno.EIO:
            raise
        break
os.close(terminal)
_, status = os.waitpid(pid, 0)
raise SystemExit(os.waitstatus_to_exitcode(status))
''')
        ssh.chmod(0o755)
        home = work / "home"
        home.mkdir()
        remote_home = work / "remote-home"
        runtime = remote_home / "custom tools/bin"
        runtime.mkdir(parents=True)
        (runtime / "zellij").symlink_to(proxy)
        (remote_home / ".files").symlink_to(ROOT)
        remote_bin = remote_home / ".local/bin"
        remote_bin.mkdir(parents=True)
        (remote_bin / "zellij-attach").symlink_to(ROOT / "bin/zellij-attach")
        (remote_bin / "zellij-agent").symlink_to(ROOT / "bin/zellij-agent")
        # Isolate runner-wide startup (including Ubuntu's interactive compinit)
        # while still exercising the repository's real user startup files.
        (remote_home / ".zshenv").write_text(
            'unsetopt GLOBAL_RCS\nsource "$HOME/.files/zsh/zshenv"\n'
        )
        for source, destination in (
            ("sh/profile", ".profile"), ("sh/alias", ".alias"),
            ("zsh/zshrc", ".zshrc"),
            ("zsh/zlogin", ".zlogin"), ("bash/bashrc", ".bashrc"),
            ("bash/bashprofile", ".bash_profile"),
        ):
            (remote_home / destination).symlink_to(ROOT / source)
        (remote_home / ".env").write_text('export PATH="$HOME/custom tools/bin:$PATH"\n')
        attached, observed, tab = work / "attached", work / "environment", work / "tab"
        forwarded_socket = str(work / "forwarded.sock")
        env = {
            **os.environ,
            "HOME": str(home),
            "REMOTE_HOME": str(remote_home),
            "REMOTE_SHELL": zsh,
            "REMOTE_AUTH_SOCK": forwarded_socket,
            "SHELL": "/bin/false",  # The launcher must select the remote shell.
            "TERM": "xterm-256color",
            "PATH": os.pathsep.join((str(work), str(ROOT / "bin"), os.environ["PATH"])),
            "ATTACHED": str(attached),
            "ATTACHED_ENV": str(observed),
            "TAB": str(tab),
        }
        for name in ("ZELLIJ", "TMUX", "KITTY_WINDOW_ID", "SSH_CONNECTION", "SSH_AUTH_SOCK"):
            env.pop(name, None)
        command = [
            shutil.which("bash"), "-c",
            'shopt -s expand_aliases; source "$1"; shift; eval \'zj "$@"\'',
            "zj-check", str(ROOT / "sh/alias"),
        ]

        subprocess.run(command, env=env, check=True, capture_output=True, text=True)
        assert json.loads(attached.read_text()) == ["attach", "--create", "main"]
        subprocess.run([*command, "chosen session"], env=env, check=True,
                       capture_output=True, text=True)
        assert json.loads(attached.read_text()) == ["attach", "--create", "chosen session"]

        attached.unlink()
        failed = subprocess.run(command, env={**env, "ATTACH_FAIL": "1"},
                                capture_output=True, text=True)
        assert failed.returncode == 17 and "attachment failed" in failed.stderr
        assert not attached.exists(), "Failed attachment must not start another session"
        nested = subprocess.run(command, env={**env, "ZELLIJ": "1"},
                                capture_output=True, text=True)
        assert nested.returncode != 0 and "already inside Zellij" in nested.stderr
        assert not attached.exists(), "Nested invocation must not attach or create a session"

        remote = [
            shutil.which("bash"), "-c", 'source "$1"; shift; zssh "$@"',
            "zssh-check", str(ROOT / "sh/functions"), "fixture-host",
        ]
        subprocess.run(remote, env=env, check=True, timeout=15)
        assert json.loads(attached.read_text()) == ["attach", "--create", "main"]
        assert json.loads(observed.read_text()) == {"tty": True, "socket": forwarded_socket}
        assert not tab.exists(), "Outside Zellij, SSH must use the current terminal"
        session = "chosen 'session; $(printf injected) $HOME"
        subprocess.run([zsh, "-dfc", *remote[2:], session], env=env, check=True,
                       timeout=15)
        assert json.loads(attached.read_text()) == ["attach", "--create", session]
        subprocess.run(remote, env={**env, "ZELLIJ": "1", "REMOTE_SHELL": shutil.which("bash")}, check=True,
                       timeout=15)
        assert json.loads(tab.read_text()) == ["action", "new-tab", "--name", "fixture-host"]
        assert json.loads(attached.read_text()) == ["attach", "--create", "main"]
        assert json.loads(observed.read_text()) == {"tty": True, "socket": forwarded_socket}
        print("PASS: zj and zssh preserve sessions; remote login shells supply PATH, TTY, and forwarded agents.")


if __name__ == "__main__":
    main()
