"""Install the dotfiles Copydesk pin in the active Neovim profile."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "copydesk"
REMOTE = "https://github.com/lanej/copydesk.git"


def git(plugin, *args):
    return subprocess.check_output(["git", "-C", str(plugin), *args], text=True).strip()


def installed_revision(plugin):
    if not plugin.exists() and not plugin.is_symlink():
        return None
    if plugin.is_symlink() or not (plugin / ".git").is_dir():
        raise ValueError(f"Preserving unmanaged Copydesk directory: {plugin}")
    if git(plugin, "config", "--local", "--get", "remote.origin.url") != REMOTE:
        raise ValueError(f"Preserving Copydesk checkout with a different origin: {plugin}")
    if git(plugin, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(f"Preserving Copydesk checkout with local edits: {plugin}")
    return git(plugin, "rev-parse", "HEAD")


def build(lazy_root, pin):
    if not (lazy_root / "lazy.nvim/lua/lazy/init.lua").is_file():
        raise ValueError("Install the dotfiles Neovim profile before updating Copydesk")
    # Lazy writes its resolved plugin set to the lockfile. Give the targeted
    # install a private copy so it cannot shrink the workstation's plugin lock.
    with tempfile.TemporaryDirectory(prefix="copydesk-update-") as scratch:
        lockfile = Path(scratch) / "lazy-lock.json"
        lockfile.write_text(json.dumps({PLUGIN: pin}))
        env = {**os.environ, "XDG_STATE_HOME": scratch, "XDG_CACHE_HOME": scratch}
        # Lazy checks out a plugin distribution, which does not need the
        # source-code guidance that the workstation hydrates in source checkouts.
        count = int(env.get("GIT_CONFIG_COUNT", "0"))
        env.update({
            "GIT_CONFIG_COUNT": str(count + 1),
            f"GIT_CONFIG_KEY_{count}": "hook.source-code-checkout.enabled",
            f"GIT_CONFIG_VALUE_{count}": "false",
        })
        subprocess.run([
            "nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n",
            "-l", str(ROOT / "scripts/project_update_copydesk.lua"),
            str(ROOT / "nvim/lua/copydesk-spec.lua"), str(lazy_root), str(lockfile),
        ], env=env, check=True, timeout=120)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "status", "inventory", "checkpoint", "restart", "restore", "verify"))
    action = parser.parse_args().action
    pin = json.loads((ROOT / "nvim/lazy-lock.json").read_text())[PLUGIN]
    expected = pin["commit"]
    if not re.fullmatch(r"[a-f0-9]{40}", expected):
        raise ValueError("Copydesk requires a full Git commit in the Neovim lockfile")
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    lazy_root = data / (os.environ.get("NVIM_APPNAME") or "nvim") / "lazy"
    plugin = lazy_root / PLUGIN
    revision = installed_revision(plugin)
    if revision == expected:
        for file in ("lua/copydesk.lua", "copydesk_schema.json"):
            if not (plugin / file).is_file():
                raise ValueError(f"Copydesk runtime file is missing: {plugin / file}")
    if action == "build":
        if revision != expected:
            build(lazy_root, pin)
            if installed_revision(plugin) != expected:
                raise ValueError("Copydesk installation did not match the locked revision")
        return 0
    if action == "status":
        print(json.dumps({"installed_revision": revision, "selected_revision": expected, "running_revision": None}))
        return 0
    target = {
        "target": "local",
        "expected_identity": expected,
        "running_identity": revision,
        "ready": revision == expected,
        "process": None,
        "sessions": [],
        "reason": "Copydesk is loaded by new Neovim processes" if revision == expected else "Build the locked Copydesk revision first",
    }
    print(json.dumps({"schema_version": 1, "targets": [target]}))
    return 0 if target["ready"] or action == "inventory" else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, KeyError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(f"copydesk: {error}")
