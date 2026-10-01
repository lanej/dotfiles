#!/usr/bin/env python3
"""Install the Bedrock router and configure this user's Codex."""

import argparse
import datetime
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import tomllib


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Write configuration and service files without starting the service",
    )
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("Python 3.11 or newer is required")
    if sys.platform not in ("darwin", "linux"):
        parser.error("Only macOS and Linux are supported")
    source = Path(__file__).resolve().parent
    root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    root.mkdir(parents=True, exist_ok=True)
    credentials = Path.home() / ".config/bedrock/env"
    if not credentials.is_file():
        parser.error("Set up your private ~/.config/bedrock/env first; see README.md")
    if credentials.stat().st_mode & 0o077:
        parser.error("Run chmod 600 ~/.config/bedrock/env first")
    env = root / ".env"
    if (env.exists() or env.is_symlink()) and env.resolve() != credentials.resolve():
        parser.error(
            "Existing .codex/.env uses another source; merge it manually before installing"
        )

    config = root / "config.toml"
    text = config.read_text() if config.exists() else ""
    previous = tomllib.loads(text)
    provider = previous.get("model_providers", {}).get("amazon-bedrock", {})
    if set(provider) - {"base_url", "aws"} or set(provider.get("aws", {})) - {"region"}:
        parser.error(
            "Existing Bedrock provider has additional settings; merge them manually"
        )
    first_table = re.search(r"(?m)^\s*\[", text)
    index = first_table.start() if first_table else len(text)
    top, tables = text[:index], text[index:]
    for key, value in {
        "model_provider": "amazon-bedrock",
        "model_reasoning_summary": "none",
        "web_search": "cached",
    }.items():
        line = f"{key} = {json.dumps(value)}"
        if re.search(rf"(?m)^{key}\s*=", top):
            top = re.sub(rf"(?m)^{key}\s*=.*$", line, top)
        else:
            top = top.rstrip() + "\n" + line + "\n"
    if "model" not in previous:
        top += 'model = "openai.gpt-6.1-sol"\n'
    for header in (
        "model_providers.amazon-bedrock",
        "model_providers.amazon-bedrock.aws",
    ):
        pattern = rf"(?ms)^\[{re.escape(header)}\]\s*\n.*?(?=^\[|\Z)"
        tables = re.sub(pattern, "", tables)
    updated = (
        top.rstrip()
        + "\n\n"
        + tables.rstrip()
        + "\n\n[model_providers.amazon-bedrock]\n"
        + 'base_url = "http://127.0.0.1:18081/openai/v1"\n\n'
        + '[model_providers.amazon-bedrock.aws]\nregion = "us-west-2"\n'
    )
    tomllib.loads(updated)
    backup = (
        root
        / "backups"
        / (
            "bedrock-router-"
            + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        )
    )
    backup.mkdir(parents=True, mode=0o700)
    if config.exists():
        shutil.copy2(config, backup / "config.toml")
        (backup / "config.toml").chmod(0o600)
    config.write_text(updated)
    if not env.is_symlink():
        env.symlink_to(credentials)
    runtime = root / "bedrock-router"
    runtime.mkdir(mode=0o700, exist_ok=True)
    # Preserve runtime logs; source comes from the checkout on every install.
    for name in ("router.py", "test_router.py"):
        shutil.copy2(source / name, runtime / name)
    executable = str(Path(sys.executable).resolve())
    if sys.platform == "darwin":
        label = "com.joshlane.codex.bedrock-router"
        service = Path.home() / "Library/LaunchAgents" / (label + ".plist")
        service.parent.mkdir(parents=True, exist_ok=True)
        service.write_bytes(
            plistlib.dumps(
                {
                    "Label": label,
                    "ProgramArguments": [
                        executable,
                        "-u",
                        str(runtime / "router.py"),
                        "--port",
                        "18081",
                    ],
                    "WorkingDirectory": str(runtime),
                    "RunAtLoad": True,
                    "KeepAlive": True,
                    "ThrottleInterval": 5,
                    "ProcessType": "Background",
                    "StandardOutPath": str(runtime / "router.log"),
                    "StandardErrorPath": str(runtime / "router.err.log"),
                }
            )
        )
        service.chmod(0o600)
        if not args.no_start:
            domain = f"gui/{os.getuid()}"
            subprocess.run(
                ["launchctl", "bootout", f"{domain}/{label}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            run("launchctl", "bootstrap", domain, str(service))
    else:
        service = Path.home() / ".config/systemd/user/codex-bedrock-router.service"
        service.parent.mkdir(parents=True, exist_ok=True)
        ca = next(
            (
                p
                for p in (
                    "/etc/pki/tls/certs/ca-bundle.crt",
                    "/etc/ssl/certs/ca-certificates.crt",
                    "/etc/ssl/cert.pem",
                )
                if Path(p).is_file()
            ),
            None,
        )
        ca_line = f"Environment=SSL_CERT_FILE={ca}\n" if ca else ""
        service.write_text(
            "[Unit]\nDescription=Codex Bedrock routing by model\n\n[Service]\n"
            + ca_line
            + f'ExecStart="{executable}" -u "{runtime / "router.py"}" --port 18081\n'
            + f'WorkingDirectory="{runtime}"\n'
            + "Restart=always\nRestartSec=3\nUMask=0077\nNoNewPrivileges=yes\nPrivateTmp=yes\n"
            + "\n[Install]\nWantedBy=default.target\n"
        )
        service.chmod(0o600)
        if not args.no_start:
            run("systemctl", "--user", "daemon-reload")
            run("systemctl", "--user", "enable", "codex-bedrock-router.service")
            run("systemctl", "--user", "restart", "codex-bedrock-router.service")
    if not args.no_start:
        for attempt in range(40):
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:18081/healthz", timeout=2
                ) as response:
                    health = json.load(response)
                if health.get("model_regions") != {"openai.gpt-6.1-sol": "us-east-1"}:
                    raise RuntimeError("Unexpected router configuration")
                print(json.dumps(health))
                break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError("Router failed to start")
    print(f"Installed Bedrock router. Original Codex config: {backup / 'config.toml'}")


if __name__ == "__main__":
    main()
