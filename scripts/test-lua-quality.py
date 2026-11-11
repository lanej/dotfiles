#!/usr/bin/env python3
"""Exercise the Lua quality entrypoint with real tools in a small Git checkout."""

from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="dotfiles-lua-quality-") as directory:
        root = Path(directory)
        (root / "scripts").mkdir()
        for name in ("scripts/lua-quality.py", ".stylua.toml", ".luacheckrc"):
            shutil.copyfile(ROOT / name, root / name)
        subprocess.run(["git", "init", "--quiet", str(root)], check=True)
        (root / ".gitignore").write_text("vendor/\n")
        (root / "vendor").mkdir()
        (root / "vendor/broken.lua").write_text("this is third-party code")
        source = root / "new config.lua"
        source.write_text("return{answer=42}\n")

        def run(*args):
            return subprocess.run(
                ["python3", str(root / "scripts/lua-quality.py"), *args],
                text=True, capture_output=True, cwd=root,
            )

        assert run().returncode != 0, "unformatted untracked Lua must fail"
        result = run("--fix")
        assert result.returncode == 0, result.stdout + result.stderr
        subprocess.run(["git", "add", "--", source.name], cwd=root, check=True)
        source.write_text("return missing_dotfiles_global\n")
        result = run()
        assert result.returncode != 0 and "missing_dotfiles_global" in result.stdout, result
        source.write_text("return vim\n")
        assert run().returncode != 0, "Neovim globals must not leak into other runtimes"
        (root / "nvim/nested").mkdir(parents=True)
        source.rename(root / "nvim/nested/new config.lua")
        result = run()
        assert result.returncode == 0, result.stdout + result.stderr
    print("PASS: formatting and analysis reject defects in new Lua files and scope host globals")


if __name__ == "__main__":
    main()
