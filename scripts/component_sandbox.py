"""Native repository-input isolation; unavailable enforcement is an error."""

import json
import re
from pathlib import Path
import shutil
import subprocess
import sys


def runtime_paths(python, tools):
    paths = [Path(path) for path in (
        "/usr", "/bin", "/sbin", "/lib", "/lib64", "/etc", "/private/etc",
        "/System", "/Library", "/private/var/select", "/opt/homebrew", "/opt/hostedtoolcache", "/dev")
        if Path(path).exists()]
    prefixes = subprocess.check_output(
        [str(python), "-c", "import json,sys; print(json.dumps([sys.prefix,sys.base_prefix]))"], text=True)
    paths.extend(Path(prefix) for prefix in json.loads(prefixes))
    for tool in tools:
        executable = shutil.which(tool)
        if executable:
            paths.extend([Path(executable), Path(executable).resolve()])
    # Keep /bin and /lib aliases: an empty Linux mount namespace needs ELF loader paths too.
    resolved = {path.absolute() for path in paths} | {path.resolve() for path in paths}
    # uv may point venv interpreters through its minor-version alias.
    for prefix in json.loads(prefixes):
        base = Path(prefix).resolve()
        for sibling in base.parent.iterdir():
            if sibling.is_symlink() and sibling.resolve() == base:
                resolved.add(sibling.absolute())
    if sys.platform == "darwin":
        resolved.update(Path(path) for path in ("/var", "/tmp", "/etc"))
    return sorted(resolved)


def sandbox_command(read, write, temporary, environment, denied=()):
    if sys.platform == "darwin":
        executable = shutil.which("sandbox-exec")
        if not executable:
            raise ValueError("sandbox-exec is required; input isolation cannot be disabled")

        def predicates(paths):
            return "(require-any " + " ".join(
                f"({'subpath' if path.is_dir() and not path.is_symlink() else 'literal'} {json.dumps(str(path.absolute()))})"
                for path in sorted(set(paths))) + ")"

        profile = temporary / "sandbox.sb"
        # dyld opens ancestor directories while locating its shared cache.
        metadata = set(read)
        for path in read:
            metadata.update(path.resolve().parents)
        metadata_predicates = "(require-any " + " ".join(
            f"(literal {json.dumps(str(path))})" for path in sorted(metadata)) + " " + predicates(read) + ")"
        mounts = subprocess.check_output(["/sbin/mount"], text=True)
        mountpoints = [Path(match.group(1)) for line in mounts.splitlines()
                       if (match := re.search(r" on (.+) \(", line))]
        mount_metadata = "(require-any " + metadata_predicates + " " + " ".join(
            f"(literal {json.dumps(str(path))})" for path in mountpoints) + ")"
        profile.write_text(
            "(version 1)\n(allow default)\n"
            f"(deny file-read-data (require-not {metadata_predicates}))\n"
            f"(deny file-read-metadata (require-not {mount_metadata}))\n"
            f"(deny file-write* (require-not {predicates([*write, Path('/dev')])}))\n"
            + "".join(f"(deny file-read* (subpath {json.dumps(str(path))}))\n" for path in denied)
            + "(deny network*)\n(allow network* (local unix-socket))\n")
        return [executable, "-f", str(profile)]
    if sys.platform == "linux":
        executable = shutil.which("bwrap")
        if not executable:
            raise ValueError("bubblewrap is required; install it with your OS package manager")
        command = [executable, "--unshare-user", "--unshare-pid", "--unshare-net", "--unshare-uts",
                   "--die-with-parent", "--new-session", "--cap-drop", "ALL",
                   "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp"]
        # Parent mounts precede children, and writable mounts override read-only ones.
        for path in sorted(set(read), key=lambda item: (len(item.parts), str(item))):
            path = path.absolute()
            if path == Path("/dev"):
                continue
            command.extend(["--ro-bind", str(path), str(path)])
        for path in sorted(set(write), key=str):
            command.extend(["--bind", str(path), str(path)])
        for path in denied:
            if any(path.is_relative_to(allowed) for allowed in read):
                command.extend(["--tmpfs", str(path)])
        command.extend(["--clearenv"])
        for key, value in sorted(environment.items()):
            command.extend(["--setenv", key, value])
        return command
    raise ValueError(f"unsupported sandbox platform: {sys.platform}")
