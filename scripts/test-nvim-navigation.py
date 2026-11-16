#!/usr/bin/env python3
"""Accept Neovim navigation, annotations, and changed-file previews with locked plugins.

Run: uv run --no-project scripts/test-nvim-navigation.py
Run one feature: uv run --no-project scripts/test-nvim-navigation.py --check changed-files
Requires Neovim 0.12+, Universal Ctags, git, cc, fzf 0.59+, rg, pgrep, and network
access to public GitHub repositories. Changed files needs only Neovim, git, fzf,
and pgrep. LSP replies are fixtures; cloud tools,
credentials, user Neovim configuration, and installed plugins are not used.
"""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, cwd=ROOT, timeout=120, **kwargs)


def checkout(url, revision, destination, env):
    run(["git", "init", "-q", str(destination)], env=env)
    run(["git", "-C", str(destination), "fetch", "-q", "--depth=1", url, revision], env=env)
    run(["git", "-C", str(destination), "checkout", "-q", "--detach", "FETCH_HEAD"], env=env)


def wait_for_fzf_helpers(work, timeout=5):
    deadline = time.monotonic() + timeout
    pattern = f"{work.name}/plugins/fzf-lua/"
    while True:
        result = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True, timeout=5)
        if result.returncode == 1:
            return
        result.check_returncode()
        if time.monotonic() >= deadline:
            raise TimeoutError(f"FzfLua helpers still running: {result.stdout.strip()}; retained {work}")
        time.sleep(0.01)


@contextmanager
def navigation_workspace():
    # rationale(cleanup): FzfLua helper editors can outlive the editor running the assertions.
    work = Path(tempfile.mkdtemp(prefix="nv-nav-", dir="/tmp"))
    try:
        yield work
    finally:
        wait_for_fzf_helpers(work)
        shutil.rmtree(work)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", choices=("navigation", "annotations", "changed-files"),
                        help="Run only this feature's acceptance check")
    args = parser.parse_args()
    checks = (args.check,) if args.check else ("navigation", "annotations", "changed-files")
    only_changed_files = checks == ("changed-files",)
    executables = ("nvim", "git", "fzf", "pgrep") if only_changed_files else (
        "nvim", "git", "cc", "fzf", "rg", "pgrep")
    for executable in executables:
        if not shutil.which(executable):
            raise SystemExit(f"Install {executable} and add it to PATH before running acceptance.")
    lock = json.loads((ROOT / "nvim/lazy-lock.json").read_text())
    # Darwin's Unix socket paths are limited; FzfLua appends its server name.
    with navigation_workspace() as work:
        env = dict(os.environ)
        for key in list(env):
            if key.startswith("GIT_"):
                del env[key]
        template = work / "git-template"
        template.mkdir()
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TEMPLATE_DIR=str(template))
        for kind in ("CONFIG", "DATA", "STATE", "CACHE", "RUNTIME"):
            directory = work / kind.lower()
            directory.mkdir(mode=0o700)
            env[f"XDG_{kind}_HOME" if kind != "RUNTIME" else "XDG_RUNTIME_DIR"] = str(directory)
        env.pop("NVIM", None)
        env.pop("NVIM_LISTEN_ADDRESS", None)
        plugins, site = work / "plugins", work / "site"
        env["NVIM_TEST_PLUGIN_ROOT"] = str(plugins)
        env["NVIM_TEST_SITE"] = str(site)
        env.pop("GUTENTAGS_RUNTIME", None)
        dependencies = [("fzf-lua", "ibhagwan/fzf-lua")]
        if "changed-files" in checks:
            dependencies.append(("gitsigns.nvim", "lewis6991/gitsigns.nvim"))
        if not only_changed_files:
            dependencies.extend((
                ("nvim-treesitter", "nvim-treesitter/nvim-treesitter"),
                ("vim-gutentags", "ludovicchabant/vim-gutentags"),
                ("todo-comments.nvim", "folke/todo-comments.nvim"),
                ("plenary.nvim", "nvim-lua/plenary.nvim"),
            ))
        for name, repository in dependencies:
            checkout(f"https://github.com/{repository}.git", lock[name]["commit"], plugins / name, env)
        if not only_changed_files:
            # Use the grammar revision selected by the locked Tree-sitter plugin.
            info = run([
                "nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n",
                "+lua local parsers = dofile(vim.env.NVIM_TEST_PLUGIN_ROOT .. '/nvim-treesitter/lua/nvim-treesitter/parsers.lua'); io.write(vim.json.encode(parsers.lua.install_info))",
                "+qa!",
            ], env=env, capture_output=True, text=True)
            grammar = json.loads(info.stdout)
            source = work / "lua-grammar"
            checkout(grammar["url"], grammar["revision"], source, env)
            grammar_parser = site / "parser/lua.so"
            grammar_parser.parent.mkdir(parents=True)
            sources = [source / "src/parser.c"]
            if (source / "src/scanner.c").exists():
                sources.append(source / "src/scanner.c")
            run(["cc", "-shared", "-fPIC", "-O2", "-I", str(source / "src"),
                 *map(str, sources), "-o", str(grammar_parser)])
        for check in checks:
            print(f"Running isolated {check} acceptance with locked plugins", flush=True)
            run(["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l",
                 f"nvim/tests/{check}.lua"], env=env)


if __name__ == "__main__":
    main()
