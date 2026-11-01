#!/usr/bin/env python3
"""One machine-config workflow: compose sets, inspect, override, reject a typo."""

import json
import io
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tarfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="dotfiles-config-") as temporary:
        home = Path(temporary)
        env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}
        for name in ("DOTFILES_CONFIG", "IS_EASYPOST", "BOOTSTRAP_MERMAID"):
            env.pop(name, None)
        command = [sys.executable, str(ROOT / "scripts/dotfiles-config.py")]

        def run(*args, check=True):
            return subprocess.run(args, cwd=ROOT, env=env, check=check,
                                  capture_output=True, text=True, timeout=30)

        baseline = json.loads(run(*command, "--format", "json").stdout)
        schema = json.loads(run(*command, "--format", "schema").stdout)
        assert json.loads((ROOT / "config/schema.json").read_text()) == schema, "Regenerate config/schema.json from the runtime definitions."
        assert baseline["settings"] == {
            "codex.github_enabled": False, "zellij.source": "patched", "bootstrap.mermaid": False,
        }
        config = home / ".config/dotfiles/config.toml"
        sets = config.parent / "sets"
        sets.mkdir(parents=True)
        (sets / "workstation.toml").write_text('sets = ["easypost", "zellij-main", "mermaid"]\n')
        config.write_text('sets = ["workstation"]\n[bootstrap]\nmermaid = false\n')
        selected = json.loads(run(*command, "--format", "json").stdout)
        assert selected["sets"] == ["base", "easypost", "zellij-main", "mermaid", "workstation"]
        assert selected["settings"] == {
            "codex.github_enabled": False, "zellij.source": "main", "bootstrap.mermaid": False,
        }
        assert selected["sources"]["bootstrap.mermaid"] == str(config)
        preview = tomllib.loads(run("make", "--no-print-directory", "config").stdout)
        assert preview["zellij"]["source"] == "main"

        # Exercise the real Make -> bootstrap -> installer path. Only compilation
        # and release downloads are fixtures; the installed binaries and source
        # transitions are observable outputs of the real installers.
        executables = home / "fixture"
        executables.mkdir()
        release = b'#!/bin/sh\necho "zellij 0.45.1"\n'
        with tarfile.open(executables / "release.tar.gz", "w:gz") as archive:
            member = tarfile.TarInfo("zellij")
            member.mode = 0o755
            member.size = len(release)
            archive.addfile(member, io.BytesIO(release))
        (executables / "release.sha256sum").write_text(hashlib.sha256(release).hexdigest() + "  target/zellij\n")
        driver = executables / "driver"
        driver.write_text(f"#!{sys.executable}\n" + r'''
import os
from pathlib import Path
import shutil
import sys
home = Path(os.environ["HOME"])
args = sys.argv[1:]
name = Path(sys.argv[0]).name
if name == "rustup":
    assert args == ["toolchain", "install", "1.95.0", "--profile", "minimal"], args
elif name == "cargo":
    assert args[:2] == ["+1.95.0", "install"] and "--locked" in args, args
    assert args[args.index("--rev") + 1] == "bf517077c848d91f75091f66d1996cfeb84f4732", args
    destination = Path(args[args.index("--root") + 1]) / "bin/zellij"
    destination.parent.mkdir(parents=True)
    destination.write_text('#!/bin/sh\necho "zellij 0.46.0"\n')
    destination.chmod(0o755)
elif name == "curl":
    url = args[1]
    assert url.startswith("https://github.com/zellij-org/zellij/releases/download/v0.45.1/zellij-"), url
    source = "release.sha256sum" if url.endswith(".sha256sum") else "release.tar.gz"
    shutil.copyfile(home / "fixture" / source, args[args.index("-o") + 1])
else:
    raise AssertionError(sys.argv)
''')
        driver.chmod(0o755)
        for name in ("rustup", "cargo", "curl"):
            (executables / name).symlink_to(driver)
        env["PATH"] = f"{executables}:{env['PATH']}"
        run("make", "--no-print-directory", "zellij-runtime")
        installed = home / ".local/bin/zellij"
        assert run(str(installed), "--version").stdout.strip() == "zellij 0.46.0"

        # A later set overrides earlier sets, and explicit local values win.
        config.write_text('sets = ["easypost", "personal", "zellij-release"]\n[codex]\ngithub_enabled = false\n')
        overridden = tomllib.loads(run(*command).stdout)
        assert overridden["codex"]["github_enabled"] is False
        assert overridden["zellij"]["source"] == "release"
        run("make", "--no-print-directory", "zellij-runtime")
        assert run(str(installed), "--version").stdout.strip() == "zellij 0.45.1"

        # An explicit alternate config is also shared by Make and bootstrap.
        alternate = home / "personal.toml"
        alternate.write_text('sets = ["personal", "zellij-main"]\n')
        explicit = run("make", "--no-print-directory", "config", f"DOTFILES_CONFIG={alternate}")
        assert tomllib.loads(explicit.stdout)["codex"]["github_enabled"] is True
        permissions = run("make", "--no-print-directory", "-n", "codex-permissions", f"DOTFILES_CONFIG={alternate}")
        assert '--github-enabled "true"' in permissions.stdout
        run("make", "--no-print-directory", "zellij-runtime", f"DOTFILES_CONFIG={alternate}")
        assert run(str(installed), "--version").stdout.strip() == "zellij 0.46.0"
        env["DOTFILES_CONFIG"] = os.path.relpath(alternate, ROOT)
        propagated = run("bash", "-ec", 'source ./bootstrap.sh; load_dotfiles_config; cd /; python3 "$1/scripts/dotfiles-config.py"', "config-test", str(ROOT))
        assert tomllib.loads(propagated.stdout)["codex"]["github_enabled"] is True
        env.pop("DOTFILES_CONFIG")
        config.write_text('sets = ["typo"]\n')
        before = installed.read_bytes()
        rejected = run("make", "--no-print-directory", "zellij-runtime", check=False)
        assert rejected.returncode != 0 and "unknown configuration set 'typo'" in rejected.stderr
        assert installed.read_bytes() == before
        print("PASS: Make and bootstrap compose explicit sets, install the selected Zellij source, and reject unknown sets.")


if __name__ == "__main__":
    main()
