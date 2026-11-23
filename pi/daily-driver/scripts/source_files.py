"""Select reviewed Git sources or an exported snapshot's explicit manifest."""
import json
from pathlib import Path
import subprocess

MANIFEST = "source-files.json"
IGNORED = {".git", "node_modules", ".aot", "__pycache__"}


def source_files(root):
    root = root.resolve()
    names = None
    from_manifest = False
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", "package.json"], cwd=root, capture_output=True)
        if Path(top).resolve() == root or tracked.returncode == 0:
            output = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."], cwd=root, capture_output=True, check=True).stdout
            names = output.decode().split("\0")
    except (OSError, subprocess.CalledProcessError):
        pass
    if names is None:
        manifest = root / MANIFEST
        if not manifest.is_file():
            raise ValueError("Source selection requires a Git checkout or exported source-files.json manifest")
        from_manifest = True
        names = json.loads(manifest.read_text())
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            raise ValueError("Invalid source manifest")
    result = []
    for name in sorted(set(names)):
        if not name:
            continue
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise ValueError(f"Invalid source path: {name}")
        if any(part in IGNORED for part in relative.parts):
            continue
        source = root / relative
        if source.is_symlink():
            raise ValueError(f"Refusing source symlink: {name}")
        if not source.exists():
            if from_manifest:
                raise ValueError(f"Missing declared source: {name}")
            continue  # Preserve a checkout's deliberate tracked-file deletion.
        if source.is_symlink() or any(parent.is_symlink() for parent in source.parents if parent != root and root in parent.parents):
            raise ValueError(f"Refusing source symlink: {name}")
        if not source.is_file():
            raise ValueError(f"Source is not a regular file: {name}")
        result.append(name)
    return result


if __name__ == "__main__":
    print(json.dumps(source_files(Path(__file__).resolve().parents[1])))
