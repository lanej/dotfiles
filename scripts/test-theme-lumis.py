#!/usr/bin/env python3
"""Exercise Lumis through the installed shell viewer and fzf preview."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / "bin/dotfiles-view"
PREVIEW = ROOT / "bin/fzf-path-preview"
LUA = ROOT / "design-system/fixtures/code.lua"
SGR = re.compile(rb"\x1b\[[0-9;]*m")


def rendered(env, command, *args, data=None):
    return subprocess.run(
        [str(command), *args], input=data, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=20,
    ).stdout


def assert_color(output, token, expected):
    rgb = ";".join(str(int(expected[i:i + 2], 16)) for i in (1, 3, 5))
    ansi = f"\x1b[38;2;{rgb}m{token}\x1b[".encode()
    assert ansi in output, f"{token}: expected {expected}, got {output!r}"


def main():
    generated = Path(os.environ.get("DOTFILES_THEME_DIR", ROOT / "design-system/generated"))
    palette = json.loads((generated / "colors.json").read_text())
    roles = palette["roles"]
    with tempfile.TemporaryDirectory(prefix="dotfiles-lumis-") as work:
        work = Path(work)
        env = {**os.environ, "DOTFILES_THEME_DIR": str(generated), "BAT_CONFIG_PATH": os.devnull,
               "BAT_CACHE_PATH": str(work / "bat"), "TERM": "xterm-256color", "COLORTERM": "truecolor"}
        env.pop("NO_COLOR", None)
        output = rendered(env, VIEWER, "--color=always", "--paging=never", "--", str(LUA))
        assert SGR.sub(b"", output) == LUA.read_bytes()
        assert_color(output, "greet", roles["syntax.function"])
        assert_color(output, "nil", roles["syntax.null"])
        preview = rendered(env, PREVIEW, str(LUA))
        assert_color(preview, "greet", roles["syntax.function"])
        assert_color(preview, "nil", roles["syntax.null"])

        source = b"local unused = nil\n"
        output = rendered(env, VIEWER, "--color=always", "--no-pager", "-l", "lua", "-", data=source)
        assert_color(output, "nil", roles["syntax.null"])
        assert SGR.sub(b"", output) == source
        assert rendered(env, VIEWER, "--plain", "--", str(LUA)) == LUA.read_bytes()
        version = rendered(env, VIEWER, "--version")
        assert version.startswith(b"bat "), version

        fail_bin = work / "fail-bin"
        fail_bin.mkdir()
        lumis = fail_bin / "lumis"
        lumis.write_text(
            "#!/bin/sh\n[ \"$1\" != languages ] || exit 0\n"
            "cat >/dev/null\nprintf 'partial result'\nexit 1\n"
        )
        lumis.chmod(0o755)
        failure_env = {**env, "PATH": str(fail_bin) + os.pathsep + env["PATH"]}
        stdin_flags = ("--color=always", "--no-pager", "-l", "lua", "-")
        assert rendered(failure_env, VIEWER, *stdin_flags, data=source) == rendered(env, "bat", *stdin_flags, data=source)
        file_flags = ("--color=always", "--no-pager", "--line-range=:2", "--", str(LUA))
        assert rendered(failure_env, VIEWER, *file_flags) == rendered(env, "bat", *file_flags)
        unknown = subprocess.run(
            [str(VIEWER), "--color=always", "-l", "missinglang", "-"], input=source,
            env=env, capture_output=True, timeout=20,
        )
        assert unknown.returncode != 0 and b"missinglang" in unknown.stderr and not unknown.stdout, unknown
    print(f"PASS Lumis viewer and fzf preview with {palette['theme']}")


if __name__ == "__main__":
    main()
