#!/usr/bin/env python3
"""Exercise opt-in resolution, installer delegation and isolated installation effects."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
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
from pathlib import Path
if sys.argv[1:] == ["--version"]:
    print("1.4.4")
else:
    with open(os.environ["TEST_OCTO_LOG"], "a") as output:
        output.write(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd()})+"\\n")
    if sys.argv[1] == "scripts/install-local.ts":
        current = Path(sys.argv[sys.argv.index("--home")+1]) / ".local/share/octo-manager/current"
        current.mkdir(parents=True, exist_ok=True)
        (current / "release.json").write_text(json.dumps({"revision":Path.cwd().name}))
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
            with patch.dict(os.environ, {"XDG_CACHE_HOME":str(home / ".cache")}), patch.object(installer.platform, "system", return_value="Darwin"), patch.object(installer.platform, "machine", return_value="arm64"), patch.object(installer, "download", side_effect=download):
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

    def test_make_install_reinstall_and_latest_select_their_exact_revisions(self):
        with tempfile.TemporaryDirectory(prefix="octo make ") as temporary:
            home, source, catalog, log, download, _ = self.fixture(temporary, installer.platform.system(), installer.platform.machine(), installer.platform.libc_ver()[0])
            with patch.object(installer, "download", side_effect=download):
                installer.runtime(home, source)
            (catalog / "scripts").mkdir()
            shutil.copyfile(ROOT / "scripts/install-octo-manager.py", catalog / "scripts/install-octo-manager.py")
            executables = Path(temporary) / "bin"
            executables.mkdir()
            real_git = shutil.which("git")
            latest_stage = source.parent / "latest-stage"
            def git_at(directory, *args):
                return subprocess.check_output([real_git, "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args], cwd=directory, text=True).strip()
            git_at(source.parent, "clone", "--quiet", "--shared", str(source), str(latest_stage))
            git_at(latest_stage, "remote", "set-url", "origin", installer.REPOSITORY)
            (latest_stage / "version.txt").write_text("Latest fixture\n")
            git_at(latest_stage, "add", "version.txt")
            git_at(latest_stage, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "Latest fixture")
            latest_source = source.parent / git_at(latest_stage, "rev-parse", "HEAD")
            latest_stage.rename(latest_source)
            self.assertNotEqual(source.name, latest_source.name)
            git = executables / "git"
            git.write_text(f"#!{sys.executable}\n" + f'''import os, sys
if sys.argv[1:2] == ["ls-remote"]:
    print(os.environ["TEST_LATEST_REV"]+"\\trefs/heads/main")
elif sys.argv[1:2] == ["fetch"]:
    sys.exit("Unexpected network fetch in cached fixture")
else:
    os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])
''')
            git.chmod(0o755)
            env = {**os.environ, "PATH": str(executables)+os.pathsep+os.environ["PATH"],
                   "XDG_CACHE_HOME":str(home / ".cache"), "TEST_OCTO_LOG":str(log),
                   "TEST_LATEST_REV":latest_source.name}
            for action, expected in (("install", source.name), ("reinstall", source.name), ("pull-latest", latest_source.name)):
                if action == "reinstall":
                    (catalog / "bootstrap/tools.toml").write_text(f'[tools.octo-manager]\nrevision = "{latest_source.name}"\n')
                elif action == "pull-latest":
                    (catalog / "bootstrap/tools.toml").write_text('[tools.octo-manager]\nrevision = "'+"0"*40+'"\n')
                result = subprocess.run(["make", "--no-print-directory", "-f", str(ROOT / "Makefile"),
                                         f"DOTFILES={catalog}", f"HOME={home}", f"octo-manager-{action}"],
                                        cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertEqual(json.loads((home / ".local/share/octo-manager/current/release.json").read_text())["revision"], expected)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual([Path(call["cwd"]).resolve() for call in calls], [source.resolve()] * 4 + [latest_source.resolve()] * 2)

    def test_latest_rejects_unidentified_heads_and_reinstall_requires_metadata(self):
        with patch.object(installer, "run", return_value="not-a-commit\trefs/heads/main"):
            with self.assertRaisesRegex(ValueError, "exact Octo main revision"):
                installer.latest_revision()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "octo-manager-install"):
                installer.installed_revision(Path(temporary))


SERVICE_BOUNDARY = '''import json, os, sys
from pathlib import Path
path = Path(os.environ["TEST_OCTO_SERVICE"])
state = json.loads(path.read_text())
command, args = Path(sys.argv[0]).name, sys.argv[1:]
state["calls"].append([command,*args])
path.write_text(json.dumps(state))
if state["fail"]:
    sys.exit(17)
if command == "launchctl":
    target = f"gui/{os.getuid()}/com.lanej.octo-manager"
    if args == ["print",target]:
        sys.exit(0 if state["running"] else 1)
    if args == ["enable",target]:
        state["enabled"] = True
    elif args == ["bootstrap",f"gui/{os.getuid()}",os.environ["TEST_OCTO_DEFINITION"]]:
        state["running"] = True
        state["generation"] += 1
    elif args == ["kickstart",target]:
        if not state["running"]:
            state["running"] = True
            state["generation"] += 1
    elif args == ["kickstart","-k",target]:
        state["running"] = True
        state["generation"] += 1
    else:
        sys.exit(2)
elif command == "systemctl":
    if args == ["--user","daemon-reload"]:
        pass
    elif args == ["--user","enable",os.environ["TEST_OCTO_DEFINITION"]]:
        state["enabled"] = True
    elif args == ["--user","start","octo-manager.service"]:
        if not state["running"]:
            state["generation"] += 1
        state["running"] = True
    elif args == ["--user","restart","octo-manager.service"]:
        state["running"] = True
        state["generation"] += 1
    else:
        sys.exit(2)
else:
    sys.exit(2)
path.write_text(json.dumps(state))
'''


class ServiceManagement(unittest.TestCase):
    def test_real_make_start_is_idempotent_restart_replaces_and_failures_propagate(self):
        with tempfile.TemporaryDirectory(prefix="octo service ") as temporary:
            root = Path(temporary)
            home, config, executables = root / "home", root / "config", root / "bin"
            if installer.platform.system() == "Darwin":
                definition = home / "Library/LaunchAgents/com.lanej.octo-manager.plist"
            else:
                definition = config / "systemd/user/octo-manager.service"
            definition.parent.mkdir(parents=True)
            definition.write_text("controlled service definition\n")
            executables.mkdir()
            for name in ("launchctl", "systemctl"):
                command = executables / name
                command.write_text(f"#!{sys.executable}\n"+SERVICE_BOUNDARY)
                command.chmod(0o755)
            state = root / "state.json"
            state.write_text(json.dumps({"running":False,"enabled":False,"generation":0,"calls":[],"fail":False,"unrelated":{"running":True}}))
            env = {**os.environ,"PATH":str(executables)+os.pathsep+os.environ["PATH"],
                   "XDG_CONFIG_HOME":str(config),"TEST_OCTO_SERVICE":str(state),
                   "TEST_OCTO_DEFINITION":str(definition if installer.platform.system() == "Darwin" else definition.resolve())}
            def invoke(action):
                return subprocess.run(["make","--no-print-directory",f"HOME={home}",f"octo-manager-{action}"],
                                      cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
            for action, generation in (("start",1),("start",1),("restart",2)):
                result = invoke(action)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                observed = json.loads(state.read_text())
                self.assertTrue(observed["running"] and observed["enabled"])
                self.assertEqual(observed["generation"],generation)
                self.assertEqual(observed["unrelated"],{"running":True})
            observed.update(running=False, enabled=False, generation=0, calls=[])
            state.write_text(json.dumps(observed))
            for action in ("restart", "start"):
                result = invoke(action)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                observed = json.loads(state.read_text())
                self.assertTrue(observed["running"] and observed["enabled"])
                self.assertEqual(observed["generation"],1)
                self.assertEqual(observed["unrelated"],{"running":True})
            observed["fail"] = True
            state.write_text(json.dumps(observed))
            self.assertNotEqual(invoke("restart").returncode,0)
            calls = json.loads(state.read_text())["calls"]
            definition.unlink()
            result = invoke("start")
            self.assertNotEqual(result.returncode,0)
            self.assertIn("octo-manager-install",result.stderr)
            self.assertEqual(json.loads(state.read_text())["calls"],calls)


if __name__ == "__main__":
    unittest.main()
