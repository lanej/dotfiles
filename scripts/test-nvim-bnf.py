#!/usr/bin/env python3
"""Install the bundled BNF parser and exercise real Neovim highlighting in isolation."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PLUGINS = {
    "nvim-treesitter": "nvim-treesitter/nvim-treesitter",
    "nvim-treesitter-textobjects": "nvim-treesitter/nvim-treesitter-textobjects",
}


def run(args, **kwargs):
    return subprocess.run(args, check=True, timeout=120, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugins-dir", type=Path, help="Reuse clean plugin checkouts at the locked revisions")
    args = parser.parse_args()
    for executable in ("nvim", "tree-sitter", "cc", "git"):
        if not shutil.which(executable):
            raise SystemExit(f"Install {executable} and add it to PATH before running the BNF check.")
    lock = json.loads((ROOT / "nvim/lazy-lock.json").read_text())
    with tempfile.TemporaryDirectory(prefix="nvim-bnf-") as temporary:
        work = Path(temporary)
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(HOME=str(work), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                   DOTFILES_NVIM_BOOTSTRAP="1")
        for kind in ("CONFIG", "DATA", "STATE", "CACHE"):
            directory = work / kind.lower()
            directory.mkdir()
            env[f"XDG_{kind}_HOME"] = str(directory)
        env.pop("NVIM", None)
        env.pop("NVIM_LISTEN_ADDRESS", None)
        env.pop("NVIM_APPNAME", None)
        config = work / "config/nvim"
        shutil.copytree(ROOT / "nvim", config,
                        ignore=shutil.ignore_patterns("src", "parser.so", "__pycache__"))
        plugins = args.plugins_dir.resolve() if args.plugins_dir else work / "plugins"
        for name, repository in PLUGINS.items():
            destination = plugins / name
            revision = lock[name]["commit"]
            if args.plugins_dir:
                actual = run(["git", "-C", str(destination), "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
                dirty = run(["git", "-C", str(destination), "status", "--porcelain"],
                            capture_output=True, text=True).stdout.strip()
                assert actual == revision and not dirty, f"Plugin must be clean at locked revision: {name}"
            else:
                run(["git", "init", "-q", str(destination)], env=env)
                run(["git", "-C", str(destination), "fetch", "-q", "--depth=1",
                     f"https://github.com/{repository}.git", revision], env=env)
                run(["git", "-C", str(destination), "checkout", "-q", "--detach", "FETCH_HEAD"], env=env)
        fixture = work / "sample.bnf"
        fixture.write_text(
            '# Grammar with alternatives and escaped terminals\n'
            '<expression> ::= <number> | <expression> "+" <number>\n'
            '              | "(" <expression> ")" # continuation\n'
            '<number> ::= "0" | \'1\'\n'
            '<empty> ::= ""\n'
            r'''<quoted> ::= "say \"hello\"" | 'it\'s' | "#"'''
        )
        env.update(NVIM_BNF_PLUGINS=str(plugins), NVIM_BNF_FIXTURE=str(fixture))
        run(["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l",
             str(ROOT / "nvim/tests/bnf.lua")], env=env)


if __name__ == "__main__":
    main()
