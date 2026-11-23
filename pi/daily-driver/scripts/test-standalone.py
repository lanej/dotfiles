"""Exercise a source export and installed bundle with Node/npm explicitly unavailable."""
import argparse
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile

from export import export

parser = argparse.ArgumentParser()
parser.add_argument("--with-integrations", action="store_true", help="Also exercise native worktree-backed delegation")
args = parser.parse_args()
command_timeout = 240 if os.environ.get("GITHUB_ACTIONS") == "true" else 90
bun = shutil.which("bun")
assert bun, "Install the pinned Bun before standalone acceptance"
with tempfile.TemporaryDirectory(prefix="pi-driver-standalone-") as temporary:
    work = Path(temporary)
    source = work / "source"
    export(source)
    home = work / "home"
    home.mkdir()
    guard = work / "guard"
    guard.mkdir()
    calls = work / "unexpected-node"
    optional_tools = ("zellij", "worktree", "octo-manager", "bd")
    def deny(name):
        script = guard / name
        script.write_text(f'#!/bin/sh\nprintf "%s\\n" "$0" >> "{calls}"\nexit 97\n')
        script.chmod(0o755)
    for name in ("node", "npm", "npx", *optional_tools):
        deny(name)
    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
           "XDG_STATE_HOME": str(home / ".local/state"), "PI_CODING_AGENT_DIR": str(home / "agent"),
           "PI_DRIVER_PREFIX": str(home / ".local"), "PI_SKIP_VERSION_CHECK": "1",
           "PATH": str(guard) + os.pathsep + os.environ["PATH"]}
    env.pop("PI_DRIVER_CONFIG", None)
    env.pop("PI_DRIVER_STATE_DIR", None)
    def run(args, expected=0, cwd=None):
        result = subprocess.run(args, cwd=cwd or source, env=env, text=True, capture_output=True, timeout=command_timeout)
        assert result.returncode == expected, (args, result.stdout[-4000:], result.stderr[-8000:])
        return result.stdout
    run(["git", "init", "-q"])
    with (source / ".gitignore").open("a") as ignored:
        ignored.write("\nlocal.env\n")
    (source / "local.env").write_text("fixture-only-private-value\n")
    exported = work / "second-export"
    run(["python3", "scripts/export.py", str(exported)])
    assert not (exported / "local.env").exists()
    # Without Git, only the declared source manifest is copied.
    (exported / "another-private-file").write_text("fixture-only-private-value\n")
    run(["python3", str(exported / "scripts/export.py"), str(work / "manifest-export")])
    assert not (work / "manifest-export/another-private-file").exists()
    run([bun, "install", "--frozen-lockfile", "--ignore-scripts"])
    run([bun, "install", "--cwd", ".typescript-quality", "--frozen-lockfile", "--ignore-scripts"])
    run([bun, "run", "typecheck"])
    run([bun, "run", "lint"])
    run([bun, "run", "test"])
    run([bun, "run", "test:pi-native"])
    report = json.loads(run([str(source / "scripts/pi-driver"), "doctor"]))
    assert all(not item["available"] for item in report["integrations"].values())
    if args.with_integrations:
        for name in optional_tools:
            (guard / name).unlink()
        for arguments in ([], ["--lost-allocation"], ["--cancel"]):
            run([bun, "run", "test:delegation-native", *arguments])
        for name in optional_tools:
            deny(name)
    run([bun, "run", "build:aot"])
    run([bun, "run", "test"])
    assert json.loads(run([str(source / "scripts/pi-driver"), "doctor"]))["resources"]["available"]
    source_config = run([str(source / "scripts/pi-driver"), "config", "--example"])
    run([bun, "scripts/lifecycle.mjs", "build"])
    launcher = home / ".local/bin/pi-driver"
    assert json.loads(run([str(launcher), "config", "--example"])) == json.loads(source_config)
    first = launcher.resolve()
    assert not (first.parents[1] / "local.env").exists()
    hostile = work / "hostile-checkout"
    hostile.mkdir()
    preload = hostile / "preload.ts"
    bootstrap_marker = work / "unexpected-preload"
    preload.write_text('import { writeFileSync } from "node:fs"; writeFileSync(' + json.dumps(str(bootstrap_marker)) + ', "executed");')
    (hostile / "bunfig.toml").write_text("preload = [" + json.dumps(str(preload)) + "]\n")
    (hostile / ".env").write_text("PI_DRIVER_BOOTSTRAP_UNTRUSTED=dotenv\n")
    assert "1.4.0" in run([str(first.with_name("pi")), "--version"], cwd=hostile)
    for mode in ("0", "1"):
        env["PI_DRIVER_USE_SOURCE"] = mode
        assert json.loads(run([str(launcher), "config", "--example"], cwd=hostile)) == json.loads(source_config)
        assert not bootstrap_marker.exists()
    env.pop("PI_DRIVER_USE_SOURCE", None)
    deny("bun")
    env["PI_DRIVER_USE_SOURCE"] = "1"
    assert json.loads(run([str(launcher), "config", "--example"])) == json.loads(source_config)
    env.pop("PI_DRIVER_USE_SOURCE", None)
    (guard / "bun").unlink()
    settings = json.loads((home / "agent/settings.json").read_text())
    assert settings["packages"] == [str(first.parents[1])]
    run([bun, "scripts/lifecycle.mjs", "build"])
    assert launcher.resolve() == first
    status = json.loads(run([bun, "scripts/lifecycle.mjs", "status"]))
    assert status["installed_fingerprint"] and status["running_revision"] is None
    run([bun, "scripts/lifecycle.mjs", "restart"], expected=3)
    # Installed extension dependencies participate in identity verification.
    dependency = first.parents[1] / "node_modules/pi-git-diff/package.json"
    original_dependency = dependency.read_bytes()
    dependency.write_bytes(original_dependency + b"\n")
    changed = json.loads(run([bun, "scripts/lifecycle.mjs", "status"]))
    assert changed["installed_fingerprint"] is None
    dependency.write_bytes(original_dependency)
    # A real staged compilation failure must leave the previous installation usable.
    cli = source / "cli.ts"
    original = cli.read_text()
    cli.write_text("invalid syntax {{{")
    run([bun, "scripts/lifecycle.mjs", "build"], expected=1)
    assert launcher.resolve() == first
    run([str(launcher), "config", "--example"])
    cli.write_text(original)
    # A changed pin fails before activation and leaves the previous installation usable.
    (source / ".bun-version").write_text("0.0.0\n")
    run([bun, "scripts/lifecycle.mjs", "build"], expected=1)
    assert launcher.resolve() == first
    run([str(launcher), "config", "--example"])
    assert not calls.exists(), calls.read_text() if calls.exists() else ""
print("Standalone source and installed bundle verified with Node/npm unavailable.")
