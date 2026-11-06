#!/usr/bin/env python3
"""Build and install the Zellij pane-navigation plugin."""

import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    source = Path(__file__).resolve().parent.parent / "zellij/navigation"
    home = Path.home()
    cache = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache"))
    cache = cache / "dotfiles/zellij-navigation"
    cache.mkdir(parents=True, exist_ok=True)
    toolchain, target = "1.95.0", "wasm32-wasip1"
    subprocess.run(["rustup", "toolchain", "install", toolchain, "--profile", "minimal"],
                   check=True)
    subprocess.run(["rustup", "target", "add", "--toolchain", toolchain, target], check=True)
    environment = {**os.environ, "CARGO_TARGET_DIR": str(cache / "target")}
    with (cache / "install.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        subprocess.run(["rustup", "run", toolchain, "cargo", "build", "--locked", "--release",
                        "--target", target, "--manifest-path", str(source / "Cargo.toml")],
                       env=environment, check=True)
        destination = home / ".local/share/zellij/plugins/pane-navigation.wasm"
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".navigation-", dir=destination.parent) as directory:
            staged = Path(directory) / destination.name
            shutil.copyfile(cache / "target" / target / "release/dotfiles-pane-navigation.wasm", staged)
            os.replace(staged, destination)
    print(f"Installed Zellij pane navigation: {destination}")


if __name__ == "__main__":
    main()
