#!/usr/bin/env python3
"""Install and activate the standalone router selected by dotfiles."""

import os
import json
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def main():
    home = Path.home()
    credentials = home / ".config/bedrock/env"
    if not credentials.is_file():
        raise ValueError("Bedrock credentials are missing; configure ~/.config/bedrock/env or set BEDROCK_TOKEN_FILE.")
    codex_home = Path(os.environ.get("CODEX_HOME") or home / ".codex")
    installed = codex_home / "bedrock-router/bedrock-router"
    compatible = False
    if installed.is_file() and os.access(installed, os.X_OK):
        help_result = subprocess.run([str(installed), "install", "--help"],
                                     capture_output=True, text=True, check=False)
        help_text = help_result.stdout + help_result.stderr
        compatible = "--preserve-mcp" in help_text or "-preserve-mcp" in help_text
        compatible = compatible and ("--keep-env" in help_text or "-keep-env" in help_text)
    if compatible:
        status = subprocess.run([str(installed), "status", "--quiet"], check=False)
        if status.returncode != 0:
            identity = subprocess.run([str(installed), "lifecycle", "identity"],
                                      capture_output=True, text=True, check=False)
            try:
                native_identity = json.loads(identity.stdout).get("identity")
            except (ValueError, AttributeError):
                native_identity = None
            compatible = identity.returncode == 0 and isinstance(native_identity, str) and native_identity.startswith("build:")
    if compatible:
        arguments = [str(installed), "install", "--keep-env", "--preserve-mcp"]
        config = installed.parent / "config.json"
        if config.is_file():
            arguments += ["--config", str(config)]
        if status.returncode == 0:
            arguments.append("--no-start")
        run(arguments)
    else:
        controller = runpy.run_path(str(ROOT / "bin/project-update"))
        projects = controller["load_projects"](ROOT / "config/project-updates.toml")
        checkout = projects["bedrock-router"]["path"]
        if not checkout.exists():
            checkout.parent.mkdir(parents=True, exist_ok=True)
            run(["git", "clone", "--", "https://github.com/lanej/bedrock-router.git", str(checkout)])
        command = [sys.executable, str(ROOT / "bin/project-update")]
        run([*command, "build", "bedrock-router"])
        arguments = [str(installed), "install", "--keep-env", "--preserve-mcp"]
        config = installed.parent / "config.json"
        if config.is_file():
            arguments += ["--config", str(config)]
        # The native installer verifies an absent owner before a cold start and refuses legacy replacement.
        run(arguments)
    run([str(installed), "status", "--quiet"])
    if sys.platform == "linux":
        user = str(os.getuid())
        lingering = run(["loginctl", "show-user", user, "-p", "Linger", "--value"],
                        capture_output=True).stdout.strip()
        if lingering != "yes":
            run(["loginctl", "enable-linger", user])
    print("Bedrock router is installed and healthy.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"bedrock-router setup failed: {error}")
