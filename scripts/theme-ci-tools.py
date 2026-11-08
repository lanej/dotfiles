#!/usr/bin/env python3
"""Install pinned native fixture tools into a disposable CI directory."""

import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    system, machine = platform.system(), platform.machine()
    targets = {("Linux", "x86_64"): ("x86_64-unknown-linux-gnu", "linux_amd64", "Linux_x86_64", "linux-x86_64"), ("Darwin", "arm64"): ("aarch64-apple-darwin", "darwin_arm64", "Darwin_arm64", "macos-arm64"), ("Darwin", "x86_64"): ("x86_64-apple-darwin", "darwin_amd64", "Darwin_x86_64", "macos-x86_64")}
    triple, fzf_platform, glow_platform, nvim_platform = targets[system, machine]
    releases = [
        ("sharkdp/bat", "v0.26.1", f"bat-v0.26.1-{triple}.tar.gz", "bat"),
        ("dandavison/delta", "0.20.1", f"delta-0.20.1-{triple}.tar.gz", "delta"),
        ("ClementTsang/bottom", "0.15.0", f"bottom_{triple}.tar.gz", "btm"),
        ("charmbracelet/glow", "v3.0.0", f"glow_3.0.0_{glow_platform}.tar.gz", "glow"),
        ("junegunn/fzf", "v0.59.0", f"fzf-0.59.0-{fzf_platform}.tar.gz", "fzf"),
        ("neovim/neovim", "v0.12.6", f"nvim-{nvim_platform}.tar.gz", "nvim"),
    ]
    binaries = destination / "bin"
    binaries.mkdir(exist_ok=True)
    for repo, tag, asset, executable in releases:
        with tempfile.TemporaryDirectory(prefix="download-", dir=destination) as directory:
            work = Path(directory)
            archive = work / "release.tar.gz"
            urllib.request.urlretrieve(f"https://github.com/{repo}/releases/download/{tag}/{asset}", archive)
            with tarfile.open(archive) as package:
                package.extractall(work, filter="data")
            if executable == "nvim":
                installation = destination / "neovim"
                shutil.copytree(work / f"nvim-{nvim_platform}", installation, dirs_exist_ok=True)
                (binaries / "nvim").symlink_to(installation / "bin/nvim")
            else:
                binary = next(p for p in work.rglob(executable) if p.is_file())
                shutil.copy2(binary, binaries / executable)
                (binaries / executable).chmod(0o755)
    locks = json.loads((ROOT / "nvim/lazy-lock.json").read_text())
    for plugin, repo in {"gitsigns.nvim": "lewis6991/gitsigns.nvim", "lualine.nvim": "nvim-lualine/lualine.nvim", "fzf-lua": "ibhagwan/fzf-lua"}.items():
        path = destination / "plugins" / plugin
        path.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "fetch", "-q", "--depth=1", f"https://github.com/{repo}", locks[plugin]["commit"]], check=True)
        subprocess.run(["git", "-C", str(path), "checkout", "-q", "--detach", "FETCH_HEAD"], check=True)


if __name__ == "__main__":
    main()
