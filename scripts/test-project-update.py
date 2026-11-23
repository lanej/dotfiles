#!/usr/bin/env python3
"""Exercise the public command with real local Git remotes and bounded adapters."""

import json
import fcntl
import hashlib

from bun_runtime import host_target
import os
import shutil
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
COMMAND = ROOT / "bin/project-update"
ADAPTER = ROOT / "scripts/project-lifecycle.py"


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="project-update-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.env = {**os.environ, "HOME": str(self.base), "XDG_CACHE_HOME": str(self.base / "cache"),
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.test",
                    "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.test"}
        tools = self.base / "fixture-bin"
        tools.mkdir()
        go = tools / "go"
        go.write_text(f"#!{sys.executable}\n"
                      "import os, sys\n"
                      "if sys.argv[1:] != ['env', 'CGO_ENABLED']: sys.exit('unexpected Go invocation')\n"
                      "print(os.environ.get('CGO_ENABLED', '1'))\n")
        go.chmod(0o755)
        self.env["PATH"] = str(tools) + os.pathsep + self.env["PATH"]
        self.origin, self.source, self.checkout = [self.base / name for name in ("remote.git", "source", "checkout with spaces")]
        self.git(self.base, "init", "--bare", str(self.origin))
        self.git(self.base, "init", "--initial-branch=trunk", str(self.source))
        self.commit("first")
        self.git(self.source, "remote", "add", "origin", str(self.origin))
        self.git(self.source, "push", "-u", "origin", "trunk")
        self.git(self.origin, "symbolic-ref", "HEAD", "refs/heads/trunk")
        self.git(self.base, "clone", str(self.origin), str(self.checkout))
        self.log = self.base / "actions.jsonl"
        hook = self.base / "hook.py"
        hook.write_text("import json, pathlib, sys\n"
                        f"log = pathlib.Path({str(self.log)!r})\n"
                        "with log.open('a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                        "if sys.argv[-1] == 'status': print('{\"running_revision\": null}')\n"
                        "if pathlib.Path('fail-build').exists() and sys.argv[-1] == 'build': sys.exit(9)\n"
                        "if pathlib.Path('pending').exists() and sys.argv[-1] == 'restart': sys.exit(3)\n")
        self.config = self.base / "projects.toml"
        self.config.write_text(f'[projects.fixture]\npath = {json.dumps(str(self.checkout))}\ncommand = {json.dumps([sys.executable, str(hook)])}\n')

    def git(self, path, *args):
        return subprocess.run(["git", "-C", str(path), *args], env=self.env,
                              text=True, capture_output=True, check=True).stdout.strip()

    def commit(self, value):
        (self.source / "content").write_text(value)
        self.git(self.source, "add", "content")
        self.git(self.source, "commit", "-m", value)

    def invoke(self, *args, code=0):
        result = subprocess.run([sys.executable, str(COMMAND), *args, "--config", str(self.config)],
                                text=True, capture_output=True, env=self.env)
        self.assertEqual(result.returncode, code, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def test_update_default_branch_and_sequence(self):
        self.commit("newest")
        self.git(self.source, "push")
        rows = self.invoke("update", "--all")
        self.assertEqual(rows[0]["completed"], ["pull", "build", "restart"])
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD"), self.git(self.source, "rev-parse", "HEAD"))
        self.assertEqual([json.loads(line) for line in self.log.read_text().splitlines()], [["build"], ["restart"]])

    def test_nonconflicting_local_changes_survive_update(self):
        self.git(self.checkout, "config", "merge.autoStash", "true")
        (self.checkout / "content").write_text("local edit")
        (self.checkout / "valuable").write_text("keep")
        (self.source / "new-file").write_text("upstream addition")
        self.git(self.source, "add", "new-file")
        self.git(self.source, "commit", "-m", "unrelated upstream change")
        self.git(self.source, "push")
        rows = self.invoke("update", "fixture")
        self.assertEqual(rows[0]["completed"], ["pull", "build", "restart"])
        self.assertEqual((self.checkout / "content").read_text(), "local edit")
        self.assertEqual((self.checkout / "valuable").read_text(), "keep")
        self.assertEqual((self.checkout / "new-file").read_text(), "upstream addition")
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD"), self.git(self.source, "rev-parse", "HEAD"))

    def test_conflicting_local_edit_blocks_update(self):
        self.git(self.checkout, "config", "merge.autoStash", "true")
        (self.checkout / "content").write_text("local edit")
        head = self.git(self.checkout, "rev-parse", "HEAD")
        self.commit("upstream edit")
        self.git(self.source, "push")
        self.invoke("update", "fixture", code=1)
        self.assertEqual((self.checkout / "content").read_text(), "local edit")
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(self.checkout, "stash", "list"), "")
        self.assertFalse(self.log.exists())

    def test_conflicting_untracked_file_blocks_update(self):
        (self.checkout / "valuable").write_text("keep")
        head = self.git(self.checkout, "rev-parse", "HEAD")
        (self.source / "valuable").write_text("upstream addition")
        self.git(self.source, "add", "valuable")
        self.git(self.source, "commit", "-m", "add valuable")
        self.git(self.source, "push")
        self.invoke("update", "fixture", code=1)
        self.assertEqual((self.checkout / "valuable").read_text(), "keep")
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD"), head)
        self.assertFalse(self.log.exists())

    def test_ahead_checkout_is_preserved(self):
        self.git(self.checkout, "commit", "--allow-empty", "-m", "local work")
        head = self.git(self.checkout, "rev-parse", "HEAD")
        self.invoke("update", "fixture", code=1)
        self.assertEqual(head, self.git(self.checkout, "rev-parse", "HEAD"))
        self.assertFalse(self.log.exists())

    def test_topic_branch_and_detached_head_are_preserved(self):
        self.git(self.checkout, "checkout", "-b", "work")
        self.invoke("pull", "fixture", code=1)
        self.assertEqual(self.git(self.checkout, "branch", "--show-current"), "work")
        self.git(self.checkout, "checkout", "--detach")
        self.invoke("pull", "fixture", code=1)
        self.assertFalse(self.log.exists())

    def test_unfinished_operation_blocks_pull(self):
        marker = self.checkout / self.git(self.checkout, "rev-parse", "--git-path", "CHERRY_PICK_HEAD")
        marker.write_text(self.git(self.checkout, "rev-parse", "HEAD"))
        rows = self.invoke("update", "fixture", code=1)
        self.assertIn("unfinished Git operation", rows[0]["error"])
        self.assertFalse(self.log.exists())

    def test_executable_entrypoint(self):
        result = subprocess.run([str(COMMAND), "status", "fixture", "--config", str(self.config)],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["outcome"], "ok")

    def test_make_update_targets_report_pending_activation_without_failure(self):
        fixture = self.base / "make fixture"
        (fixture / "bin").mkdir(parents=True)
        command = fixture / "bin/project-update"
        command.write_text(f"#!{sys.executable}\n"
                           "import json, os, sys\n"
                           "print(json.dumps(sys.argv[1:]))\n"
                           "sys.exit(int(os.environ['UPDATE_RESULT']))\n")
        command.chmod(0o755)
        for target, selection in (("update-zellij", "zellij"), ("update-projects", "--all"),
                                  ("project-updates", "--all")):
            for code in (0, 3, 1, 2):
                with self.subTest(target=target, code=code):
                    result = subprocess.run(
                        ["make", "--no-print-directory", "-f", str(ROOT / "Makefile"),
                         f"DOTFILES={fixture}", target],
                        env={**self.env, "UPDATE_RESULT": str(code)}, text=True, capture_output=True)
                    self.assertEqual(json.loads(result.stdout), ["update", selection])
                    self.assertEqual(result.returncode == 0, code in (0, 3), result.stderr)
                    self.assertEqual("manual activation remains" in result.stderr, code == 3)

    def test_concurrent_mutation_is_rejected(self):
        cache = self.base / "cache/dotfiles/project-update"
        cache.mkdir(parents=True)
        key = hashlib.sha256(os.fsencode(self.checkout.resolve())).hexdigest()
        with (cache / f"{key}.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run([sys.executable, str(COMMAND), "build", "fixture", "--config", str(self.config)],
                                    env=self.env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_failure_stops_restart_and_other_projects_continue(self):
        (self.checkout / "fail-build").touch()
        with self.config.open("a") as out:
            out.write(self.config.read_text().replace("projects.fixture", "projects.second"))
        rows = self.invoke("build", "--all", code=1)
        self.assertEqual([r["outcome"] for r in rows], ["failed", "failed"])
        self.assertEqual(len(self.log.read_text().splitlines()), 2)
        self.log.unlink()
        self.git(self.checkout, "add", "fail-build")
        self.git(self.checkout, "commit", "-m", "failure fixture")
        self.git(self.checkout, "push")
        self.invoke("update", "fixture", code=1)
        self.assertEqual(self.log.read_text().strip(), '["build"]')

    def test_dry_run_and_status_freshness(self):
        self.invoke("update", "fixture", "--dry-run")
        self.assertFalse(self.log.exists())
        cached = self.invoke("status", "fixture")[0]
        self.assertEqual(cached["upstream_freshness"], "cached-or-unknown")
        self.commit("latest")
        self.git(self.source, "push")
        fresh = self.invoke("status", "fixture", "--fetch")[0]
        self.assertEqual(fresh["upstream_revision"], self.git(self.source, "rev-parse", "HEAD"))
        self.assertNotEqual(fresh["checkout_revision"], fresh["upstream_revision"])

    def test_pending_restart_and_individual_actions(self):
        (self.checkout / "pending").touch()
        rows = self.invoke("restart", "fixture", code=3)
        self.assertEqual(rows[0]["outcome"], "restart-required")
        self.invoke("clean", "fixture")
        self.assertEqual([json.loads(line) for line in self.log.read_text().splitlines()], [["restart"], ["clean"]])

    def test_zellij_build_includes_plugins_for_selected_runtime(self):
        make = self.base / "tools/make"
        make.parent.mkdir()
        log = self.base / "make-actions"
        make.write_text(f"#!{sys.executable}\nimport json, sys\nwith open({str(log)!r}, 'a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n")
        make.chmod(0o755)
        config = self.base / "machine.toml"
        env = {**self.env, "DOTFILES_CONFIG": str(config),
               "PATH": str(make.parent) + os.pathsep + self.env["PATH"]}
        expected = {"patched": ["zellij-runtime", "zellij-status", "zellij-config", "zellij-copy-hop"],
                    "main": ["zellij-runtime", "zellij-status", "zellij-config"],
                    "release": ["zellij-runtime", "zellij-config"]}
        for source, targets in expected.items():
            with self.subTest(source=source):
                config.write_text(f'sets = []\n[zellij]\nsource = "{source}"\n')
                result = subprocess.run([sys.executable, str(ADAPTER), "zellij", "build"],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = json.loads(log.read_text().splitlines()[-1])
                self.assertEqual(arguments, ["-C", str(ROOT.resolve()), *targets])

    def test_beads_stages_then_restarts_only_matching_artifacts(self):
        scripts = self.checkout / "tools/beads"
        scripts.mkdir(parents=True)
        adapter = scripts / "project-update.py"
        shutil.copyfile(ROOT / "tools/beads/project-update.py", adapter)
        (scripts / "beads_config.py").write_text("# Fixture config reader\n")
        catalog = self.checkout / "bootstrap/tools.toml"
        catalog.parent.mkdir()
        catalog.write_text('[tools.beads]\nversion="1.3.4"\ndolt_version="2.7.4"\n')
        profile = self.checkout / "config/beads/trial.toml"
        profile.parent.mkdir(parents=True)
        profile.write_text('profile="trial"\n')
        controller = scripts / "beads-service.py"
        controller.write_text('''import fcntl, json, shutil, sys
from pathlib import Path
home=Path.home()
share=home/'.local/share/beads-service'
action=sys.argv[1]
if action in ('install','restart'):
    assert '--install-lock-fd' in sys.argv
    with (share/'install.lock').open('a') as contender:
        try:
            fcntl.flock(contender,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            raise AssertionError('The parent deployment lock must remain held')
if action=='install':
    assert '--no-start' in sys.argv
    share.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(__file__,share/'beads-service.py')
    shutil.copyfile(Path(__file__).with_name('beads_config.py'),share/'beads_config.py')
    binaries={}
    for name in ('bd','dolt'):
        binary=share/name
        binary.write_text(name+' fixture artifact')
        binaries[name]=str(binary)
    (share/'runtime.json').write_text(json.dumps(binaries))
elif action=='restart':
    with (home/'beads-restarts').open('a') as output: output.write('restart\\n')
elif action=='status':
    print(json.dumps({'ready':True}))
''')
        self.git(self.checkout, "add", ".")
        self.git(self.checkout, "commit", "-m", "Beads adapter fixture")
        revision = self.git(self.checkout, "rev-parse", "HEAD")
        self.config.write_text(f'[projects.beads]\npath={json.dumps(str(self.checkout))}\n'
                               f'command={json.dumps([sys.executable, str(adapter)])}\n')
        persistent = self.base / ".local/state/beads-service/workspace/valuable"
        persistent.parent.mkdir(parents=True)
        persistent.write_text("retained task data")
        local_config = self.base / ".config/beads-service/config.toml"
        local_config.parent.mkdir(parents=True)
        local_config.write_text("# retained operator settings\n")
        self.invoke("restart", "beads", code=1)
        self.invoke("build", "beads")
        self.assertFalse((self.base / "beads-restarts").exists())
        status = self.invoke("status", "beads")[0]["runtime"]
        self.assertEqual(status["installed_revision"], revision)
        self.assertIsNone(status["running_revision"])
        self.invoke("restart", "beads")
        self.git(self.checkout, "commit", "--allow-empty", "-m", "Unrelated source revision")
        self.assertEqual(self.invoke("status", "beads")[0]["runtime"]["installed_revision"], revision)
        profile.write_text(profile.read_text() + "# local configuration edit\n")
        self.invoke("restart", "beads", code=1)
        self.invoke("build", "beads")
        status = self.invoke("status", "beads")[0]["runtime"]
        self.assertIsNone(status["installed_revision"])
        self.assertTrue(status["installed_source_dirty"])
        self.invoke("restart", "beads")
        installed_helper = self.base / ".local/share/beads-service/beads_config.py"
        installed_helper.write_text("modified outside staging\n")
        self.assertIsNone(self.invoke("status", "beads")[0]["runtime"]["installed_versions"])
        self.invoke("restart", "beads", code=1)
        self.assertEqual((self.base / "beads-restarts").read_text(), "restart\nrestart\n")
        self.assertEqual(persistent.read_text(), "retained task data")
        self.assertEqual(local_config.read_text(), "# retained operator settings\n")

    def test_worktree_manager_pulls_sources_then_builds_and_activates(self):
        scripts = self.checkout / "scripts"
        scripts.mkdir()
        adapter = scripts / "worktree-manager-update.sh"
        shutil.copyfile(ROOT / "scripts/worktree-manager-update.sh", adapter)
        catalog = self.checkout / "bootstrap/tools.toml"
        catalog.parent.mkdir()
        library = scripts / "lib/git-worktree-runtime.sh"
        library.parent.mkdir()
        shutil.copyfile(ROOT / "scripts/lib/git-worktree-runtime.sh", library)
        catalog.write_text('[tools.worktree-manager]\nversion="0.2.0"\n'
                           '[tools.git-worktree-hooks]\nversion="2.57.0"\nruntime_version="2.57.0.worktree-hooks.1"\n')
        self.git(self.source, "tag", "v2.57.0")
        (scripts / "pull-git-worktree-source.sh").write_text(
            'cache="$XDG_CACHE_HOME/dotfiles/git-worktree-hooks"\nmkdir -p "$cache"\n'
            f'printf \'%s\\n\' {shlex.quote(str(self.source))} > "$cache/selected-source"\n'
            'touch "$HOME/pulled-git"\n')
        (scripts / "install-git-worktree-hooks.sh").write_text('''#!/bin/sh
set -eu
[ -f "$HOME/pulled-git" ]
mkdir -p "$HOME/.local/bin"
printf '#!/bin/sh\\necho "git version 2.57.0.worktree-hooks.1"\\n' > "$HOME/.local/bin/git"
chmod +x "$HOME/.local/bin/git"
''')
        (scripts / "install-worktree-manager").write_text('''#!/bin/sh
set -eu
[ "$1" = 0.2.0 ]
[ -x "$HOME/.local/bin/git" ]
printf '#!/bin/sh\\necho "worktree 0.2.0"\\n' > "$HOME/.local/bin/worktree"
chmod +x "$HOME/.local/bin/worktree"
''')
        (self.checkout / "Makefile").write_text("git:\n\t@touch configured\n")
        self.git(self.checkout, "add", ".")
        self.git(self.checkout, "commit", "-m", "Worktree adapter fixture")
        self.git(self.checkout, "push")
        self.config.write_text(f'[projects.worktree-manager]\npath={json.dumps(str(self.checkout))}\n'
                               f'command={json.dumps(["bash", str(adapter)])}\npull_sources=true\n')
        self.invoke("restart", "worktree-manager", code=1)
        self.invoke("build", "worktree-manager", code=1)
        self.invoke("update", "worktree-manager")
        self.assertTrue((self.checkout / "configured").is_file())
        status = self.invoke("status", "worktree-manager")[0]["runtime"]
        self.assertEqual(status["installed_versions"]["git"], "git version 2.57.0.worktree-hooks.1")
        self.assertEqual(status["installed_versions"]["worktree"], "worktree 0.2.0")
        self.assertIsNone(status["running_revision"])
        (scripts / "pull-git-worktree-source.sh").write_text('exit 9\n')
        (self.checkout / "configured").unlink()
        self.invoke("update", "worktree-manager", code=1)
        self.assertFalse((self.checkout / "configured").exists())

    def test_zellij_restart_preserves_live_sessions(self):
        binary = self.base / ".local/bin/zellij"
        binary.parent.mkdir(parents=True)
        for output, expected in [("main [Created 1h ago]", 3), ("main [Created 1h ago] (EXITED - attach to resurrect)", 0)]:
            binary.write_text(f"#!/bin/sh\nprintf '%s\\n' '{output}'\n")
            binary.chmod(0o755)
            result = subprocess.run([sys.executable, str(ADAPTER), "zellij", "restart"], env=self.env, capture_output=True)
            self.assertEqual(result.returncode, expected, result.stderr)
        binary.write_text("#!/bin/sh\necho 'No active zellij sessions found.' >&2\nexit 1\n")
        result = subprocess.run([sys.executable, str(ADAPTER), "zellij", "restart"], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_octo_staging_and_manual_activation(self):
        binary = self.base / ".local/bin/bun"
        binary.parent.mkdir(parents=True)
        log = self.base / "bun-args"
        binary.write_text(f'#!{sys.executable}\nimport json, sys\nwith open({str(log)!r}, "a") as out: out.write(json.dumps(sys.argv[1:]) + "\\n")\nif "scripts/install-local.ts" in sys.argv: print(json.dumps({{"started": False, "manualCommand": "foreground"}}))\n')
        binary.chmod(0o755)
        env = {**self.env, "PATH": str(binary.parent) + os.pathsep + self.env["PATH"]}
        def invoke(action):
            return subprocess.run([sys.executable, str(ADAPTER), "octo-manager", action],
                                  cwd=self.checkout, env=env, text=True, capture_output=True)
        self.assertEqual(invoke("restart").returncode, 1)
        self.assertFalse(log.exists())
        result = invoke("build")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()],
                         [["install", "--frozen-lockfile", "--ignore-scripts"], ["scripts/install-local.ts", "--no-start"]])
        metadata = self.base / ".local/share/octo-manager/current/release.json"
        metadata.parent.mkdir(parents=True)
        metadata.write_text(json.dumps({"revision": self.git(self.checkout, "rev-parse", "HEAD")}))
        result = invoke("restart")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("manualCommand", result.stdout)

    def test_registered_scope_includes_beads_and_both_approval_projects(self):
        result = subprocess.run([sys.executable, str(COMMAND), "update", "--all", "--dry-run"],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({row["project"] for row in json.loads(result.stdout)},
                         {"octo-manager", "zellij", "beads", "bedrock-router", "intent", "keylease", "worktree-manager", "studio"})

    def test_dotfiles_install_clones_and_preserves_both_tools(self):
        for project, directory in (("intent", "intent"), ("keylease", "1password-agent")):
            with self.subTest(project=project):
                (self.source / "payload").write_text("installed " + project)
                (self.source / ".gitignore").write_text("bin/\n")
                (self.source / "Makefile").write_text(
                    "install:\n\tmkdir -p bin $(PREFIX)/bin\n"
                    f"\tcp payload bin/{project}\n\tcp bin/{project} $(PREFIX)/bin/{project}\n")
                self.git(self.source, "add", ".")
                self.git(self.source, "commit", "-m", project)
                self.git(self.source, "push")
                env = {**self.env, "GIT_CONFIG_COUNT": "1",
                       "GIT_CONFIG_KEY_0": f"url.{self.origin}.insteadOf",
                       "GIT_CONFIG_VALUE_0": f"https://github.com/lanej/{project}.git"}
                def install():
                    return subprocess.run([sys.executable, str(ROOT / "scripts/install-approval-cli.py"), project],
                                          env=env, text=True, capture_output=True)
                result = install()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                checkout = self.base / "src" / directory
                head = self.git(checkout, "rev-parse", "HEAD")
                self.git(self.source, "commit", "--allow-empty", "-m", "new remote source")
                self.git(self.source, "push")
                self.assertEqual(install().returncode, 0)
                self.assertEqual(self.git(checkout, "rev-parse", "HEAD"), head)
                if project == "keylease":
                    disabled = subprocess.run([sys.executable, str(ROOT / "scripts/install-approval-cli.py"), project],
                                              env={**env, "CGO_ENABLED": "0"}, text=True, capture_output=True)
                    self.assertNotEqual(disabled.returncode, 0)
                    self.assertIn("CGO_ENABLED=1", disabled.stdout + disabled.stderr)
                valuable = checkout / "active-state"
                valuable.write_text("preserve")
                self.assertNotEqual(install().returncode, 0)
                self.assertEqual(valuable.read_text(), "preserve")
                self.assertEqual((self.base / ".local/bin" / project).read_text(), "installed " + project)

    def test_studio_bootstrap_installs_selected_source_with_its_private_runtime(self):
        (self.source / ".bun-version").write_text("1.4.5\n")
        (self.source / "scripts").mkdir()
        (self.source / "scripts/lifecycle.mjs").write_text("// Controlled Studio boundary\n")
        self.git(self.source, "add", ".")
        self.git(self.source, "commit", "-m", "Studio fixture")
        self.git(self.source, "push")
        _, target = host_target()
        runtime = self.base / ".local/share/studio/runtime" / target / "bun-1.4.5/bun"
        runtime.parent.mkdir(parents=True)
        calls = self.base / "studio-calls"
        runtime.write_text(f"#!{sys.executable}\n" + f'''import json, os, sys
from pathlib import Path
args=sys.argv[1:]
if args == ["--version"]:
    print("1.4.5"); sys.exit(0)
assert args[0] == "scripts/lifecycle.mjs", args
with open({str(calls)!r}, "a") as out: out.write(json.dumps([str(Path.cwd()), *args])+"\\n")
if args[1] == "build":
    if Path("fail-build").exists(): sys.exit(12)
    installed=Path.home()/".local/bin/studio"
    installed.parent.mkdir(parents=True,exist_ok=True)
    installed.write_text("installed Studio")
elif args[1] == "status": print(json.dumps({{"installed":True,"running_revision":None}}))
elif args[1] == "restart": sys.exit(3)
else: raise AssertionError(args)
''')
        runtime.chmod(0o755)
        env = {**self.env, "GIT_CONFIG_COUNT": "1",
               "GIT_CONFIG_KEY_0": f"url.{self.origin}.insteadOf",
               "GIT_CONFIG_VALUE_0": "https://github.com/lanej/studio.git"}
        script = '''source "$1"
install_config_runtime() { :; }
load_dotfiles_config() { DOTFILES_INSTALL_PLAN=$'studio\\tstudio\\tstudio\\t-'; }
install_dependencies
'''
        def install():
            return subprocess.run(["bash", "-c", script, "test", str(ROOT / "bootstrap.sh")],
                                  env=env, text=True, capture_output=True, timeout=20)
        first=install()
        self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
        source=(self.base/"src/studio").resolve()
        self.assertEqual((self.base/".local/bin/studio").read_text(),"installed Studio")
        selected=self.git(source,"rev-parse","HEAD")
        self.commit("new upstream")
        self.git(self.source,"push")
        (source/"local-work").write_text("preserve")
        again=install()
        self.assertEqual(again.returncode,0,again.stdout+again.stderr)
        self.assertEqual(self.git(source,"rev-parse","HEAD"),selected)
        self.assertEqual((source/"local-work").read_text(),"preserve")
        self.assertEqual([json.loads(line) for line in calls.read_text().splitlines()],
                         [[str(source),"scripts/lifecycle.mjs","build"]]*2)
        status=subprocess.run([sys.executable,str(COMMAND),"status","studio"],env=env,text=True,capture_output=True)
        self.assertEqual(status.returncode,0,status.stderr)
        self.assertTrue(json.loads(status.stdout)[0]["runtime"]["installed"])
        restart=subprocess.run([sys.executable,str(COMMAND),"restart","studio"],env=env,text=True,capture_output=True)
        self.assertEqual(restart.returncode,3,restart.stderr)
        (source/"fail-build").touch()
        failed=install()
        self.assertNotEqual(failed.returncode,0)
        self.assertEqual((self.base/".local/bin/studio").read_text(),"installed Studio")
        self.git(source,"remote","set-url","origin","https://github.com/example/unrelated.git")
        before=calls.read_bytes()
        runtime.rename(runtime.with_name("retained-bun"))
        unexpected=self.base/"unexpected-download"
        curl=self.base/"fixture-bin/curl"
        curl.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nPath({str(unexpected)!r}).touch()\nraise SystemExit(99)\n")
        curl.chmod(0o755)
        for action in ("build", "status", "restart"):
            rejected=subprocess.run([sys.executable,str(COMMAND),action,"studio"],env=env,text=True,capture_output=True)
            self.assertEqual(rejected.returncode,1,rejected.stderr)
            self.assertIn("Preserve unrecognized Studio checkout",rejected.stdout+rejected.stderr)
        self.assertEqual(calls.read_bytes(),before)
        self.assertFalse(unexpected.exists())

    def test_approval_projects_install_and_preserve_active_sessions(self):
        make = self.base / "tools/make"
        make.parent.mkdir()
        log = self.base / "native-installs"
        make.write_text(f"#!{sys.executable}\n"
                        "import json, os, pathlib, sys\n"
                        f"with open({str(log)!r}, 'a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                        "project = pathlib.Path('selected-project').read_text()\n"
                        "prefix = pathlib.Path(sys.argv[2].split('=', 1)[1])\n"
                        "built = pathlib.Path('bin') / project\n"
                        "built.parent.mkdir(exist_ok=True)\n"
                        "built.write_text('built ' + project)\n"
                        "installed = prefix / 'bin' / project\n"
                        "installed.parent.mkdir(parents=True, exist_ok=True)\n"
                        "installed.write_bytes(built.read_bytes())\n"
                        "if os.environ.get('APPROVAL_REPLACEMENT_MARKER'): pathlib.Path(os.environ['APPROVAL_REPLACEMENT_MARKER']).write_text(str(installed))\n")
        make.chmod(0o755)
        (self.checkout / ".gitignore").write_text("bin/\n")
        (self.checkout / "selected-project").write_text("intent")
        self.git(self.checkout, "add", ".gitignore", "selected-project")
        self.git(self.checkout, "commit", "-m", "Native build fixture")
        env = {**self.env, "PATH": str(make.parent) + os.pathsep + self.env["PATH"]}
        for project in ("intent", "keylease"):
            with self.subTest(project=project):
                (self.checkout / "selected-project").write_text(project)
                self.git(self.checkout, "add", "selected-project")
                self.git(self.checkout, "commit", "--allow-empty", "-m", project)
                def invoke(action):
                    return subprocess.run([sys.executable, str(ADAPTER), project, action],
                                          cwd=self.checkout, env=env, text=True, capture_output=True)
                self.assertIsNone(json.loads(invoke("status").stdout)["installed_revision"])
                self.assertEqual(invoke("restart").returncode, 1)
                valuable = self.checkout / "active-session-state"
                valuable.write_text("preserve")
                self.assertEqual(invoke("build").returncode, 1)
                self.assertEqual(valuable.read_text(), "preserve")
                valuable.unlink()
                result = invoke("build")
                self.assertEqual(result.returncode, 0, result.stderr)
                revision = self.git(self.checkout, "rev-parse", "HEAD")
                status = json.loads(invoke("status").stdout)
                self.assertEqual(status["installed_revision"], revision)
                self.assertIsNone(status["running_revision"])
                self.assertEqual(invoke("restart").returncode, 3)
                self.git(self.checkout, "commit", "--allow-empty", "-m", "advance source")
                self.assertEqual(json.loads(invoke("status").stdout)["installed_revision"], revision)
                self.assertEqual(invoke("restart").returncode, 1)
                installed = self.base / ".local/bin" / project
                installed.write_text("replaced externally")
                self.assertIsNone(json.loads(invoke("status").stdout)["installed_revision"])
                self.assertEqual(invoke("clean").returncode, 1)
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()],
                         [["install", f"PREFIX={self.base / '.local'}"]] * 2)
        # Another installer replaces the file after verification, while the
        # adapter checks that source did not move before publishing its receipt.
        marker = self.base / "replace-after-verification"
        real_git = shutil.which("git")
        git = make.parent / "git"
        git.write_text(f"#!{sys.executable}\n"
                       "import os, pathlib, sys\n"
                       f"marker = pathlib.Path({str(marker)!r})\n"
                       "if sys.argv[1:] == ['rev-parse', 'HEAD'] and marker.exists():\n"
                       " pathlib.Path(marker.read_text()).write_text('foreign replacement')\n"
                       " marker.unlink()\n"
                       f"os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n")
        git.chmod(0o755)
        env["APPROVAL_REPLACEMENT_MARKER"] = str(marker)
        result = invoke("build")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(json.loads(invoke("status").stdout)["installed_revision"])

    def test_router_preserves_settings_and_requires_staged_binary(self):
        go = self.base / "tools/go"
        go.parent.mkdir()
        log = self.base / "router-actions"
        installer = (f"#!{sys.executable}\n"
                     "import json, os, pathlib, shutil, sys\n"
                     f"with open({str(log)!r}, 'a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                     "installed = pathlib.Path(os.environ.get('CODEX_HOME') or pathlib.Path(os.environ['HOME']) / '.codex') / 'bedrock-router/bedrock-router'\n"
                     "installed.parent.mkdir(parents=True, exist_ok=True)\n"
                     "shutil.copyfile(__file__, installed)\n")
        go.write_text(f"#!{sys.executable}\nimport pathlib, sys\np = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\np.write_text({installer!r})\np.chmod(0o755)\n")
        go.chmod(0o755)
        codex_home = self.base / "custom-codex"
        env = {**self.env, "CODEX_HOME": str(codex_home), "PATH": str(go.parent) + os.pathsep + self.env["PATH"]}
        def invoke(action):
            return subprocess.run([sys.executable, str(ADAPTER), "bedrock-router", action],
                                  cwd=self.checkout, env=env, text=True, capture_output=True)
        self.assertEqual(invoke("restart").returncode, 1)
        self.assertFalse(log.exists())
        result = invoke("build")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = invoke("restart")
        self.assertEqual(result.returncode, 0, result.stderr)
        staged, activated = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(staged, ["install", "--config", str(self.checkout.resolve() / "config.json"),
                                  "--keep-env", "--preserve-mcp", "--no-start"])
        self.assertEqual(activated, staged[:-1])
        installed = codex_home / "bedrock-router/bedrock-router"
        revision = self.git(self.checkout, "rev-parse", "HEAD")
        self.assertEqual(json.loads(invoke("status").stdout)["installed_revision"], revision)
        self.git(self.checkout, "commit", "--allow-empty", "-m", "next source revision")
        advanced = json.loads(invoke("status").stdout)
        self.assertEqual(advanced["installed_revision"], revision)
        self.assertNotEqual(revision, self.git(self.checkout, "rev-parse", "HEAD"))
        self.assertEqual(advanced["installed_binary"], str(installed))
        self.assertEqual(invoke("restart").returncode, 1)
        self.git(self.checkout, "checkout", "--detach", revision)
        installed.write_text("different binary")
        self.assertIsNone(json.loads(invoke("status").stdout)["installed_revision"])
        self.assertEqual(invoke("restart").returncode, 1)
        self.assertEqual(len(log.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
