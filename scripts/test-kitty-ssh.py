#!/usr/bin/env python3
"""Prepare remote terminfo, then connect through kssh; the transport is a fixture."""
from pathlib import Path
import os
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="kitty-ssh-") as directory:
        remote_home = Path(directory) / "remote"
        remote_home.mkdir()
        subprocess.run(
            ["make", "-s", "-C", str(root), "kitty-terminfo", f"HOME={remote_home}"],
            check=True,
        )
        fixture = Path(directory) / "bin"
        fixture.mkdir()
        kitten = fixture / "kitten"
        kitten.write_text(
            '#!/bin/bash\nset -e\n'
            '[ "$#" = 4 ] && [ "$1" = ssh ] && [ "$2" = -p ] && '
            '[ "$3" = 2222 ] && [ "$4" = fixture-host ]\n'
            'infocmp -A "$REMOTE_HOME/.terminfo" xterm-kitty >/dev/null\n'
            'TERMINFO="$REMOTE_HOME/.terminfo" TERM=xterm-kitty tput colors\n'
        )
        kitten.chmod(0o755)
        result = subprocess.run(
            ["/bin/bash", "-c", 'source "$1"; kssh -p 2222 fixture-host',
             "bash", str(root / "sh/functions")],
            env={
                **os.environ,
                "PATH": f"{fixture}:/usr/bin:/bin",
                "KITTY_WINDOW_ID": "fixture",
                "REMOTE_HOME": str(remote_home),
            },
            capture_output=True, text=True, check=True,
        )
        assert result.stdout.strip() == "256", result.stdout + result.stderr
        print("PASS: kssh preserves SSH arguments and the prepared remote recognizes xterm-kitty.")


if __name__ == "__main__":
    main()
