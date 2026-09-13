#!/usr/bin/env python3
"""One regression workflow: install the real pin, launch it, and use the project opt-in hook."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
pin = json.loads((root / "claude/ui-review/tool.json").read_text())
with tempfile.TemporaryDirectory(prefix="viewrule-integration-") as temporary:
    project = Path(temporary) / "app"
    project.mkdir()
    env = {**os.environ, "VIEWRULE_INSTALL_ROOT": str(Path(temporary) / "install")}
    env.pop("VIEWRULE_DEV_DIR", None)
    install = ["python3", str(root / "scripts/install-viewrule.py"), "--skip-browser"]
    if env.get("VIEWRULE_ARCHIVE"):
        install += ["--archive", env["VIEWRULE_ARCHIVE"]]
    subprocess.run(install, env=env, check=True)
    cli = str(root / "bin/ui-review")
    version = subprocess.check_output([cli, "--version"], env=env, text=True).strip()
    assert version == pin["version"], version
    decision = subprocess.check_output([cli, "hook"], input=json.dumps({"cwd": str(project)}), env=env, text=True)
    assert not decision.strip() or json.loads(decision) == {}, decision
    subprocess.run([cli, "init", "--project", str(project)], env=env, check=True)
    config_path = project / ".ui-review/config.json"
    config = json.loads(config_path.read_text())
    config["enforceOnStop"] = True
    config_path.write_text(json.dumps(config))
    decision = json.loads(subprocess.check_output([cli, "hook"], input=json.dumps({"cwd": str(project)}), env=env, text=True))
    assert decision.get("decision") == "block", decision
    print("PASS: pinned install launches; opted-in project blocks without a review.")
