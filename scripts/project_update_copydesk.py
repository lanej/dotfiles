"""Install the fetched Copydesk main revision in the active Neovim profile."""
import argparse
import json
import os
from pathlib import Path
import shutil
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
    settings = json.loads(subprocess.check_output(
        [sys.executable, str(ROOT / "scripts/dotfiles-config.py"), "--format", "json"], text=True,
    ))["settings"]
    if not settings["tools.neovim"]:
        if action == "status":
            print(json.dumps({"activation": "not-applicable", "reason": "Neovim is disabled"}))
        elif action != "build":
            identity = "copydesk:neovim-disabled"
            print(json.dumps({"schema_version": 1, "targets": [{
                "target": "local", "expected_identity": identity, "running_identity": identity,
                "ready": True, "process": None, "sessions": [], "reason": "Neovim is disabled",
            }]}))
        else:
            print("copydesk: Neovim is disabled; skipping plugin installation", file=sys.stderr)
        return 0

    source = Path.cwd()
    origin = git(source, "config", "--local", "--get", "remote.origin.url")
    if origin not in {REMOTE, REMOTE.removesuffix(".git"), "git@github.com:lanej/copydesk.git",
                      "ssh://git@github.com/lanej/copydesk.git"}:
        raise ValueError(f"Expected the upstream Copydesk checkout: {source}")
    expected = git(source, "rev-parse", "--verify", "refs/remotes/origin/main^{commit}")
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    lazy_root = data / (os.environ.get("NVIM_APPNAME") or "nvim") / "lazy"
    plugin = lazy_root / PLUGIN
    editor_available = shutil.which("nvim") is not None and (lazy_root / "lazy.nvim/lua/lazy/init.lua").is_file()
    prerequisites = "Install Neovim and the profile’s lazy.nvim before updating Copydesk"
    revision = installed_revision(plugin)
    if revision == expected:
        for file in ("lua/copydesk.lua", "copydesk_schema.json"):
            if not (plugin / file).is_file():
                raise ValueError(f"Copydesk runtime file is missing: {plugin / file}")
    if action == "build":
        if not editor_available:
            raise ValueError(prerequisites)
        if revision != expected:
            build(lazy_root, {"branch": "main", "commit": expected})
            if installed_revision(plugin) != expected:
                raise ValueError("Copydesk installation did not match the fetched main revision")
        return 0
    if action == "status":
        print(json.dumps({
            "installed_revision": revision, "selected_revision": expected,
            "running_revision": None, "editor_available": editor_available,
        }))
        return 0
    ready = editor_available and revision == expected
    target = {
        "target": "local",
        "expected_identity": expected,
        "running_identity": revision,
        "ready": ready,
        "process": None,
        "sessions": [],
        "reason": ("Copydesk is available to new Neovim processes" if ready else
                   "Build the fetched Copydesk main revision first" if editor_available else prerequisites),
    }
    print(json.dumps({"schema_version": 1, "targets": [target]}))
    return 0 if target["ready"] or action == "inventory" else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, KeyError, ValueError, subprocess.SubprocessError) as error:
        sys.exit(f"copydesk: {error}")
