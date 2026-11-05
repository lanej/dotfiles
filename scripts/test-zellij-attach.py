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
if args[:2] == ["action", "new-tab"]:
    Path(os.environ["TAB"]).write_text(json.dumps(args[:args.index("--")]))
    raise SystemExit(subprocess.run(args[args.index("--") + 1:]).returncode)
if os.environ.get("ATTACH_FAIL"):
    print("attachment failed", file=sys.stderr)
    raise SystemExit(17)
Path(os.environ["ATTACHED"]).write_text(json.dumps(args))
''')
        proxy.chmod(0o755)
        ssh = work / "ssh"
        ssh.write_text(f"#!{sys.executable}\n" + '''
import os
import subprocess
import sys

assert sys.argv[1:3] == ["-t", "fixture-host"], sys.argv
# SSH starts a noninteractive remote shell, without the local session or PATH.
env = dict(os.environ)
env.pop("ZELLIJ", None)
env["HOME"] = env.pop("REMOTE_HOME")
env["PATH"] = os.defpath
raise SystemExit(subprocess.run(["/bin/sh", "-c", sys.argv[3]], env=env).returncode)
''')
        ssh.chmod(0o755)
        home = work / "home"
        home.mkdir()
        remote_home = work / "remote user's home"
        (remote_home / ".local/bin").mkdir(parents=True)
        (remote_home / ".local/bin/zellij").symlink_to(proxy)
        attached, tab = work / "attached", work / "tab"
        env = {
            **os.environ,
            "HOME": str(home),
            "REMOTE_HOME": str(remote_home),
            "PATH": os.pathsep.join((str(work), str(ROOT / "bin"), os.environ["PATH"])),
            "ATTACHED": str(attached),
            "TAB": str(tab),
        }
        for name in ("ZELLIJ", "KITTY_WINDOW_ID", "SSH_CONNECTION", "SSH_AUTH_SOCK"):
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
        subprocess.run(remote, env=env, check=True, capture_output=True, text=True)
        assert json.loads(attached.read_text()) == ["attach", "--create", "main"]
        assert not tab.exists(), "Outside Zellij, SSH must use the current terminal"
        subprocess.run([*remote, "chosen 'session"], env=env, check=True,
                       capture_output=True, text=True)
        assert json.loads(attached.read_text()) == ["attach", "--create", "chosen 'session"]
        subprocess.run(remote, env={**env, "ZELLIJ": "1"}, check=True,
                       capture_output=True, text=True)
        assert json.loads(tab.read_text()) == ["action", "new-tab", "--name", "fixture-host"]
        assert json.loads(attached.read_text()) == ["attach", "--create", "main"]
        print("PASS: zj and zssh default to main, preserve explicit names, and retain launcher safeguards.")


if __name__ == "__main__":
    main()
