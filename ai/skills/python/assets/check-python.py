#!/usr/bin/env python3
"""Run the isolated, pinned Python correctness profile without rewriting source."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tokenize
import tomllib
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import TypedDict, cast


class Commands(TypedDict):
    test: list[str]
    legacy: list[list[str]]


class Settings(TypedDict):
    version: int
    paths: list[str]
    commands: Commands


def settings(root: Path) -> Settings:
    data = json.loads((root / ".python-quality.json").read_text())
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("unsupported Python quality settings")
    paths = data.get("paths")
    if (
        not isinstance(paths, list)
        or not paths
        or not all(
            isinstance(path, str)
            and path
            and not PurePosixPath(path).is_absolute()
            and ".." not in PurePosixPath(path).parts
            and (root / path).exists()
            and (root / path).resolve().is_relative_to(root)
            for path in paths
        )
    ):
        raise ValueError("Python paths must be existing repository-relative paths")
    commands = data.get("commands")
    if not isinstance(commands, dict) or set(commands) != {"test", "legacy"}:
        raise ValueError("Python commands must contain test and legacy")
    for command in [commands["test"], *commands["legacy"]] if isinstance(commands["legacy"], list) else [None]:
        if not isinstance(command, list) or not command or not all(isinstance(arg, str) and arg for arg in command):
            raise ValueError("Python commands must be nonempty argv arrays")
    return cast(Settings, data)


def tool_environment(root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["UV_PROJECT_ENVIRONMENT"] = str(root / ".python-quality/.venv")
    environment["RUFF_CACHE_DIR"] = str(root / ".python-quality/.ruff_cache")
    environment.pop("VIRTUAL_ENV", None)
    return environment


def run(root: Path, command: Sequence[str], *, isolated: bool = True) -> None:
    print("Python quality: " + json.dumps(list(command)), flush=True)
    subprocess.run(  # noqa: S603 -- explicit trusted project/check argv
        command, cwd=root, check=True, env=tool_environment(root) if isolated else None
    )


def uv() -> str:
    executable = shutil.which("uv")
    if executable is None:
        raise ValueError("uv is required for Python quality checks")
    return executable


def tool(root: Path, *command: str) -> list[str]:
    return [uv(), "run", "--project", str(root / ".python-quality"), "--locked", "--no-sync", *command]


def audit(root: Path, paths: Sequence[str]) -> None:
    # Do not execute dependency manifests; unsupported declared runtimes fail closed.
    manifests = {
        "requirements.txt",
        "requirements.in",
        "Pipfile",
        "Pipfile.lock",
        "setup.py",
        "setup.cfg",
        "poetry.lock",
        "pdm.lock",
        "environment.yml",
        "environment.yaml",
    }
    candidates = {root}
    for path in source_files(root, paths):
        candidates.update(parent for parent in path.parents if parent.is_relative_to(root))
    projects = [root / ".python-quality"]
    for project in sorted(candidates):
        has_manifest = (
            any((project / name).is_file() for name in manifests)
            or any(project.glob("requirements*.txt"))
            or any(project.glob("requirements*.in"))
        )
        pyproject = project / "pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as stream:
                metadata = tomllib.load(stream)
            tools = metadata.get("tool", {})
            has_manifest = (
                has_manifest
                or "project" in metadata
                or "build-system" in metadata
                or isinstance(tools, dict)
                and any(name in tools for name in ("poetry", "pdm"))
            )
        if (project / "uv.lock").is_file():
            projects.append(project)
        elif has_manifest:
            raise ValueError(
                f"dependency audit requires uv.lock for declared runtime dependencies at {project}; no manifest was executed"
            )
    seen_requirements: set[str] = set()
    for project in projects:
        exported = subprocess.run(  # noqa: S603 -- fixed uv dependency export command
            [
                uv(),
                "export",
                "--project",
                str(project),
                "--locked",
                "--no-build",
                "--all-packages",
                "--no-hashes",
                "--no-emit-project",
                "--no-emit-workspace",
            ],
            cwd=root,
            env=tool_environment(root),
            text=True,
            capture_output=True,
            check=True,
        )
        normalized = "\n".join(line for line in exported.stdout.splitlines() if not line.lstrip().startswith("#"))
        if normalized in seen_requirements:
            continue
        seen_requirements.add(normalized)
        with tempfile.TemporaryDirectory(prefix="python-audit-") as temporary:
            requirements = Path(temporary) / "requirements.txt"
            requirements.write_text(exported.stdout)
            run(root, tool(root, "pip-audit", "--disable-pip", "--no-deps", "--requirement", str(requirements)))


def source_files(root: Path, paths: Sequence[str]) -> set[Path]:
    excluded = {"vendor", "node_modules", "__pycache__", "build", "dist"}
    files: set[Path] = set()
    for name in paths:
        target = root / name
        if target.is_file():
            files.add(target)
        else:
            for directory, children, names in os.walk(target):
                children[:] = [child for child in children if not child.startswith(".") and child not in excluded]
                files.update(Path(directory) / name for name in names if name.endswith((".py", ".pyi")))
    return files


def reject_blanket_overrides(root: Path, paths: Sequence[str]) -> None:
    files = source_files(root, paths)
    for path in sorted(files):
        try:
            with tokenize.open(path) as stream:
                for token in tokenize.generate_tokens(stream.readline):
                    if token.type != tokenize.COMMENT:
                        continue
                    comment = token.string.removeprefix("#").strip()
                    standalone = not token.line[: token.start[1]].strip()
                    if (
                        comment.startswith("mypy:")
                        or (comment.startswith("ty:") and standalone)
                        or (comment.startswith("type: ignore") and standalone)
                    ):
                        raise ValueError(
                            f"blanket type-check override at {path.relative_to(root)}:{token.start[0]}; keep strict checking and use precise line-level handling"
                        )
        except (tokenize.TokenError, IndentationError, SyntaxError, UnicodeError) as error:
            raise ValueError(f"cannot inspect Python source {path}: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("tools", "format", "lint", "typecheck", "test", "audit", "alpha", "all"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if (root / ".python-quality").is_symlink() or (root / ".python-quality/.venv").is_symlink():
            raise ValueError("Python quality tooling directories must not be symlinks")
        config = settings(root)
        if args.command == "tools":
            run(root, [uv(), "sync", "--project", str(root / ".python-quality"), "--locked"])
            return 0
        if not (root / ".python-quality/.venv").is_dir():
            raise ValueError("Python quality tools are missing; run python3 scripts/check-python.py tools")
        run(root, [uv(), "sync", "--project", str(root / ".python-quality"), "--locked", "--check"])
        paths = config["paths"]
        steps = [args.command] if args.command not in {"alpha", "all"} else ["format", "lint", "typecheck", "test"]
        if args.command == "all":
            steps.append("audit")
        if args.command in {"typecheck", "test", "alpha", "all"}:
            for command in config["commands"]["legacy"]:
                run(root, command, isolated=False)
        for step in steps:
            if step == "format":
                run(
                    root, tool(root, "ruff", "format", "--check", "--config", ".python-quality/ruff.toml", "--", *paths)
                )
            elif step == "lint":
                run(root, tool(root, "ruff", "check", "--config", ".python-quality/ruff.toml", "--", *paths))
            elif step == "typecheck":
                reject_blanket_overrides(root, paths)
                run(
                    root,
                    tool(
                        root,
                        "ruff",
                        "check",
                        "--config",
                        ".python-quality/ruff.toml",
                        "--select",
                        "ANN,PYI",
                        "--",
                        *paths,
                    ),
                )
                python = root / ".venv" if (root / ".venv").is_dir() else root / ".python-quality/.venv"
                run(
                    root,
                    tool(
                        root,
                        "ty",
                        "check",
                        "--project",
                        str(root),
                        "--config-file",
                        ".python-quality/ty.toml",
                        "--python",
                        str(python),
                        "--",
                        *paths,
                    ),
                )
            elif step == "test":
                run(root, config["commands"]["test"], isolated=False)
            elif step == "audit":
                audit(root, paths)
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 1
    except (OSError, ValueError) as error:
        print(f"Python quality: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
