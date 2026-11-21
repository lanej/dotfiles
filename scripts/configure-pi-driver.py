"""Register the opt-in local Pi package without changing providers or credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys

package = Path(sys.argv[1]).resolve()
agent = Path(os.environ.get("PI_CODING_AGENT_DIR", sys.argv[2]))
if not (package / "node_modules/tsx/dist/loader.mjs").is_file():
    raise SystemExit("Install the Pi driver dependencies explicitly with npm ci --ignore-scripts first.")
settings = agent / "settings.json"
if settings.is_symlink():
    raise SystemExit("Preserving linked Pi settings; add the local package through its source configuration.")
value = json.loads(settings.read_text()) if settings.exists() else {}
if not isinstance(value, dict):
    raise SystemExit("Pi settings must be an object; existing file preserved.")
packages = value.get("packages", [])
if not isinstance(packages, list):
    raise SystemExit("Pi packages must be an array; existing file preserved.")
theme = package.parents[1] / "design-system/generated/pi.json"
if not theme.is_file():
    raise SystemExit("Generate the shared Pi theme with make theme-generate first.")
theme_link = agent / "themes/dotfiles.json"
if theme_link.exists() and not theme_link.is_symlink():
    raise SystemExit("Preserving the local dotfiles.json theme; move it before configuring the managed theme.")
subprocess.run(["node", str(package / "scripts/prepare-delegation.mjs")], check=True)
theme_link.parent.mkdir(parents=True, exist_ok=True)
if theme_link.is_symlink():
    theme_link.unlink()
theme_link.symlink_to(theme)
if str(package) not in packages:
    value["packages"] = [*packages, str(package)]
value["theme"] = "dotfiles"
value["quietStartup"] = True
agent.mkdir(parents=True, exist_ok=True)
settings.write_text(json.dumps(value, indent=2) + "\n")
print("Registered the Pi driver. Task-bound dispatch remains disabled.")
