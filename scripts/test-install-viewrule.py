#!/usr/bin/env python3
"""Check offline reuse and activation failures through the Viewrule installer."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="dotfiles-viewrule-install-") as temporary:
        scratch = Path(temporary)
        checkout = scratch / "checkout"
        (checkout / "scripts").mkdir(parents=True)
        (checkout / "claude/ui-review").mkdir(parents=True)
        installer = checkout / "scripts/install-viewrule.py"
        shutil.copyfile(root / "scripts/install-viewrule.py", installer)
        pin = json.loads((root / "claude/ui-review/tool.json").read_text())
        pin["url"] = "http://127.0.0.1:1/unavailable"
        (checkout / "claude/ui-review/tool.json").write_text(json.dumps(pin))
        install_root = scratch / "install"
        destination = install_root / "releases" / f'{pin["version"]}-{pin["sha256"][:12]}'
        package = destination / "node_modules/viewrule"
        package.mkdir(parents=True)
        metadata = {"name": "viewrule", "version": pin["version"]}
        (package / "package.json").write_text(json.dumps(metadata))
        binary = scratch / "bin"
        binary.mkdir()
        browser_log = scratch / "browser"
        node = binary / "node"
        node.write_text(
            f"#!{sys.executable}\n"
            "import os, pathlib, sys\n"
            "assert sys.argv[2:] == ['install-browser'], sys.argv\n"
            "assert sys.argv[1].endswith('/bin/viewrule.mjs'), sys.argv\n"
            "pathlib.Path(os.environ['BROWSER_LOG']).write_text('installed')\n"
            "sys.exit(int(os.environ.get('BROWSER_FAIL', '0')))\n"
        )
        node.chmod(0o755)
        env = {**os.environ, "VIEWRULE_INSTALL_ROOT": str(install_root),
               "PATH": f"{binary}:{os.environ['PATH']}", "BROWSER_LOG": str(browser_log)}

        def run(*args, environment=env):
            return subprocess.run([sys.executable, str(installer), *args],
                                  env=environment, capture_output=True, text=True)

        result = run()
        assert result.returncode == 0, result.stdout + result.stderr
        current = install_root / "current"
        assert current.resolve() == destination
        assert browser_log.read_text() == "installed"
        current.unlink()
        previous = scratch / "previous"
        previous.mkdir()
        current.symlink_to(previous)
        result = run(environment={**env, "BROWSER_FAIL": "1"})
        assert result.returncode != 0 and current.resolve() == previous
        (package / "package.json").write_text(json.dumps({**metadata, "version": "0.0.0"}))
        result = run("--skip-browser")
        assert result.returncode != 0 and "does not match" in result.stderr
        assert current.resolve() == previous
        archive = scratch / "bad.tgz"
        archive.write_bytes(b"unreviewed archive")
        result = run("--archive", str(archive), "--skip-browser",
                     environment={**env, "VIEWRULE_INSTALL_ROOT": str(scratch / "fresh")})
        assert result.returncode != 0 and "checksum differs" in result.stderr
        assert not (scratch / "fresh/current").exists()
        print("PASS: installed Viewrule is reused offline; browser, metadata and checksum failures preserve activation.")


if __name__ == "__main__":
    main()
