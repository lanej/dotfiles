"""Copy the standalone source boundary into a new, empty directory."""
from pathlib import Path
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
    for source in ROOT.rglob("*"):
        relative = source.relative_to(ROOT)
        if any(part in IGNORED for part in relative.parts):
            continue
        if source.is_symlink():
            raise ValueError(f"Refusing source symlink: {relative}")
        target = destination / relative
        if source.is_dir():
            target.mkdir(exist_ok=True)
        else:
            shutil.copy2(source, target)
    print(f"Exported standalone Pi driver source to {destination}")


if __name__ == "__main__":
    export(Path(sys.argv[1]))
