#!/usr/bin/env python3
"""Check that shared plugin builds survive a disposable installation HOME."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def check_plugins(artifacts, source):
    with tempfile.TemporaryDirectory(prefix="zellij-artifacts-") as temporary:
        work = Path(temporary)
        fixture = work / "bin"
        fixture.mkdir()
        rustup = fixture / "rustup"
        rustup.write_text(f"#!{sys.executable}\n" + '''
import os
from pathlib import Path
import sys
target = Path(sys.argv[sys.argv.index("--target-dir") + 1])
output = target / "wasm32-wasip1/release/lane-status.wasm"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(b"fixture wasm\\0" + os.environ["ZELLIJ_ACTIVATION_IMAGE_ID"].encode())
''')
        rustup.chmod(0o755)
        target = work / "build"
        selected = target / "wasm32-wasip1/release/lane-status.wasm"
        homes = [work / "persistent-home", work / "disposable-home"]
        installed = []
        for index, home in enumerate(homes):
            home.mkdir()
            env = {**os.environ, "HOME": str(home),
                   "PATH": str(fixture) + os.pathsep + os.environ["PATH"]}
            build_target = target if index == 0 else target.relative_to(work)
            destination = selected if index == 0 else selected.relative_to(work)
            subprocess.run([sys.executable, str(artifacts), "plugin", "lane-status",
                            str(source), str(build_target), str(destination)], env=env, cwd=work,
                           check=True, timeout=30)
            images = list((home / ".local/lib/zellij/plugins").glob("*/lane-status.wasm"))
            assert len(images) == 1, "The installation must retain its immutable plugin image"
            installed.append(images[0])
        expected = installed[0].read_bytes()
        shutil.rmtree(homes[1])
        assert selected.exists(), "The shared plugin build alias died with a disposable HOME"
        assert selected.read_bytes() == expected, "The shared plugin build changed its bytes"
        assert installed[0].read_bytes() == expected, "A later install changed the earlier image"
    print("PASS shared Zellij plugin build survives disposable HOME cleanup")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    check_plugins(root / "scripts/zellij-artifacts.py", root / "zellij/status")
