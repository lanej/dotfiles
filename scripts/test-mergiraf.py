#!/usr/bin/env python3
"""Compare ordinary Git and the configured Mergiraf driver on dotfiles examples."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    (
        "Independent tool additions", "tools.toml",
        '[tools]\ngit = true\n',
        '[tools]\ngit = true\nmergiraf = true\n',
        '[tools]\ngit = true\nzellij = true\n',
        '[tools]\ngit = true\nmergiraf = true\nzellij = true\n',
        1, 0,
    ),
    (
        "Independent edits on one Lua line", "options.lua",
        'return { timeout = 1000, enabled = false }\n',
        'return { timeout = 500, enabled = false }\n',
        'return { timeout = 1000, enabled = true }\n',
        'return { timeout = 500, enabled = true }\n',
        1, 0,
    ),
    (
        "Conflicting values still need a decision", "settings.toml",
        '[editor]\ntimeout = 1000\n',
        '[editor]\ntimeout = 500\n',
        '[editor]\ntimeout = 2000\n',
        None,
        1, 1,
    ),
    (
        "Duplicate JSON keys hidden by a clean textual merge", "settings.json",
        '{\n  "alpha": 1,\n  "beta": 2,\n  "gamma": 3,\n  "delta": 4\n}\n',
        '{\n  "timeout": 500,\n  "alpha": 1,\n  "beta": 2,\n  "gamma": 3,\n  "delta": 4\n}\n',
        '{\n  "alpha": 1,\n  "beta": 2,\n  "gamma": 3,\n  "delta": 4,\n  "timeout": 2000\n}\n',
        None,
        0, 1,
    ),
)


def main():
    if not shutil.which("mergiraf"):
        raise SystemExit("mergiraf is required; see docs/mergiraf.md")
    driver = subprocess.check_output(
        ["git", "config", "--file", str(ROOT / "git/gitconfig"),
         "--get", "merge.mergiraf.driver"], text=True,
    ).strip()
    print(subprocess.check_output(["mergiraf", "--version"], text=True).strip())
    with tempfile.TemporaryDirectory(prefix="dotfiles-mergiraf-") as temporary:
        scratch = Path(temporary)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith("GIT_") and key != "mergiraf"}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                   XDG_CACHE_HOME=str(scratch / "cache"))
        for index, (title, name, base, ours, theirs, expected, plain_status,
                    structured_status) in enumerate(CASES):
            repo = scratch / str(index)
            repo.mkdir()

            def git(*args, status=0):
                result = subprocess.run(
                    ["git", "-c", "core.hooksPath=" + os.devnull,
                     "-c", "core.attributesFile=" + os.devnull,
                     "-c", "commit.gpgsign=false", *args],
                    cwd=repo, env=env, capture_output=True, text=True, timeout=30,
                )
                if result.returncode != status:
                    raise AssertionError(f"{title}: git {args}: {result.stdout}{result.stderr}")
                return result

            git("init", "-q", "--initial-branch=ours")
            git("config", "user.name", "Mergiraf example")
            git("config", "user.email", "example@example.invalid")
            git("config", "merge.conflictStyle", "diff3")
            git("config", "merge.mergiraf.driver", driver)
            path = repo / name
            path.write_text(base)
            git("add", name)
            git("commit", "-qm", "base")
            git("branch", "theirs")
            path.write_text(ours)
            git("commit", "-qam", "ours")
            git("switch", "-q", "theirs")
            path.write_text(theirs)
            git("commit", "-qam", "theirs")
            git("switch", "-q", "ours")
            git("merge", "--no-commit", "--no-ff", "theirs", status=plain_status)
            plain = path.read_text()
            git("merge", "--abort")
            (repo / ".git/info/attributes").write_text(f"{name} merge=mergiraf\n")
            git("merge", "--no-commit", "--no-ff", "theirs", status=structured_status)
            structured = path.read_text()
            if expected is not None:
                assert structured == expected, (title, structured)
            else:
                assert "<<<<<<<" in structured and "500" in structured and "2000" in structured, structured
            if index == 3:
                assert plain.count('"timeout"') == 2, plain
            print(f"\n{title} ({name})")
            print(f"Git: {'conflict' if plain_status else 'clean'}")
            print(plain, end="")
            print(f"Mergiraf: {'conflict' if structured_status else 'clean'}")
            print(structured, end="")
            git("merge", "--abort")
            env["mergiraf"] = "0"
            git("merge", "--no-commit", "--no-ff", "theirs", status=plain_status)
            assert path.read_text() == plain, f"{title}: escape hatch changed Git's result"
            env.pop("mergiraf")


if __name__ == "__main__":
    main()
