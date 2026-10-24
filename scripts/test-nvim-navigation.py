#!/usr/bin/env python3
"""Accept navigation through real Neovim, Ctags, Tree-sitter, rg, and FzfLua.

Run: uv run --no-project scripts/test-nvim-navigation.py
Requires Neovim 0.12+, Universal Ctags, git, cc, fzf 0.59+, rg, and network
access to public GitHub repositories. LSP replies are fixtures; cloud tools,
credentials, user Neovim configuration, and installed plugins are not used.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, cwd=ROOT, timeout=120, **kwargs)


def checkout(url, revision, destination, env):
    run(["git", "init", "-q", str(destination)], env=env)
    run(["git", "-C", str(destination), "fetch", "-q", "--depth=1", url, revision], env=env)
    run(["git", "-C", str(destination), "checkout", "-q", "--detach", "FETCH_HEAD"], env=env)


def main():
    for executable in ("nvim", "git", "cc", "fzf", "rg"):
        if not shutil.which(executable):
            raise SystemExit(f"Install {executable} and add it to PATH before running acceptance.")
    lock = json.loads((ROOT / "nvim/lazy-lock.json").read_text())
    # Darwin's Unix socket paths are limited; FzfLua appends its server name.
    with tempfile.TemporaryDirectory(prefix="nv-nav-", dir="/tmp") as temporary:
        work = Path(temporary)
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
        for name, repository in (
            ("fzf-lua", "ibhagwan/fzf-lua"),
            ("nvim-treesitter", "nvim-treesitter/nvim-treesitter"),
            ("vim-gutentags", "ludovicchabant/vim-gutentags"),
        ):
            checkout(f"https://github.com/{repository}.git", lock[name]["commit"], plugins / name, env)
        # Use the grammar revision selected by the locked Tree-sitter plugin.
        info = run([
            "nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n",
            "+lua local parsers = dofile(vim.env.NVIM_TEST_PLUGIN_ROOT .. '/nvim-treesitter/lua/nvim-treesitter/parsers.lua'); io.write(vim.json.encode(parsers.lua.install_info))",
            "+qa!",
        ], env=env, capture_output=True, text=True)
        grammar = json.loads(info.stdout)
        source = work / "lua-grammar"
        checkout(grammar["url"], grammar["revision"], source, env)
        parser = site / "parser/lua.so"
        parser.parent.mkdir(parents=True)
        sources = [source / "src/parser.c"]
        if (source / "src/scanner.c").exists():
            sources.append(source / "src/scanner.c")
        run(["cc", "-shared", "-fPIC", "-O2", "-I", str(source / "src"),
             *map(str, sources), "-o", str(parser)])
        print("Running isolated navigation acceptance with locked plugins", flush=True)
        run(["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l", "nvim/tests/navigation.lua"], env=env)


if __name__ == "__main__":
    main()
