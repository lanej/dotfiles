#!/usr/bin/env python3
"""Run Buf with a native JSON string field rule and the project's lifecycle gate."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import TypedDict, cast


class Settings(TypedDict):
    version: int
    against: str | None


BUF_VERSION = "1.75.0"
PLUGIN = ".protobuf-quality/bin/buf-plugin-json-string"
STRICT = {
    "version": "v2",
    "lint": {
        "use": ["STANDARD", "COMMENT_MESSAGE", "COMMENT_RPC", "COMMENT_SERVICE", "FIELD_NO_JSON_STRING"],
        "disallow_comment_ignores": True,
    },
    "breaking": {"use": ["FILE"]},
    "plugins": [{"plugin": PLUGIN}],
}


def run(argv: list[str], root: Path, *, capture: bool = False, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(argv, cwd=root, env=env, check=True, text=True, stdout=subprocess.PIPE if capture else None)  # noqa: S603 -- constructed argv, no shell
    return result.stdout if capture else ""


def buf_binary(root: Path) -> str:
    for candidate in (shutil.which("buf"), str(root / ".protobuf-quality/bin/buf")):
        if (
            candidate
            and Path(candidate).is_file()
            and run([candidate, "--version"], root, capture=True).strip() == BUF_VERSION
        ):
            return candidate
    raise ValueError(f"Buf {BUF_VERSION} is required; run python3 scripts/check-protobuf.py tools")


def install_tools(root: Path) -> None:
    go = shutil.which("go")
    if go is None:
        raise ValueError("Go 1.26+ is required to build the Buf check plugin")
    binary_dir = root / ".protobuf-quality/bin"
    binary_dir.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, GOWORK="off", GOBIN=str(binary_dir))
    try:
        buf_binary(root)
    except ValueError:
        run([go, "install", f"github.com/bufbuild/buf/cmd/buf@v{BUF_VERSION}"], root, env=environment)
    run([go, "build", "-mod=readonly", "-o", str(root / PLUGIN), "."], root / ".protobuf-quality", env=environment)


def settings(root: Path) -> Settings:
    value = json.loads((root / ".protobuf-quality.json").read_text())
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "against"}
        or type(value["version"]) is not int
        or value["version"] != 1
    ):
        raise ValueError("unsupported .protobuf-quality.json; expected version and against")
    if value["against"] is not None and (not isinstance(value["against"], str) or not value["against"].strip()):
        raise ValueError("against must be null or a nonempty Buf input")
    return cast(Settings, value)


def schema_inputs(root: Path) -> list[str]:
    policy = root / ".source-code.json"
    inputs = (
        json.loads(policy.read_text()).get("detection", {}).get("protobuf_roots", ["."]) if policy.is_file() else ["."]
    )
    if (
        not isinstance(inputs, list)
        or not inputs
        or not all(
            isinstance(name, str)
            and name
            and not PurePosixPath(name).is_absolute()
            and ".." not in PurePosixPath(name).parts
            and "," not in name
            and "#" not in name
            and (root / name).is_dir()
            and (root / name).resolve().is_relative_to(root)
            for name in inputs
        )
    ):
        raise ValueError("invalid detected Protobuf roots; rerun source-code setup")
    return cast(list[str], inputs)


def baseline_input(against: str, source: str) -> str:
    location, separator, options = against.partition("#")
    if (
        source != "."
        and location.endswith(".git")
        and not any(option.startswith("subdir=") for option in options.split(","))
    ):
        return location + "#" + (options + "," if separator and options else "") + "subdir=" + source
    return against


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=("tools", "build", "lint", "format", "fmt", "breaking", "alpha", "all"),
    )
    parser.add_argument("--against", help="Buf baseline; otherwise PROTOBUF_AGAINST or saved against")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.mode == "tools":
            install_tools(root)
            return 0
        config = settings(root)
        buf = buf_binary(root)
        inputs = schema_inputs(root)
        if args.mode in {"fmt", "format", "alpha", "all"}:
            for source in inputs:
                run(
                    [buf, "format", source, "-w"]
                    if args.mode == "fmt"
                    else [buf, "format", source, "--diff", "--exit-code"],
                    root,
                )
        if args.mode in {"fmt", "format"}:
            return 0
        if not (root / PLUGIN).is_file():
            raise ValueError("Buf check plugin is missing; run python3 scripts/check-protobuf.py tools")
        against = args.against or os.environ.get("PROTOBUF_AGAINST") or config["against"] or ""
        if args.mode in {"breaking", "all"} and not against:
            raise ValueError(
                "set an explicit compatibility baseline with --against, PROTOBUF_AGAINST, or saved against"
            )
        for source in inputs:
            check_schema(buf, root, args.mode, against, source)
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 1
    except (OSError, ValueError) as error:
        print(f"Protobuf quality: {error}", file=sys.stderr)
        return 1
    return 0


def check_schema(buf: str, root: Path, mode: str, against: str, source: str) -> None:
    with tempfile.TemporaryDirectory(prefix="protobuf-quality-") as temporary:
        image = Path(temporary) / "image.binpb"
        # Retain workspace/import resolution while enforcing the profile's lint policy on the compiled image.
        run([buf, "build", source, "--output", str(image)], root)
        policy = (
            STRICT
            if mode in {"lint", "alpha", "all"}
            else {
                **STRICT,
                "lint": {"use": ["FIELD_NO_JSON_STRING"], "disallow_comment_ignores": True},
            }
        )
        run([buf, "lint", str(image), "--config", json.dumps(policy)], root)
        if mode in {"breaking", "all"}:
            run(
                [
                    buf,
                    "breaking",
                    str(image),
                    "--config",
                    json.dumps(STRICT),
                    "--against",
                    baseline_input(against, source),
                ],
                root,
            )


if __name__ == "__main__":
    sys.exit(main())
