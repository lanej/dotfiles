"""Copy the standalone source boundary into a new, empty directory."""
from pathlib import Path
import json
from source_files import source_files, MANIFEST
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", "node_modules", ".aot", "__pycache__"}


def export(destination):
    destination = destination.resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("Export outside the source package")
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("Export destination must be empty")
    names = source_files(ROOT)
    for name in names:
        source = ROOT / name
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (destination / MANIFEST).write_text(json.dumps(sorted(set([*names, MANIFEST])), indent=2) + "\n")
    print(f"Exported standalone Pi driver source to {destination}")


if __name__ == "__main__":
    export(Path(sys.argv[1]))
