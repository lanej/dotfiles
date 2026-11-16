#!/usr/bin/env python3
"""Exercise GitHub credential lookup through Git with a restricted caller PATH."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    git = shutil.which("git")
    assert git, "Install Git before running the credential detector."
    with tempfile.TemporaryDirectory(prefix="git-credentials-") as temporary:
        home = Path(temporary)
        managed = home / ".local/bin"
        managed.mkdir(parents=True)
        caller = home / "caller-bin"
        caller.mkdir()
        restricted = home / "restricted-bin"
        restricted.mkdir()
        for directory, identity in ((managed, "managed"), (caller, "caller")):
            gh = directory / "gh"
            gh.write_text(
                "#!/bin/sh\n"
                '[ "$1" = auth ] && [ "$2" = git-credential ] && [ "$3" = get ] || exit 97\n'
                'while IFS= read -r line && [ -n "$line" ]; do\n'
                '  printf "%s\\n" "$line" >> "$CREDENTIAL_REQUEST"\n'
                'done\n'
                f'printf "username={identity}\\npassword=fixture-only\\n\\n"\n'
            )
            gh.chmod(0o755)
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(
            HOME=str(home),
            GIT_CONFIG_GLOBAL=str(ROOT / "git/gitconfig"),
            GIT_CONFIG_NOSYSTEM="1",
            GIT_TERMINAL_PROMPT="0",
            CREDENTIAL_REQUEST=str(home / "request"),
        )
        for host in ("github.com", "gist.github.com"):
            for path, identity in ((str(restricted), "managed"), (str(caller), "caller")):
                request = home / "request"
                request.unlink(missing_ok=True)
                result = subprocess.run(
                    [git, "credential", "fill"],
                    input=f"protocol=https\nhost={host}\n\n",
                    env={**env, "PATH": path},
                    cwd=home,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                assert result.returncode == 0, result.stderr
                credentials = dict(line.split("=", 1) for line in result.stdout.splitlines())
                assert credentials["username"] == identity, "Unexpected credential helper selected"
                assert credentials["password"] == "fixture-only"
                assert set(request.read_text().splitlines()) == {"protocol=https", f"host={host}"}
        print("PASS: GitHub and Gist credentials use managed gh without a shell PATH and retain caller PATH precedence.")


if __name__ == "__main__":
    main()
