#!/usr/bin/env python3
"""Build and atomically install the dotfiles-owned Zellij copy-hop plugin."""

import fcntl
import os
from pathlib import Path
import subprocess


def main():
    source = Path(__file__).resolve().parent.parent / "zellij/copy-hop"
    home = Path.home()
    cache = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache"))
    cache = cache / "dotfiles/zellij-copy-hop"
    cache.mkdir(parents=True, exist_ok=True)
    toolchain, target = "1.95.0", "wasm32-wasip1"
    subprocess.run(["rustup", "toolchain", "install", toolchain, "--profile", "minimal"],
                   check=True)
    subprocess.run(["rustup", "target", "add", "--toolchain", toolchain, target], check=True)
    with (cache / "install.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        destination = home / ".local/share/zellij/plugins/copy-hop.wasm"
        subprocess.run(["python3", str(Path(__file__).with_name("zellij-artifacts.py")),
                        "plugin", "dotfiles-copy-hop", str(source), str(cache / "target"),
                        str(destination)], check=True)
    print(f"Installed Zellij copy-hop: {destination}")


if __name__ == "__main__":
    main()
