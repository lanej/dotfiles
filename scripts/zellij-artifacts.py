#!/usr/bin/env python3
"""Build immutable native Zellij artifacts with a compiled plugin image ID."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def immutable(source, kind, image_id=None, *, root=None):
    sha = digest(source)
    storage = Path.home() / ".local/lib/zellij" if root is None else root
    base = storage / kind / sha
    base.mkdir(parents=True, exist_ok=True)
    destination = base / source.name
    if destination.exists():
        if digest(destination) != sha:
            raise ValueError("Preserving a changed immutable Zellij artifact")
    else:
        with tempfile.NamedTemporaryFile(dir=base, delete=False) as staged:
            temporary = Path(staged.name)
            shutil.copyfile(source, temporary)
        temporary.chmod(0o555 if kind == "runtimes" else 0o444)
        temporary.replace(destination)
    if image_id is not None:
        receipt = base / "image.json"
        value = {"schema_version": 1, "image_id": image_id, "sha256": sha,
                 "path": str(destination)}
        if receipt.exists() and json.loads(receipt.read_text()) != value:
            raise ValueError("Preserving a changed immutable Zellij image receipt")
        if not receipt.exists():
            receipt.write_text(json.dumps(value) + "\n")
            receipt.chmod(0o444)
    return destination


def select(destination, source):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".zellij-select-", dir=destination.parent) as directory:
        staged = Path(directory) / destination.name
        staged.symlink_to(source)
        staged.replace(destination)


def plugin(name, source, target, destination):
    files = sorted(source.glob("src/**/*.rs")) + [source / "Cargo.toml"]
    lock = source / "Cargo.lock"
    if not lock.exists():
        lock = source.parent / "Cargo.lock"
    files.append(lock)
    shared = source.parent / "protocol"
    files += sorted(shared.glob("src/**/*.rs")) + [shared / "Cargo.toml"]
    generated = source.parent.parent / "design-system/generated"
    files.append(generated / "zellij-symbols.rs")
    if name == "lane-status":
        files.append(generated / "zellij-states.rs")
    hasher = hashlib.sha256(b"zellij-plugin-image-v1:rust-1.95.0:wasm32-wasip1\0")
    for file in sorted(set(files)):
        hasher.update(os.path.relpath(file, source.parent).encode())
        hasher.update(b"\0")
        hasher.update(file.read_bytes())
        hasher.update(b"\0")
    image = hasher.hexdigest()
    build_images = (target / "immutable").resolve()
    target = target / "activation-build"
    env = {**os.environ, "ZELLIJ_ACTIVATION_IMAGE_ID": image}
    subprocess.run(["rustup", "run", "1.95.0", "cargo", "build", "--locked", "--release",
                    "--target", "wasm32-wasip1", "--target-dir", str(target),
                    "--manifest-path", str(source / "Cargo.toml")], env=env, check=True)
    built = target / "wasm32-wasip1/release" / (name + ".wasm")
    stored = immutable(built, "plugins", image)
    # The shared build alias must outlive an installer's disposable HOME.
    # Each installation still owns its separate immutable plugin image.
    cached = immutable(built, "plugins", image, root=build_images)
    select(destination, cached)
    return stored


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "runtime":
        source = Path(sys.argv[2])
        selected = immutable(source, "runtimes")
        select(Path.home() / ".local/bin/zellij", selected)
    elif len(sys.argv) in (2, 5) and sys.argv[1] == "runtime-selected":
        selected = (Path.home() / ".local/bin/zellij").resolve()
        root = (Path.home() / ".local/lib/zellij/runtimes").resolve()
        if selected.parent.parent != root or selected.parent.name != digest(selected):
            raise ValueError("Selected immutable runtime image differs")
        if len(sys.argv) == 5:
            revision, toolchain, host = sys.argv[2:]
            receipt = selected.parent / "build.json"
            if receipt.is_symlink() or not receipt.is_file():
                raise ValueError("Selected curated runtime build receipt is unavailable")
            expected = {"schema_version": 1, "base_revision": revision, "activation_patch": None,
                        "toolchain": toolchain, "host": host, "sha256": digest(selected)}
            if json.loads(receipt.read_text()) != expected:
                raise ValueError("Selected runtime does not match the curated build")
    elif len(sys.argv) == 6 and sys.argv[1] == "plugin":
        plugin(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]))
    else:
        raise ValueError("Usage: zellij-artifacts.py runtime SOURCE | plugin NAME SOURCE TARGET DESTINATION")


if __name__ == "__main__":
    main()
