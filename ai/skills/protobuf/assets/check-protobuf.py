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
from pathlib import Path
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
        if args.mode in {"fmt", "format", "alpha", "all"}:
            run([buf, "format", "-w"] if args.mode == "fmt" else [buf, "format", "--diff", "--exit-code"], root)
        if args.mode in {"fmt", "format"}:
            return 0
        if not (root / PLUGIN).is_file():
            raise ValueError("Buf check plugin is missing; run python3 scripts/check-protobuf.py tools")
        against = args.against or os.environ.get("PROTOBUF_AGAINST") or config["against"] or ""
        if args.mode in {"breaking", "all"} and not against:
            raise ValueError(
                "set an explicit compatibility baseline with --against, PROTOBUF_AGAINST, or saved against"
            )
        with tempfile.TemporaryDirectory(prefix="protobuf-quality-") as temporary:
            image = Path(temporary) / "image.binpb"
            # Retain workspace/import resolution while enforcing the profile's lint policy on the compiled image.
            run([buf, "build", "--output", str(image)], root)
            policy = (
                STRICT
                if args.mode in {"lint", "alpha", "all"}
                else {
                    **STRICT,
                    "lint": {"use": ["FIELD_NO_JSON_STRING"], "disallow_comment_ignores": True},
                }
            )
            run([buf, "lint", str(image), "--config", json.dumps(policy)], root)
            if args.mode in {"breaking", "all"}:
                run([buf, "breaking", str(image), "--config", json.dumps(STRICT), "--against", against], root)
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 1
    except (OSError, ValueError) as error:
        print(f"Protobuf quality: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
