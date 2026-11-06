#!/usr/bin/env python3
"""Exercise curl | sh against real Git/Make, with package installation simulated."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import threading


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="dotfiles-entrypoint-") as temporary:
        work = Path(temporary)
        home = work / "home with spaces"
        home.mkdir()
        source = work / "repository"
        source.mkdir()
        (source / "bootstrap.sh").write_text("# Fixture: package installation is simulated.\n")
        (source / "Makefile").write_text(
            f'bootstrap:\n\t@"{sys.executable}" "$(CURDIR)/fixture.py"\n'
        )
        (source / "fixture.py").write_text('''from pathlib import Path
import os
import sys
home = Path(os.environ["HOME"])
with (home / "bootstrap-calls").open("a") as calls:
    calls.write("bootstrap\\n")
assert not sys.stdin.read(), "bootstrap consumed bytes from the installer pipe"
if os.environ.get("FIXTURE_BOOTSTRAP_FAIL"):
    raise SystemExit(1)
config = home / ".config/dotfiles/config.toml"
config.parent.mkdir(parents=True, exist_ok=True)
if not config.exists():
    config.write_text('sets = ["linux"]\\n')
(home / "runtime-ready").touch()
''')
        environment = {
            **os.environ,
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            # Use the real clone path without requiring GitHub or touching a real home.
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"url.{source}.insteadOf",
            "GIT_CONFIG_VALUE_0": "https://github.com/lanej/dotfiles.git",
        }
        environment.pop("DOTFILES_CONFIG", None)
        subprocess.run(["git", "init", "-q", str(source)], env=environment, check=True)
        subprocess.run(["git", "-C", str(source), "add", "."], env=environment, check=True)
        subprocess.run(
            ["git", "-C", str(source), "-c", "user.name=Fixture", "-c",
             "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
             "commit", "-qm", "Installation fixture"], env=environment, check=True,
        )
        served = work / "http"
        served.mkdir()
        shutil.copyfile(root / "install.sh", served / "install.sh")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(served)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def install(extra=None):
            curl = subprocess.Popen(
                ["curl", "-fsSL", f"http://127.0.0.1:{server.server_port}/install.sh"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
            )
            result = subprocess.run(
                ["sh"], stdin=curl.stdout, capture_output=True, text=True,
                env={**environment, **(extra or {})},
            )
            curl.stdout.close()
            error = curl.stderr.read().decode()
            assert curl.wait() == 0, error
            curl.stderr.close()
            return result

        try:
            checkout = home / ".files"
            checkout.mkdir()
            occupied = checkout / "keep-me"
            occupied.write_text("existing user files")
            result = install()
            assert result.returncode != 0 and "Refusing to replace" in result.stderr, result
            assert occupied.read_text() == "existing user files"
            assert not (home / "bootstrap-calls").exists()
            # The user relocates the conflicting directory before retrying.
            checkout.rename(home / "saved-files")
            result = install()
            assert result.returncode == 0, result.stderr
            assert (home / "runtime-ready").exists()
            config = home / ".config/dotfiles/config.toml"
            assert config.read_text() == 'sets = ["linux"]\n'
            selection = 'sets = ["shell", "personal"]\n# Keep this machine selection.\n'
            config.write_text(selection)
            (checkout / "local-edit").write_text("preserve me")
            # A later upstream commit must not replace the existing checkout on rerun.
            (source / "upstream-change").write_text("not pulled")
            subprocess.run(["git", "-C", str(source), "add", "."], env=environment, check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Fixture", "-c",
                            "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                            "commit", "-qm", "Upstream change"], env=environment, check=True)
            result = install({"FIXTURE_BOOTSTRAP_FAIL": "1"})
            assert result.returncode != 0, result
            assert "bootstrap complete" not in result.stdout.lower()
            result = install()
            assert result.returncode == 0, result.stderr
            assert config.read_text() == selection
            assert (checkout / "local-edit").read_text() == "preserve me"
            assert not (checkout / "upstream-change").exists()
            assert (home / "bootstrap-calls").read_text() == "bootstrap\n" * 3
            assert "make install" in result.stdout
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    print("PASS: curl | sh clones, bootstraps, preserves local state on retry, and reports failure. Package installation was simulated.")


if __name__ == "__main__":
    main()
