#!/usr/bin/env python3
"""Exercise zj through its shell alias with Zellij's CLI boundary simulated."""

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
import sys

if sys.argv[1:2] == ["list-sessions"]:
    if os.environ.get("LIST_FAIL"):
        print("session discovery failed", file=sys.stderr)
        raise SystemExit(1)
    lines = Path(os.environ["LISTING"]).read_text().splitlines()
    if "--reverse" in sys.argv:
        lines.reverse()
    print("\\n".join(lines))
else:
    Path(os.environ["ATTACHED"]).write_text(json.dumps(sys.argv[1:]))
''')
        proxy.chmod(0o755)
        listing, attached = work / "listing", work / "attached"
        env = {
            **os.environ,
            "PATH": os.pathsep.join((str(work), str(ROOT / "bin"), os.environ["PATH"])),
            "LISTING": str(listing),
            "ATTACHED": str(attached),
        }
        command = [
            shutil.which("bash"), "-c",
            'shopt -s expand_aliases; source "$1"; shift; eval \'zj "$@"\'',
            "zj-check", str(ROOT / "sh/alias"),
        ]

        listing.write_text(
            "older [Created 4s ago] \n"
            "new regular [Created 3s ago] \n"
            "exited [Created 2s ago] (EXITED - attach to resurrect)\n"
            "dotfiles-popup [Created 1s ago] \n"
        )
        subprocess.run(command, env=env, check=True, capture_output=True, text=True)
        assert json.loads(attached.read_text()) == ["attach", "new regular"]

        listing.write_text("dotfiles-popup [Created 1s ago] \n")
        subprocess.run(command, env=env, check=True, capture_output=True, text=True)
        assert json.loads(attached.read_text()) == []

        subprocess.run([*command, "chosen session"], env=env, check=True,
                       capture_output=True, text=True)
        assert json.loads(attached.read_text()) == ["attach", "--create", "chosen session"]

        attached.unlink()
        failed = subprocess.run(command, env={**env, "LIST_FAIL": "1"},
                                capture_output=True, text=True)
        assert failed.returncode != 0 and "session discovery failed" in failed.stderr
        assert not attached.exists(), "Failed discovery must not start another session"
        print("PASS: zj selects a regular session, creates when needed, forwards names, and preserves discovery failures.")


if __name__ == "__main__":
    main()
