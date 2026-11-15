#!/usr/bin/env python3
"""Exercise the portable profile against real Buf compilation and diagnostics."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]


def run(root: Path, *args: str, success: bool = True) -> str:
    result = subprocess.run(  # noqa: S603 -- test-controlled argv
        [sys.executable, str(root / "scripts/check-protobuf.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == success, (args, result.stdout, result.stderr)
    return result.stdout + result.stderr


with tempfile.TemporaryDirectory(prefix="protobuf-quality-acceptance-") as temporary:
    root = Path(temporary)
    (root / "scripts").mkdir()
    shutil.copy2(SOURCE / "ai/skills/protobuf/assets/check-protobuf.py", root / "scripts/check-protobuf.py")
    plugin = root / ".protobuf-quality"
    plugin.mkdir()
    for name in ("main.go", "go.mod", "go.sum"):
        shutil.copy2(SOURCE / "ai/skills/protobuf/assets" / name, plugin / name)
    shutil.copy2(SOURCE / "ai/skills/protobuf/assets/gitignore", plugin / ".gitignore")
    settings = root / ".protobuf-quality.json"
    shutil.copy2(SOURCE / "ai/skills/protobuf/assets/protobuf-quality.json", settings)
    run(root, "tools")
    directory = root / "proto/acme/v1"
    directory.mkdir(parents=True)
    # Existing workspace settings must resolve imports, but cannot weaken the generated lint policy.
    (root / "buf.yaml").write_text("version: v2\nmodules:\n  - path: proto\nlint:\n  use: [MINIMAL]\n")
    schema = directory / "example.proto"
    header = 'syntax = "proto3";\npackage acme.v1;\n'
    good = header + "// Example has typed fields.\nmessage Example {\n  string display_name = 1;\n}\n"
    schema.write_text(good)
    run(root, "fmt")
    good = schema.read_text()
    run(root, "alpha")
    image = root / "baseline.json"
    executable = shutil.which("buf") or str(root / ".protobuf-quality/bin/buf")
    subprocess.run([executable, "build", "--output", str(image)], cwd=root, check=True)  # noqa: S603 -- pinned Buf argv
    run(root, "all", "--against", str(image))
    git = shutil.which("git")
    assert git, "Git is required for the baseline fixture"
    for args in (
        ("init", "--quiet"),
        ("add", "."),
        (
            "-c",
            "user.name=Profile test",
            "-c",
            "user.email=profile@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "--quiet",
            "-m",
            "Initial schema",
        ),
    ):
        subprocess.run([git, *args], cwd=root, check=True)  # noqa: S603 -- constructed fixture Git argv
    run(root, "all", "--against", ".git#ref=HEAD")
    assert "explicit compatibility baseline" in run(root, "all", success=False)

    schema.write_text(good.replace("string display_name = 1;", "string display_name=1;"))
    before = schema.read_bytes()
    run(root, "format", success=False)
    assert schema.read_bytes() == before, "check mode rewrote source"
    run(root, "fmt")
    assert schema.read_text() == good
    schema.write_text(
        good.replace("string display_name", "// buf:lint:ignore FIELD_LOWER_SNAKE_CASE\n  string DisplayName")
    )
    run(root, "lint", success=False)
    schema.write_text(good.replace("string display_name = 1;", "MissingType display_name = 1;"))
    run(root, "build", success=False)
    schema.write_text(good.replace("string display_name = 1;", "int32 display_name = 1;"))
    run(root, "fmt")
    run(root, "alpha")
    run(root, "all", "--against", str(image), success=False)

    # Native Buf diagnostics identify the exact field, including nested and repeated declarations.
    for field in (
        "string request_json = 1;",
        "repeated string request_json = 1;",
        "message Nested { string request_json = 1; }",
        "oneof choice { string request_json = 1; }",
        "string /* a comment */ request_json = 1;",
    ):
        schema.write_text(header + "// Example.\nmessage Example {\n" + field + "\n}\n")
        diagnostic = run(root, "build", success=False)
        assert "request_json" in diagnostic and "acme/v1/example.proto:" in diagnostic, diagnostic
        assert "_json" in diagnostic, diagnostic

    # The custom rule is deliberately limited to string *_json, rather than general payload opinions.
    schema.write_text(
        header
        + """// Example.
message Example {
  message Payload { string name = 1; }
  Payload request_json = 1;
  string payload = 2;
  bytes response_json = 3;
  string json_request = 4;
}
"""
    )
    run(root, "build")
    schema.write_text(good)
    settings.write_text(json.dumps({"version": 1, "against": str(image)}))
    run(root, "all")
    settings.write_text('{"version": 999}')
    run(root, "build", success=False)

print(
    "Protobuf profile acceptance passed (real Buf compilation, lint, formatting, native plugin diagnostics, compatibility)"
)
