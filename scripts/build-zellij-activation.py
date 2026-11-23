#!/usr/bin/env python3
"""Build the unchanged curated Zellij base as an immutable installation."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def main():
    revision, toolchain, host = sys.argv[1:]
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "dotfiles/zellij"
    cache.mkdir(parents=True, exist_ok=True)
    with (cache / "activation-build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        source = Path.home() / "src/zellij"
        exists = subprocess.run(["git", "-C", str(source), "cat-file", "-e", revision + "^{commit}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not exists:
            source = cache / "sources.git"
            if not source.exists():
                subprocess.run(["git", "clone", "--bare", "--filter=blob:none",
                                "https://github.com/lanej/zellij.git", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "fetch", "--no-tags", "origin", revision], check=True)
        with tempfile.TemporaryDirectory(prefix="activation-build-", dir=cache) as temporary:
            work = Path(temporary)
            exported = work / "source"
            exported.mkdir()
            archive = work / "source.tar"
            with archive.open("wb") as output:
                subprocess.run(["git", "-C", str(source), "archive", revision],
                               stdout=output, check=True)
            with tarfile.open(archive) as content:
                content.extractall(exported, filter="data")
            stage = work / "installed"
            environment = {**os.environ,
                           "CARGO_TARGET_DIR": str(cache / "target" / (revision + "-curated"))}
            environment.pop("ZELLIJ_ACTIVATION_BUILD_ID", None)
            subprocess.run(["rustup", "run", toolchain, "cargo", "install", "--path", str(exported),
                            "--locked", "--root", str(stage), "--target", host,
                            "--no-default-features",
                            "--features", "plugins_from_target,vendored_curl,web_server_capability",
                            "--bin", "zellij"], env=environment, check=True)
            helper = Path(__file__).with_name("zellij-artifacts.py")
            subprocess.run([sys.executable, str(helper), "runtime", str(stage / "bin/zellij")],
                           check=True)
            runtime = (Path.home() / ".local/bin/zellij").resolve()
            receipt = {"schema_version": 1, "base_revision": revision, "activation_patch": None,
                       "toolchain": toolchain, "host": host,
                       "sha256": hashlib.sha256(runtime.read_bytes()).hexdigest()}
            selected = runtime.parent / "build.json"
            if selected.exists() and json.loads(selected.read_text()) != receipt:
                raise ValueError("Preserving a changed immutable runtime build receipt")
            if not selected.exists():
                selected.write_text(json.dumps(receipt) + "\n")
                selected.chmod(0o444)


if __name__ == "__main__":
    main()
