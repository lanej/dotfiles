#!/usr/bin/env python3
"""Check the portable Python gate against real passing and failing programs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict


class TestCommands(TypedDict):
    test: list[str]
    legacy: list[list[str]]


class TestSettings(TypedDict):
    version: int
    paths: list[str]
    commands: TestCommands


SOURCE = Path(__file__).resolve().parents[1]


def run(root: Path, command: Sequence[str], *, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=root, text=True, capture_output=True)  # noqa: S603 -- controlled test argv
    assert (result.returncode == 0) == success, (command, result.stdout, result.stderr)
    return result


def main() -> int:
    for source, destination in (
        ("check-python.py", "scripts/check-python.py"),
        ("pyproject.toml", ".python-quality/pyproject.toml"),
        ("uv.lock", ".python-quality/uv.lock"),
        ("ruff.toml", ".python-quality/ruff.toml"),
        ("ty.toml", ".python-quality/ty.toml"),
    ):
        assert (SOURCE / "ai/skills/python/assets" / source).read_bytes() == (SOURCE / destination).read_bytes(), (
            destination
        )
    with tempfile.TemporaryDirectory(prefix="python-quality-acceptance-") as temporary:
        root = Path(temporary).resolve()
        assets = SOURCE / "ai/skills/python/assets"
        for source, destination in (
            ("check-python.py", "scripts/check-python.py"),
            ("pyproject.toml", ".python-quality/pyproject.toml"),
            ("uv.lock", ".python-quality/uv.lock"),
            ("ty.toml", ".python-quality/ty.toml"),
            ("ruff.toml", ".python-quality/ruff.toml"),
        ):
            target = root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(assets / source, target)
        # A parent uv workspace must not absorb or rewrite the isolated tool project.
        parent_project = (
            '[project]\nname = "parent"\nversion = "1.0.0"\n[tool.uv.workspace]\nmembers = ["packages/*"]\n'
        )
        (root / "pyproject.toml").write_text(parent_project)
        (root / "tests").mkdir()
        (root / "tests/test_app.py").write_text(
            "import unittest\nfrom app import double\n\nclass Example(unittest.TestCase):\n    def test_double(self):\n        self.assertEqual(double(3), 6)\n        self.assertEqual(double(-1), -2)\n"
        )
        app = root / "app.py"
        original = "def double(value: int) -> int:\n    return value * 2\n"
        app.write_text(original)
        settings: TestSettings = {
            "version": 1,
            "paths": ["app.py"],
            "commands": {
                "legacy": [],
                "test": [
                    "uv",
                    "run",
                    "--project",
                    ".python-quality",
                    "--locked",
                    "--no-sync",
                    "python",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                ],
            },
        }
        config = root / ".python-quality.json"
        config.write_text(json.dumps(settings))
        checker = [sys.executable, str(root / "scripts/check-python.py")]
        foreign = root / "foreign-environment"
        foreign.mkdir()
        (foreign / "sentinel").write_text("preserve")
        environment = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(foreign)}
        configured = subprocess.run([*checker, "tools"], cwd=root, env=environment, text=True, capture_output=True)  # noqa: S603 -- controlled checker invocation
        assert configured.returncode == 0, configured.stderr
        assert list(foreign.iterdir()) == [foreign / "sentinel"]
        assert (foreign / "sentinel").read_text() == "preserve"
        run(root, [*checker, "project-tools"])
        assert not (root / ".venv").exists()
        run(root, [*checker, "alpha"])
        assert app.read_text() == original
        assert (root / "pyproject.toml").read_text() == parent_project
        assert not (root / "uv.lock").exists()

        app.write_text("def double(value):\n    return value * 2\n")
        assert "ANN001" in run(root, [*checker, "typecheck"], success=False).stdout
        (root / "pyproject.toml").write_text(
            parent_project.replace('version = "1.0.0"', 'version = "1.0.0"\nrequires-python = ">=3.12"')
        )
        app.write_text("from typing import override\n\n\n" + original)
        # The isolated Ty configuration uses the selected environment for its target version.
        run(root, ["uv", "venv", "--python", "3.12", str(root / ".venv")])
        run(root, [*checker, "typecheck"])
        shutil.rmtree(root / ".venv")
        (root / "pyproject.toml").write_text(parent_project)
        wrong = original.replace("return value * 2", 'return "wrong"')
        app.write_text(wrong)
        failed = run(root, [*checker, "typecheck"], success=False)
        assert "invalid-explicit-return" in failed.stdout and app.read_text() == wrong
        app.write_text("# mypy: disallow-untyped-defs, warn-return-any=True\n" + original)
        run(root, [*checker, "typecheck"])
        app.write_text("# mypy: disallow-untyped-defs=False\n" + original)
        assert "blanket type-check override" in run(root, [*checker, "typecheck"], success=False).stderr
        app.write_text("# mypy: ignore-errors\n" + wrong)
        assert "blanket type-check override" in run(root, [*checker, "typecheck"], success=False).stderr
        app.write_text("# ty: ignore[invalid-explicit-return]\n" + wrong)
        assert "blanket type-check override" in run(root, [*checker, "typecheck"], success=False).stderr
        app.write_text("# type: ignore[return-value]\n" + wrong)
        assert "blanket type-check override" in run(root, [*checker, "typecheck"], success=False).stderr
        settings["commands"]["legacy"] = [[sys.executable, "-c", "raise SystemExit(19)"]]
        config.write_text(json.dumps(settings))
        assert run(root, [*checker, "typecheck"], success=False).returncode == 19
        settings["commands"]["legacy"] = []
        config.write_text(json.dumps(settings))
        app.write_text(original)
        app.write_text("def unsafe(value: str) -> object:\n    return eval(value)\n")
        assert "S307" in run(root, [*checker, "lint"], success=False).stdout
        app.write_text(original.replace("value * 2", "value*2"))
        before = app.read_bytes()
        run(root, [*checker, "format"], success=False)
        assert app.read_bytes() == before, "format gate rewrote the program"
        app.write_text(original)

        settings["commands"]["test"] = [sys.executable, "-c", "raise SystemExit(17)"]
        config.write_text(json.dumps(settings))
        assert run(root, [*checker, "test"], success=False).returncode == 17
        settings["paths"] = ["../outside.py"]
        config.write_text(json.dumps(settings))
        assert "repository-relative" in run(root, [*checker, "typecheck"], success=False).stderr
        settings["paths"] = ["app.py"]
        config.write_text(json.dumps(settings))
        assert "uv.lock" in run(root, [*checker, "audit"], success=False).stderr
        (root / "pyproject.toml").unlink()
        marker = root / "manifest-executed"
        (root / "setup.py").write_text('from pathlib import Path\nPath("manifest-executed").touch()\n')
        assert "uv.lock" in run(root, [*checker, "audit"], success=False).stderr
        assert not marker.exists()
        (root / "setup.py").unlink()

        dash = root / "--ignore-missing-imports"
        dash.write_text(wrong)
        settings["paths"] = ["app.py", dash.name]
        config.write_text(json.dumps(settings))
        dash_result = run(root, [*checker, "typecheck"], success=False)
        assert "invalid-explicit-return" in dash_result.stdout
        settings["paths"] = ["app.py"]
        config.write_text(json.dumps(settings))
        (root / "pyproject.toml").write_text(
            '[project]\nname="application"\nversion="0.1.0"\nrequires-python=">=3.11"\ndependencies=["six==1.17.0"]\n[tool.uv]\npackage=false\n'
        )
        run(root, ["uv", "lock"])
        run(root, [*checker, "project-tools"])
        app.write_text("import six\n\n" + original)
        run(root, [*checker, "typecheck"])
        # A runnable but stale tool version must be rejected before any gate executes.
        uv = shutil.which("uv")
        assert uv is not None
        run(root, [uv, "pip", "install", "--python", str(root / ".python-quality/.venv/bin/python"), "ruff==0.17.4"])
        stale = run(root, [*checker, "typecheck"], success=False)
        assert '"ty"' not in stale.stdout
        run(root, [*checker, "tools"])

        project = root / ".python-quality/pyproject.toml"
        project.write_text(project.read_text().replace("ruff==0.17.5", "ruff==0.17.4"))
        old_lock = (root / ".python-quality/uv.lock").read_bytes()
        run(root, [*checker, "typecheck"], success=False)
        assert (root / ".python-quality/uv.lock").read_bytes() == old_lock
    print(
        "PASS: pinned Python profile rejects type/security/format faults, forwards test failures, and preserves project/workspace policy."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
