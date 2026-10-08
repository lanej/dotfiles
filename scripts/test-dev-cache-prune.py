#!/usr/bin/env python3
"""Exercise the scheduled entrypoint against a real npm cache."""
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path


def main():
    entrypoint = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parents[1] / "bin/dev-cache-prune")
    with tempfile.TemporaryDirectory(prefix="dev-cache-test-") as folder:
        home = Path(folder).resolve()
        archive = home / "package.tgz"
        with tarfile.open(archive, "w:gz") as package:
            for name, data in (
                ("package/package.json", b'{"name":"cache-budget-test","version":"1.0.0"}'),
                ("package/content", os.urandom(65536)),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                package.addfile(info, io.BytesIO(data))
        cache = home / "npm"
        env = os.environ.copy()
        env.update(HOME=str(home), NPM_CONFIG_CACHE=str(cache),
                   UV_CACHE_DIR=str(home / "uv"), CARGO_HOME=str(home / "cargo"),
                   GOCACHE=str(home / "go"))
        env["GOMODCACHE"] = str(home / "modules")
        subprocess.run(["npm", "cache", "add", str(archive)], env=env,
                       check=True, capture_output=True)
        installed = cache / "_npx/tool/installed"
        installed.parent.mkdir(parents=True)
        installed.write_text("keep this installed tool")
        config = home / "budgets.json"
        config.write_text(json.dumps({
            "uv_gib": 4, "go_build_gib": 2, "go_modules_gib": 4, "cargo_gib": 2,
            "npm_gib": 0.000001, "rust_targets_gib": 8,
        }))
        payload = next((cache / "_cacache/content-v2").rglob("*"))
        while not payload.is_file():
            payload = next(payload.iterdir())
        reader = subprocess.Popen(["tail", "-f", str(payload)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(0.2)
            result = subprocess.run([sys.executable, str(entrypoint), "--config", str(config)],
                                    env=env, check=True, capture_output=True, text=True)
            assert payload.is_file(), result.stdout + result.stderr
            assert "Deferred: cache is in use" in result.stdout, result.stdout
        finally:
            reader.terminate()
            reader.wait(timeout=5)
        result = subprocess.run([sys.executable, str(entrypoint), "--config", str(config)],
                                env=env, check=True, capture_output=True, text=True)
        assert not (cache / "_cacache").exists(), result.stdout + result.stderr
        assert installed.read_text() == "keep this installed tool"
    print("Cache budget entrypoint: busy cache deferred, idle cache pruned, installed tool retained")


if __name__ == "__main__":
    main()
