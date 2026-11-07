#!/usr/bin/env python3
"""Exercise the scheduled entrypoint against real npm and Go caches."""
import io
import json
import os
import shutil
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

        source = home / "program.go"
        source.write_text("package main\nfunc main() {}\n")
        env.update(GOTOOLCHAIN="local", GOWORK="off", GOENV="off")
        subprocess.run(["go", "run", str(source)], env=env,
                       check=True, capture_output=True)
        go_cache = home / "go"
        executable = next(p for p in go_cache.glob("*/*-d") if p.is_dir())
        outputs = sorted((p for p in go_cache.glob("*/*-d")
                          if p.is_file() and p.parent != executable.parent),
                         key=lambda p: p.stat().st_size, reverse=True)
        archives = []
        for output in outputs:
            with output.open("rb") as stream:
                if stream.read(8) == b"!<arch>\n":
                    archives.append(output)
        outputs = archives
        victim = outputs[0]
        held = outputs[1]
        recent = outputs[2]
        old = time.time() - 2 * 24 * 60 * 60
        if sys.platform == "darwin":
            os.utime(recent, (time.time() - 30 * 60, time.time() - 30 * 60))
        os.utime(victim, (old, old))
        os.utime(held, (old, old))
        os.utime(executable, (old, old))
        linked_bucket = home / ".local/bin/cache-snapshot"
        linked_bucket.parent.mkdir(parents=True)
        linked_bucket.symlink_to(executable.parent)
        unknown = go_cache / "fuzz/keep"
        unknown.parent.mkdir()
        unknown.write_text("keep fuzzing inputs")
        budgets = json.loads(config.read_text())
        budgets["go_build_gib"] = 0.000001
        config.write_text(json.dumps(budgets))
        # A persistent cache reader with the same process name as a language
        # server exercises the scheduler's process and open-file boundary.
        language_server = home / "gopls"
        language_server.symlink_to(shutil.which("tail"))
        reader = subprocess.Popen([str(language_server), "-f", str(held)], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(0.2)
            assert reader.poll() is None, "Persistent reader exited: " + str(reader.returncode)
            result = subprocess.run(
                [sys.executable, str(entrypoint), "--config", str(config), "--dry-run"],
                env=env, check=True, capture_output=True, text=True)
            assert victim.is_file(), result.stdout + result.stderr
            assert "Would trim" in result.stdout, result.stdout
            result = subprocess.run([sys.executable, str(entrypoint), "--config", str(config)],
                                    env=env, check=True, capture_output=True, text=True)
            assert not victim.exists(), result.stdout + result.stderr
            assert held.is_file(), "Open entry removed: " + result.stdout
            assert recent.is_file(), "Recent entry removed: " + result.stdout
            if sys.platform == "darwin":
                assert recent.stat().st_flags & 0x20, "Archive not compressed: " + result.stdout
                subprocess.run(["go", "tool", "nm", str(recent)], env=env, check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            assert executable.is_dir(), "Linked executable removed: " + result.stdout
            assert unknown.read_text() == "keep fuzzing inputs"
            assert "Soft limit:" in result.stdout, result.stdout
            source.write_text('package main\nfunc main() { println("compressed-cache-hit") }\n')
            rebuilt = subprocess.run(["go", "run", str(source)], env=env,
                                     check=True, capture_output=True, text=True)
            assert rebuilt.stderr == "compressed-cache-hit\n", rebuilt.stderr
        finally:
            reader.terminate()
            reader.wait(timeout=5)
    print("Cache budget entrypoint: busy cache deferred, idle cache pruned, installed tool retained")
    print("Go build budget: old entries trimmed with gopls running, protected entries retained, rebuild passed")


if __name__ == "__main__":
    main()
