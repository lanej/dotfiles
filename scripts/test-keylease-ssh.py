#!/usr/bin/env python3
"""Exercise configuration through Make and real ssh -G, with a synthetic Keylease."""
import os
from pathlib import Path
import platform
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if platform.system() != "Darwin":
        print("SKIP: outgoing native approval configuration is macOS-only")
        return
    with tempfile.TemporaryDirectory(prefix="kl config test-", dir="/tmp") as temporary:
        home = Path(temporary)
        binary = home / ".local/bin/keylease"
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh\necho '-control string' >&2\n")
        binary.chmod(0o755)
        helper = binary.parent / "Approval.app/Contents/MacOS/Approval"
        helper.parent.mkdir(parents=True)
        helper.touch()
        env = {**os.environ, "HOME": str(home)}
        config = home / ".ssh/config"
        config.parent.mkdir(mode=0o700)
        original = 'Host *\n    IdentityAgent "/existing/1password.sock"\n\nHost personal\n    HostName 127.0.0.1\n    User existing\n'
        config.write_text(original)

        def make(target="keylease-ssh", ok=True):
            result = subprocess.run(["make", "--no-print-directory", target, f"HOME={home}", f"KEYLEASE_BINARY={binary}"], cwd=ROOT, env=env, capture_output=True, text=True)
            assert (result.returncode == 0) == ok, result.stdout + result.stderr
            return result

        def effective(host="personal"):
            output = subprocess.run(["ssh", "-G", "-F", str(config), host], env=env, check=True, capture_output=True, text=True).stdout
            return dict(line.split(" ", 1) for line in output.splitlines() if " " in line)

        make()
        first = config.read_text()
        assert first.startswith(original), "user SSH configuration changed"
        values = effective()
        assert values["identityagent"] == "/existing/1password.sock", values
        assert values["hostname"] == "127.0.0.1" and values["user"] == "existing", values
        assert values["controlmaster"] == "auto" and values["controlpersist"] == "30", values
        assert str(binary) in values["localcommand"] and "ssh-hook" in values["localcommand"], values
        make()
        assert config.read_text() == first, "setup is not idempotent"
        assert config.with_name("config.before-keylease").read_text() == original, "original backup changed"
        make("keylease-ssh-remove")
        assert config.read_text() == original, "removal did not preserve user config"
        # Keep symlinked SSH configs linked to their actual source.
        source = home / "source-config"
        source.write_text(original)
        config.unlink()
        config.symlink_to(source)
        make()
        assert config.is_symlink() and source.read_text().startswith(original)
        make("keylease-ssh-remove")
        assert source.read_text() == original
        source.write_text(original.rstrip("\n"))
        make()
        make("keylease-ssh-remove")
        assert source.read_text() == original.rstrip("\n"), "removal changed the original final newline"
        source.write_text(original + "\nHost *\n    ControlMaster no\n")
        before = source.read_text()
        make(ok=False)
        assert source.read_text() == before, "conflicting setup changed config"
        source.write_text(original)
        binary.unlink()
        make(ok=False)
        assert source.read_text() == original, "missing dependency changed config"
        print("PASS: real SSH config preserves identities and host settings, converges, removes cleanly, preserves symlinks and rejects missing/conflicting setup.")


if __name__ == "__main__":
    main()
