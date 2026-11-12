#!/usr/bin/env python3
"""Exercise opt-in resolution, installer delegation and isolated installation effects."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("octo_install", ROOT / "scripts/install-octo-manager.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installation(unittest.TestCase):
    def fixture(self, temporary, system="Darwin",machine="arm64",libc="glibc"):
        root = Path(temporary)
        home, repository, catalog = root / "home", root / "repo", root / "catalog"
        repository.mkdir()
        (repository / ".bun-version").write_text("1.4.4\n")
        (repository / "scripts").mkdir()
        (repository / "scripts/install-local.ts").write_text("controlled upstream entrypoint\n")
        def git(*args):
            return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args], cwd=repository, text=True).strip()
        git("init", "--quiet")
        git("remote", "add", "origin", installer.REPOSITORY)
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "Fixture")
        revision = git("rev-parse", "HEAD")
        artifact_name,target=installer.runtime_target(system,machine,libc)
        cache = home / ".cache/dotfiles/octo-manager" / target
        cache.mkdir(parents=True)
        source = cache / revision
        repository.rename(source)
        (catalog / "bootstrap").mkdir(parents=True)
        (catalog / "bootstrap/tools.toml").write_text(f'[tools.octo-manager]\nrevision = "{revision}"\n')
        log = root / "calls.jsonl"
        binary = f'#!{sys.executable}\n' + '''import json, os, sys
if sys.argv[1:] == ["--version"]:
    print("1.4.4")
else:
    with open(os.environ["TEST_OCTO_LOG"], "a") as output:
        output.write(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd()})+"\\n")
    print('{"installed":true}')
'''
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(artifact_name+"/bun", binary)
        artifact = buffer.getvalue()
        downloads = []
        def download(url, destination):
            downloads.append(url)
            if url.endswith("SHASUMS256.txt"):
                destination.write_text(hashlib.sha256(artifact).hexdigest()+"  "+artifact_name+".zip\n")
            else:
                destination.write_bytes(artifact)
        return home, source, catalog, log, download, downloads

    def test_install_reuses_verified_runtime_and_delegates_hooks_each_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            home, source, catalog, log, download, downloads = self.fixture(temporary)
            with patch.dict(os.environ, {"XDG_CACHE_HOME":str(home / ".cache"), "TEST_OCTO_LOG":str(log)}), patch.object(installer.platform, "system", return_value="Darwin"), patch.object(installer.platform, "machine", return_value="arm64"), patch.object(installer, "download", side_effect=download), contextlib.redirect_stdout(io.StringIO()):
                installer.install(catalog, home)
                installer.install(catalog, home)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(downloads), 2)
            self.assertEqual([call["args"] for call in calls], [["install","--frozen-lockfile","--ignore-scripts"], ["scripts/install-local.ts","--home",str(home),"--codex"]] * 2)
            self.assertTrue(all(Path(call["cwd"]).resolve() == source.resolve() for call in calls))
            self.assertFalse((source.parent / ".install-lock").exists())

    def test_checksum_failure_prevents_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            home, source, catalog, log, download, _ = self.fixture(temporary)
            def corrupt(url, destination):
                download(url, destination)
                if url.endswith(".zip"):
                    destination.write_bytes(b"wrong archive")
            with patch.dict(os.environ, {"XDG_CACHE_HOME":str(home / ".cache")}), patch.object(installer.platform, "system", return_value="Darwin"), patch.object(installer.platform, "machine", return_value="arm64"), patch.object(installer, "download", side_effect=corrupt):
                with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                    installer.install(catalog, home)
            self.assertFalse(log.exists())
            self.assertFalse((home / ".local/share/octo-manager/runtime/darwin-arm64/bun-1.4.4/bun").exists())
            self.assertFalse((source.parent / ".install-lock").exists())

    def test_modified_cache_and_unsupported_platform_fail_before_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            home, source, catalog, log, download, downloads = self.fixture(temporary)
            with patch.object(installer.platform, "system", return_value="Windows"):
                with self.assertRaisesRegex(ValueError, "Unsupported Octo platform"):
                    installer.install(catalog, home)
            (source / ".bun-version").write_text("modified\n")
            with patch.dict(os.environ, {"XDG_CACHE_HOME":str(home / ".cache")}), patch.object(installer.platform, "system", return_value="Darwin"), patch.object(installer, "download", side_effect=download):
                with self.assertRaisesRegex(ValueError, "modified or unrecognized"):
                    installer.install(catalog, home)
            self.assertFalse(downloads)
            self.assertFalse(log.exists())

    def test_linux_artifact_selection_and_hook_delegation(self):
        cases=[("arm64","glibc","bun-linux-aarch64"),("x86_64","glibc","bun-linux-x64-baseline"),("arm64","musl","bun-linux-aarch64-musl"),("x86_64","musl","bun-linux-x64-musl-baseline")]
        for machine,libc,expected in cases:
            with self.subTest(machine=machine,libc=libc), tempfile.TemporaryDirectory() as temporary:
                home,source,catalog,log,download,downloads=self.fixture(temporary,"Linux",machine,libc)
                with patch.dict(os.environ,{"XDG_CACHE_HOME":str(home/".cache"),"TEST_OCTO_LOG":str(log)}), patch.object(installer.platform,"system",return_value="Linux"),patch.object(installer.platform,"machine",return_value=machine),patch.object(installer.platform,"libc_ver",return_value=(libc,"")),patch.object(installer,"download",side_effect=download),contextlib.redirect_stdout(io.StringIO()):
                    installer.install(catalog,home)
                self.assertTrue(downloads[-1].endswith(expected+".zip"))
                calls=[json.loads(line) for line in log.read_text().splitlines()]
                self.assertEqual(calls[-1]["args"],["scripts/install-local.ts","--home",str(home),"--codex"])

    def test_real_bootstrap_dispatch_stops_on_installer_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "calls"
            script = '''source "$1"
install_config_runtime() { :; }
load_dotfiles_config() { DOTFILES_INSTALL_PLAN=$'octo-manager\\tocto-manager\\tocto-manager\\t-\\nnext\\tpackage\\tnext\\t1'; }
python3() { printf '%s\\n' "$*" >> "$TEST_LOG"; return 17; }
install_package_version() { printf 'unexpected next tool\\n' >> "$TEST_LOG"; }
install_dependencies
'''
            result = subprocess.run(["bash", "-c", script, "test", str(ROOT / "bootstrap.sh")], env={**os.environ,"TEST_LOG":str(log)}, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(log.read_text().strip(), str(ROOT / "scripts/install-octo-manager.py"))


if __name__ == "__main__":
    unittest.main()
