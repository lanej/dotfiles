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

import bun_runtime

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("octo_install", ROOT / "scripts/install-octo-manager.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installation(unittest.TestCase):
    def fixture(self, temporary, system=None, machine=None):
        root = Path(temporary)
        home, repository, catalog = root / "home", root / "repo", root / "catalog"
        repository.mkdir()
        (repository / "package.json").write_text('{"engines":{"bun":">=1.4.4"}}\n')
        (repository / "scripts").mkdir()
        (repository / "scripts/install-local.ts").write_text("controlled upstream entrypoint\n")
        def git(*args):
            return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args], cwd=repository, text=True).strip()
        git("init", "--quiet")
        git("remote", "add", "origin", installer.REPOSITORY)
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "Fixture")
        revision = git("rev-parse", "HEAD")
        _, target = bun_runtime.runtime_target(system or installer.platform.system(), machine or installer.platform.machine(), "glibc")
        cache = home / ".cache/dotfiles/octo-manager" / target
        cache.mkdir(parents=True)
        source = cache / revision
        repository.rename(source)
        (catalog / "bootstrap").mkdir(parents=True)
        (catalog / "bootstrap/tools.toml").write_text(f'[tools.octo-manager]\nrevision = "{revision}"\n')
        log = root / "calls.jsonl"
        binary = home / ".local/bin/bun"
        binary.parent.mkdir(parents=True)
        binary.write_text(f'#!{sys.executable}\n' + '''import json, os, sys
from pathlib import Path
if sys.argv[1:] == ["--version"]:
    print(os.environ.get("TEST_BUN_VERSION", "1.10.0"))
else:
    with open(os.environ["TEST_OCTO_LOG"], "a") as output:
        output.write(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd()})+"\\n")
    if sys.argv[1] == "scripts/install-local.ts":
        current = Path(sys.argv[sys.argv.index("--home")+1]) / ".local/share/octo-manager/current"
        current.mkdir(parents=True, exist_ok=True)
        (current / "release.json").write_text(json.dumps({"revision":Path.cwd().name}))
    print('{"installed":true}')
''')
        binary.chmod(0o755)
        env = {"HOME": str(home), "PATH": str(binary.parent) + os.pathsep + os.environ["PATH"],
               "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache"), "TEST_OCTO_LOG": str(log)}
        return home, source, catalog, log, env

    def test_install_reuses_newer_shared_runtime_and_registers_minimum(self):
        with tempfile.TemporaryDirectory() as temporary:
            home, source, catalog, log, env = self.fixture(temporary)
            binary = home / ".local/bin/bun"
            before = binary.read_bytes()
            with patch.dict(os.environ, env), contextlib.redirect_stdout(io.StringIO()):
                installer.install(catalog, home)
                installer.install(catalog, home)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual([call["args"] for call in calls], [["install","--frozen-lockfile","--ignore-scripts"], ["scripts/install-local.ts","--home",str(home),"--codex"]] * 2)
            self.assertTrue(all(Path(call["cwd"]).resolve() == source.resolve() for call in calls))
            self.assertEqual(binary.read_bytes(), before)
            self.assertFalse((home / ".local/share/octo-manager/runtime").exists())
            declaration = home / ".config/dotfiles/runtime-requirements.d/octo-manager.json"
            self.assertEqual(json.loads(declaration.read_text())["engines"], {"bun": ">=1.4.4"})
            self.assertFalse((source.parent / ".install-lock").exists())

    def test_runtime_failure_does_not_activate_or_register_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            home, source, catalog, log, env = self.fixture(temporary)
            with patch.dict(os.environ, env), patch.object(installer, "ensure_runtime", side_effect=ValueError("Bun unavailable")):
                with self.assertRaisesRegex(ValueError, "Bun unavailable"):
                    installer.install(catalog, home)
            self.assertFalse(log.exists())
            self.assertFalse((home / ".config/dotfiles/runtime-requirements.d/octo-manager.json").exists())
            self.assertFalse((source.parent / ".install-lock").exists())

    def test_modified_cache_and_unsupported_platform_fail_before_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            home, source, catalog, log, env = self.fixture(temporary)
            with patch.object(installer.platform, "system", return_value="Windows"):
                with self.assertRaisesRegex(ValueError, "Unsupported Bun platform"):
                    installer.install(catalog, home)
            (source / "package.json").write_text("modified\n")
            with patch.dict(os.environ, env):
                with self.assertRaisesRegex(ValueError, "modified or unrecognized"):
                    installer.install(catalog, home)
            self.assertFalse(log.exists())
            failed = subprocess.run([sys.executable, str(ROOT / "scripts/install-octo-manager.py"), "reinstall", "--home", str(home)], text=True, capture_output=True, env={**os.environ, **env})
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Octo is not installed; run make octo-manager-install", failed.stderr)
            self.assertNotIn("Traceback", failed.stderr)

    def test_real_bootstrap_dispatch_stops_on_installer_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "calls"
            script = '''source "$1"
install_config_runtime() { :; }
load_dotfiles_config() { DOTFILES_TOOLS=octo-manager; DOTFILES_INSTALL_PLAN=$'octo-manager\\tocto-manager\\tocto-manager\\t-\\nnext\\tpackage\\tnext\\t1'; }
python3() { printf '%s\\n' "$*" >> "$TEST_LOG"; case "$1" in *prepare-project-runtimes.py) return 0;; *) return 17;; esac; }
install_package_version() { printf 'unexpected next tool\\n' >> "$TEST_LOG"; }
install_dependencies
'''
            result = subprocess.run(["bash", "-c", script, "test", str(ROOT / "bootstrap.sh")], env={**os.environ,"TEST_LOG":str(log)}, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(log.read_text().splitlines()[-1], str(ROOT / "scripts/install-octo-manager.py"))
            self.assertEqual(len(log.read_text().splitlines()), 2)

    def test_make_install_reinstall_and_latest_select_their_exact_revisions(self):
        with tempfile.TemporaryDirectory(prefix="octo make ") as temporary:
            home, source, catalog, log, env = self.fixture(temporary)
            (catalog / "scripts").mkdir()
            for name in ("install-octo-manager.py", "bun_runtime.py", "runtime_requirements.py"):
                shutil.copyfile(ROOT / "scripts" / name, catalog / "scripts" / name)
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
            env = {**os.environ, **env, "PATH": str(executables)+os.pathsep+env["PATH"], "TEST_LATEST_REV":latest_source.name}
            for action, expected in (("install", source.name), ("reinstall", source.name), ("pull-latest", latest_source.name)):
                if action == "reinstall":
                    (catalog / "bootstrap/tools.toml").write_text(f'[tools.octo-manager]\nrevision = "{latest_source.name}"\n')
                elif action == "pull-latest":
                    (catalog / "bootstrap/tools.toml").write_text('[tools.octo-manager]\nrevision = "'+"0"*40+'"\n')
                result = subprocess.run(["make", "--no-print-directory", "-f", str(ROOT / "Makefile"), f"DOTFILES={catalog}", f"HOME={home}", f"octo-manager-{action}"],
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


class SharedBun(unittest.TestCase):
    def test_selected_projects_share_highest_minimum_before_installation(self):
        import runpy

        preparation = runpy.run_path(str(ROOT / "scripts/prepare-project-runtimes.py"))
        load_adapter = runpy.run_path
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            sources = {project: home / project for project in ("studio", "octo-manager")}
            expected = {"projects": {}}
            for project, minimum in (("studio", ">=1.9.0"), ("octo-manager", ">=1.10.0")):
                source = sources[project]
                source.mkdir()
                (source / "package.json").write_text(json.dumps({"engines": {"bun": minimum}}))
                expected["projects"][project] = {"engines": {"bun": minimum}, "source": str(source / "package.json")}

            def adapter(path):
                namespace = load_adapter(path)
                if Path(path).name == "install-studio.py":
                    namespace["checkout"] = lambda: sources["studio"]
                else:
                    self.assertEqual(Path(path).name, "install-octo-manager.py")
                    namespace["prepare_source"] = lambda: sources["octo-manager"]
                return namespace

            with patch.object(runpy, "run_path", side_effect=adapter):
                prepared = preparation["prepare"](set(sources))
            self.assertEqual(prepared, expected)
            requirements = home / "prepared.json"
            requirements.write_text(json.dumps(prepared))
            config = home / "machine.toml"
            config.write_text("[tools]\nstudio = true\nocto-manager = true\n")
            env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
                   "DOTFILES_CONFIG": str(config)}
            env.pop("DOTFILES_RUNTIME_REQUIREMENTS_FILE", None)
            script = '''source "$1"
DOTFILES_RUNTIME_REQUIREMENTS_FILE="$2" load_dotfiles_config || exit
printf '%s\\n' "$DOTFILES_INSTALL_PLAN"
'''
            result = subprocess.run(["bash", "-c", script, "preflight-test", str(ROOT / "bootstrap.sh"), str(requirements)],
                                    env=env, text=True, capture_output=True, check=True)
            rows = [line.split("\t") for line in result.stdout.splitlines()]
            self.assertEqual([row for row in rows if row[0] == "bun"], [["bun", "package", "bun", "1.10.0"]])
            names = [row[0] for row in rows]
            self.assertLess(names.index("bun"), names.index("studio"))
            self.assertLess(names.index("bun"), names.index("octo-manager"))
            self.assertFalse((home / ".config/dotfiles/runtime-requirements.d").exists())

    def test_fallback_preserves_unrecognized_executables_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            binary = home / ".local/bin/bun"
            binary.parent.mkdir(parents=True)
            original = b"#!/bin/sh\nprintf '%s\\n' 'custom bun wrapper'\n"
            binary.write_bytes(original)
            binary.chmod(0o755)
            def unexpected_download(*args):
                self.fail("Preserving an existing executable must not download a replacement")
            with patch.dict(os.environ, {"PATH": str(binary.parent)}):
                with self.assertRaisesRegex(ValueError, "Preserve unrecognized Bun executable"):
                    bun_runtime.install_release("1.4.5", home, fetch=unexpected_download)
                self.assertEqual(binary.read_bytes(), original)
                target = home / "system-bun"
                target.write_bytes(b"#!/bin/sh\nprintf '%s\\n' '1.4.4'\n")
                target.chmod(0o755)
                target_contents = target.read_bytes()
                binary.unlink()
                binary.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "package-manager-owned Bun symlink"):
                    bun_runtime.install_release("1.4.5", home, fetch=unexpected_download)
                self.assertTrue(binary.is_symlink())
                self.assertEqual(binary.readlink(), target)
                self.assertEqual(target.read_bytes(), target_contents)

    def test_checks_reject_missing_old_prerelease_and_accept_newer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "bun"
            with self.assertRaisesRegex(ValueError, "required on PATH"):
                bun_runtime.installed_bun("1.4.5", path=str(root))
            for version, accepted in (("1.4.4", False), ("1.4.5-canary", False), ("1.4.5", True), ("1.10.0", True)):
                binary.write_text(f"#!/bin/sh\nprintf '%s\\n' '{version}'\n")
                binary.chmod(0o755)
                if accepted:
                    self.assertEqual(bun_runtime.installed_bun("1.4.5", path=str(root)), binary)
                else:
                    with self.assertRaisesRegex(ValueError, "required on PATH"):
                        bun_runtime.installed_bun("1.4.5", path=str(root))
            self.assertEqual(list(root.iterdir()), [binary])

    def test_verified_fallback_is_shared_and_never_downgrades(self):
        for system, machine, libc in (("Darwin", "arm64", ""), ("Linux", "x86_64", "glibc"), ("Linux", "aarch64", "musl")):
            with self.subTest(system=system, machine=machine, libc=libc), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary)
                name, target = bun_runtime.runtime_target(system, machine, libc)
                payload = b"#!/bin/sh\nprintf '%s\\n' '1.4.5'\n"
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    archive.writestr(name + "/bun", payload)
                artifact = buffer.getvalue()
                calls = []
                def fetch(url, destination):
                    calls.append(url)
                    if url.endswith("SHASUMS256.txt"):
                        destination.write_text(hashlib.sha256(artifact).hexdigest() + "  " + name + ".zip\n")
                    else:
                        destination.write_bytes(artifact)
                with patch.dict(os.environ, {"PATH": str(home / ".local/bin")}), patch.object(bun_runtime, "host_target", return_value=(name, target)):
                    binary = bun_runtime.install_release("1.4.5", home, fetch=fetch)
                    self.assertEqual(binary, home / ".local/bin/bun")
                    self.assertEqual(bun_runtime.install_release("1.4.4", home, fetch=fetch), binary)
                    self.assertEqual(len(calls), 2)
                    self.assertEqual(binary.read_bytes(), payload)
                    self.assertFalse((home / ".local/share/studio/runtime").exists())

    def test_checksum_failure_preserves_shared_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            binary = home / ".local/bin/bun"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\necho 1.4.4\n")
            binary.chmod(0o755)
            original = binary.read_bytes()
            name, _ = bun_runtime.host_target()
            def corrupt(url, destination):
                destination.write_text(("0"*64 + "  " + name + ".zip\n") if url.endswith("SHASUMS256.txt") else "bad archive")
            with patch.dict(os.environ, {"PATH": str(binary.parent)}):
                with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                    bun_runtime.install_release("1.4.5", home, fetch=corrupt)
            self.assertEqual(binary.read_bytes(), original)


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
