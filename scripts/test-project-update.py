#!/usr/bin/env python3
"""Exercise the public command with real local Git remotes and bounded adapters."""

import json
import fcntl
import hashlib

import os
import shutil
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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
                    "XDG_CONFIG_HOME": str(self.base / ".config"),
                    "ZELLIJ_SOCKET_DIR": str(self.base / "zellij-sockets"),
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
        hook.write_text("import hashlib, json, os, pathlib, sys, time\n"
                        f"log = pathlib.Path({str(self.log)!r})\n"
                        "with log.open('a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                        "if sys.argv[-1] == 'status': print('{\"running_revision\": null}')\n"
                        "if pathlib.Path('fail-build').exists() and sys.argv[-1] == 'build': sys.exit(9)\n"
                        "action=sys.argv[-1]\n"
                        "if action=='build' and pathlib.Path('pause-build').exists():\n"
                        " pathlib.Path('build-started').touch()\n"
                        " while not pathlib.Path('continue-build').exists(): time.sleep(0.02)\n"
                        "expected=hashlib.sha256(pathlib.Path('content').read_bytes()).hexdigest()\n"
                        "runtime=pathlib.Path('runtime')\n"
                        "if action=='restart': runtime.write_text(expected)\n"
                        "if action in ('inventory','checkpoint','restart','restore','verify'):\n"
                        " target={'target':'local','expected_identity':expected,'running_identity':runtime.read_text() if runtime.exists() else None,'ready':runtime.exists(),'process':None,'sessions':[]}\n"
                        " if action=='checkpoint': target['checkpoint']={'state':'refused' if pathlib.Path('pending').exists() else 'confirmed','run_id':os.environ['PROJECT_UPDATE_RUN_ID']}\n"
                        " if pathlib.Path('process-change').exists():\n"
                        "  target['process']={'pid':100 if action=='inventory' else 200,'start_identity':'start','native_id':'native','owner_verified':True}\n"
                        " if pathlib.Path('final-process-swap').exists():\n"
                        "  pid=200 if action=='verify' else 100\n"
                        "  target['process']={'pid':pid,'start_identity':str(pid),'native_id':str(pid),'owner_verified':True}\n"
                        " if pathlib.Path('pause-mismatch').exists(): target['scheduler_paused']=action not in ('restore','verify')\n"
                        " if action=='verify' and pathlib.Path('drift').exists(): target.update(expected_identity='different',running_identity='different')\n"
                        " if action=='restore' and pathlib.Path('restore-failure').exists(): target['reason']='conversation-restoration-failed'\n"
                        " print(json.dumps({'schema_version':1,'targets':[target]}))\n"
                        " if action=='restore' and pathlib.Path('restore-failure').exists(): sys.exit(3)\n"
                        " if action=='checkpoint' and pathlib.Path('pending').exists(): sys.exit(3)\n")
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
        configuration = [] if args[0] == "wait" else ["--config", str(self.config)]
        result = subprocess.run([sys.executable, str(COMMAND), *args, *configuration],
                                text=True, capture_output=True, env=self.env)
        self.assertEqual(result.returncode, code, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def test_update_default_branch_and_sequence(self):
        self.commit("newest")
        self.git(self.source, "push")
        rows = self.invoke("update", "--all")
        self.assertEqual(rows[0]["completed"], ["pull", "build", "inventory", "checkpoint", "restart", "restore", "verify"])
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD"), self.git(self.source, "rev-parse", "HEAD"))
        self.assertEqual([json.loads(line) for line in self.log.read_text().splitlines()],
                         [[action] for action in ("build", "inventory", "checkpoint", "restart", "restore", "verify")])

    def test_update_clones_missing_checkout_from_registered_repository(self):
        shutil.rmtree(self.checkout)
        self.checkout = self.base / "new parent" / "checkout with spaces"
        self.config.write_text(f'[projects.fixture]\npath={json.dumps(str(self.checkout))}\n'
                               f'command={json.dumps([sys.executable, str(self.base / "hook.py")])}\n')
        self.invoke("update", "fixture", "--dry-run")
        self.invoke("status", "fixture", code=1)
        self.assertFalse(self.checkout.exists())
        missing = self.invoke("pull", "fixture", code=1)
        self.assertIn("configure repository", missing[0]["error"])
        self.assertFalse(self.checkout.exists())
        with self.config.open("a") as output:
            output.write(f'repository={json.dumps(str(self.origin))}\nremote="upstream"\n')
        self.commit("latest remote content")
        self.git(self.source, "push")
        rows = self.invoke("update", "fixture")
        self.assertEqual(rows[0]["outcome"], "ok")
        self.assertEqual(self.git(self.checkout, "symbolic-ref", "--short", "HEAD"), "trunk")
        self.assertEqual(self.git(self.checkout, "remote", "get-url", "upstream"), str(self.origin))
        self.assertEqual((self.checkout / "content").read_text(), "latest remote content")
        self.assertEqual(rows[0]["completed"],
                         ["pull", "build", "inventory", "checkpoint", "restart", "restore", "verify"])
        self.invoke("pull", "fixture")

    def test_clone_preserves_existing_non_checkout_directory(self):
        shutil.rmtree(self.checkout)
        self.checkout.mkdir()
        valuable = self.checkout / "valuable.txt"
        valuable.write_text("preserve me")
        with self.config.open("a") as output:
            output.write(f'repository={json.dumps(str(self.origin))}\n')
        rows = self.invoke("update", "fixture", code=1)
        self.assertEqual(rows[0]["completed"], [])
        self.assertEqual(valuable.read_text(), "preserve me")
        self.assertFalse((self.checkout / ".git").exists())
        self.assertFalse(self.log.exists())

    def test_clone_failure_stops_before_build(self):
        shutil.rmtree(self.checkout)
        with self.config.open("a") as output:
            output.write(f'repository={json.dumps(str(self.base / "unavailable.git"))}\n')
        rows = self.invoke("update", "fixture", code=1)
        self.assertIn("Clone failed", rows[0]["error"])
        self.assertFalse(self.log.exists())

    def test_zellij_update_is_deferred_until_explicitly_requested(self):
        self.config.write_text(
            f'[projects.zellij]\npath={json.dumps(str(self.checkout))}\n'
            f'command={json.dumps([sys.executable, str(self.base / "hook.py")])}\n'
            'lifecycle="terminal"\nautomatic_restart=false\n')
        runtime = self.checkout / "runtime"
        runtime.write_text("old-runtime")
        rows = self.invoke("update", "--all")
        self.assertEqual(rows[0]["activation"], "deferred")
        self.assertFalse(rows[0]["activation_verified"])
        self.assertEqual(rows[0]["staging"], "deferred")
        self.assertEqual(rows[0]["completed"], ["pull", "inventory"])
        self.assertEqual(runtime.read_text(), "old-runtime")
        self.assertNotEqual(rows[0]["targets"][0]["expected_identity"],
                            rows[0]["targets"][0]["running_identity"])
        self.assertEqual([json.loads(line) for line in self.log.read_text().splitlines()], [["inventory"]])
        self.invoke("verify", "--all", code=3)
        requested = self.invoke("restart", "zellij", "--restart-zellij")
        self.assertEqual(requested[0]["outcome"], "ok")
        self.assertEqual(requested[0]["completed"],
                         ["inventory", "checkpoint", "restart", "restore", "verify"])
        self.assertNotEqual(runtime.read_text(), "old-runtime")

    def test_deferred_terminal_preserves_its_application_before_checkpoint(self):
        hook = self.base / "hook.py"
        code = hook.read_text().replace(
            "if action=='checkpoint': target['checkpoint']",
            "if pathlib.Path('terminal-owned').exists(): target['sessions']=["
            "{'session_id':'conversation','restoration':'unchanged',"
            "'restoration_owner':{'project':'zellij','target':'local','pane_id':1}}]\n"
            " if action=='checkpoint': target['checkpoint']")
        hook.write_text(code)
        application = self.base / "application"
        shutil.copytree(self.checkout, application)
        (application / "terminal-owned").touch()
        (application / "runtime").write_text("old-application")
        (self.checkout / "runtime").write_text("old-terminal")
        self.config.write_text(
            f'[projects.application]\npath={json.dumps(str(application))}\n'
            f'command={json.dumps([sys.executable, str(hook)])}\nlifecycle="consumer"\n'
            f'[projects.zellij]\npath={json.dumps(str(self.checkout))}\n'
            f'command={json.dumps([sys.executable, str(hook)])}\nlifecycle="terminal"\n'
            'automatic_restart=false\ndepends_on=["application"]\n')
        rows = self.invoke("restart", "--all", code=3)
        app = next(row for row in rows if row["project"] == "application")
        self.assertEqual(app["reason"], "terminal-session-restart-deferred: zellij")
        self.assertEqual((application / "runtime").read_text(), "old-application")
        self.assertEqual((self.checkout / "runtime").read_text(), "old-terminal")
        actions = [json.loads(line)[-1] for line in self.log.read_text().splitlines()]
        self.assertTrue(set(actions) <= {"inventory", "verify"}, actions)

    def test_unsupported_terminal_request_refuses_before_dependent_checkpoint(self):
        self.config.write_text(
            f'[projects.zellij]\npath={json.dumps(str(self.checkout))}\n'
            f'command={json.dumps([sys.executable, str(self.base / "hook.py")])}\n'
            'lifecycle="terminal"\nautomatic_restart=false\n')
        hook = self.base / "hook.py"
        hook.write_text(hook.read_text().replace(
            "if action=='checkpoint': target['checkpoint']",
            "target['session_replacement_supported']=False\n"
            " if action=='checkpoint': target['checkpoint']"))
        rows = self.invoke("restart", "zellij", "--restart-zellij", code=3)
        self.assertEqual(rows[0]["reason"], "zellij-session-restoration-not-supported")
        self.assertTrue(set(json.loads(line)[-1] for line in self.log.read_text().splitlines())
                        <= {"inventory", "verify"})

    def test_nonconflicting_local_changes_survive_update(self):
        self.git(self.checkout, "config", "merge.autoStash", "true")
        (self.checkout / "content").write_text("local edit")
        (self.checkout / "valuable").write_text("keep")
        (self.source / "new-file").write_text("upstream addition")
        self.git(self.source, "add", "new-file")
        self.git(self.source, "commit", "-m", "unrelated upstream change")
        self.git(self.source, "push")
        rows = self.invoke("update", "fixture")
        self.assertEqual(rows[0]["completed"], ["pull", "build", "inventory", "checkpoint", "restart", "restore", "verify"])
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

    def test_make_update_targets_propagate_incomplete_activation(self):
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
                    self.assertEqual(result.returncode == 0, code == 0, result.stderr)
                    if code:
                        self.assertIn(f"Error {code}", result.stderr)

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
        self.assertEqual(rows[0]["outcome"], "incomplete")
        self.invoke("clean", "fixture")
        self.assertEqual([json.loads(line) for line in self.log.read_text().splitlines()],
                         [["inventory"], ["checkpoint"], ["verify"], ["clean"]])

    def test_current_runtime_skips_checkpoint_and_relaunch(self):
        (self.checkout / "runtime").write_text(hashlib.sha256((self.checkout / "content").read_bytes()).hexdigest())
        rows = self.invoke("restart", "fixture")
        self.assertEqual(rows[0]["activation"], "already-current")
        self.assertEqual([json.loads(line)[0] for line in self.log.read_text().splitlines()], ["inventory", "verify"])

    def test_lost_original_restore_ack_reconciles_without_repeating_effects(self):
        hook = self.base / "original-owner.py"
        state = self.base / "original-owner.json"
        selected = self.base / "select-original"
        process = {"pid": 123, "start_identity": "original-start",
                   "native_id": "original-native", "owner_verified": True}
        state.write_text(json.dumps({"process": process, "ready": True}))
        hook.write_text(f'''import json, os, pathlib, sys
actor, action = sys.argv[1:]
log = pathlib.Path({str(self.log)!r})
with log.open('a') as out:
    out.write(json.dumps([actor, action]) + '\\n')
state = pathlib.Path({str(state)!r})
value = json.loads(state.read_text())
target = {{**value,'target':'local','expected_identity':'original-image' if pathlib.Path({str(selected)!r}).exists() else 'selected-image',
          'running_identity':'original-image','sessions':[],'scheduler_paused':False}}
if actor == 'prerequisite':
    target.update(ready=False, running_identity=None, process=None)
else:
    if action == 'checkpoint':
        target.update(ready=False, checkpoint={{'state':'confirmed','run_id':os.environ['PROJECT_UPDATE_RUN_ID']}})
        state.write_text(json.dumps(target))
    if action == 'restore':
        assert os.environ.get('PROJECT_UPDATE_RECOVER_ORIGINAL') == '1'
        target.pop('checkpoint', None)
        target['ready'] = True
        state.write_text(json.dumps(target))
        print('restore acknowledgement lost')
        sys.exit(0)
print(json.dumps({{'schema_version':1,'targets':[target]}}))
if action == 'verify' and (not target['ready'] or target['running_identity'] != target['expected_identity']):
    sys.exit(3)
''')
        command = [sys.executable, str(hook)]
        self.config.write_text(
            f'[projects.fixture]\npath={json.dumps(str(self.checkout))}\n'
            f'command={json.dumps([*command, "fixture"])}\ndepends_on=["prerequisite"]\n'
            f'[projects.prerequisite]\npath={json.dumps(str(self.checkout))}\n'
            f'command={json.dumps([*command, "prerequisite"])}\n')
        first = self.invoke("restart", "fixture", code=3)[0]
        self.assertEqual(first["target_results"][0]["phase"], "original-restoration-requested")
        self.assertNotIn("recovered_original", first["target_results"][0])
        self.assertTrue(json.loads(state.read_text())["ready"])
        self.invoke("verify", "fixture", code=3)
        selected.touch()

        # A healthy different owner cannot prove release of the frozen owner.
        changed = json.loads(state.read_text())
        changed["process"] = {**process, "native_id": "different-owner"}
        state.write_text(json.dumps(changed))
        blocked = self.invoke("restart", "fixture", code=3)[0]
        self.assertIn("previous-update-not-restored", blocked["reason"])
        changed["process"] = process
        state.write_text(json.dumps(changed))

        # Even an exact original is insufficient after an unknown launch.
        operation = Path(first["recovery_path"])
        unknown = operation / "evidence/unknown-restart.json"
        unknown.write_text(json.dumps({"project": "fixture", "target": "local",
                                      "action": "restart", "state": "outcome-unknown"}))
        unknown.chmod(0o600)
        blocked = self.invoke("restart", "fixture", code=3)[0]
        self.assertIn("previous-update-not-restored", blocked["reason"])
        unknown.unlink()

        completed = self.invoke("restart", "fixture")[0]
        self.assertEqual(completed["activation"], "already-current")
        reconciled = json.loads((operation / "fixture-reconciled.json").read_text())
        self.assertTrue(reconciled["targets"][0]["recovered_original"])
        actions = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(actions.count(["fixture", "checkpoint"]), 1)
        self.assertEqual(actions.count(["fixture", "restore"]), 1)
        self.assertNotIn(["fixture", "restart"], actions)

    def test_changed_process_blocks_replacement(self):
        (self.checkout / "process-change").touch()
        rows = self.invoke("restart", "fixture", code=3)
        self.assertIn("checkpoint-process-or-artifact-identity-changed", rows[0]["reason"])
        self.assertFalse((self.checkout / "runtime").exists())

    def test_selected_identity_drift_blocks_verified_completion(self):
        (self.checkout / "drift").touch()
        rows = self.invoke("restart", "fixture", code=3)
        self.assertIn("selected-artifact-changed", rows[0]["reason"])

    def test_final_same_image_process_swap_is_incomplete(self):
        (self.checkout / "final-process-swap").touch()
        rows = self.invoke("restart", "fixture", code=3)
        self.assertIn("final-process-incarnation-changed", rows[0]["reason"])

    def test_restored_scheduler_pause_must_match_checkpoint_baseline(self):
        (self.checkout / "pause-mismatch").touch()
        rows = self.invoke("restart", "fixture", code=3)
        self.assertIn("restored-scheduler-pause-differs", rows[0]["reason"])
        launches = [json.loads(line)[0] for line in self.log.read_text().splitlines()].count("restart")
        self.invoke("restart", "fixture", code=3)
        self.assertEqual([json.loads(line)[0] for line in self.log.read_text().splitlines()].count("restart"), launches)

    def test_restoration_failure_retains_native_evidence(self):
        (self.checkout / "restore-failure").touch()
        rows = self.invoke("restart", "fixture", code=3)
        self.assertEqual(rows[0]["reason"], "conversation-restoration-failed")
        operation = Path(rows[0]["recovery_path"])
        responses = [json.loads(path.read_text()) for path in (operation / "evidence").iterdir()]
        self.assertTrue(any(response.get("exit_code") == 3 and response["response"]["targets"][0]["reason"]
                            == "conversation-restoration-failed" for response in responses))
        self.assertEqual(self.invoke("wait", rows[0]["run_id"], code=3), rows)
        # A second invocation reconciles the first result through inspection
        # and does not repeat the already observed launch.
        before = [json.loads(line)[0] for line in self.log.read_text().splitlines()].count("restart")
        self.invoke("restart", "fixture", code=0)
        after = [json.loads(line)[0] for line in self.log.read_text().splitlines()].count("restart")
        self.assertEqual(before, after)

    def test_unselected_consumer_refusal_blocks_service(self):
        consumer = self.base / "consumer"
        shutil.copytree(self.checkout, consumer)
        (consumer / "pending").touch()
        with self.config.open("a") as output:
            output.write(f'\n[projects.consumer]\npath={json.dumps(str(consumer))}\n'
                         f'command={json.dumps([sys.executable, str(self.base / "hook.py")])}\n'
                         'lifecycle="consumer"\ndepends_on=["fixture"]\n')
        rows = self.invoke("restart", "fixture", code=3)
        self.assertEqual({row["project"] for row in rows}, {"fixture", "consumer"})
        self.assertFalse((self.checkout / "runtime").exists())
        self.assertFalse((consumer / "runtime").exists())
        self.assertTrue(any(row.get("participation") == "dependent-recovery" for row in rows))
        (consumer / "pending").unlink()
        retried = self.invoke("restart", "fixture")
        self.assertTrue(all(row["outcome"] == "ok" for row in retried))

    def test_current_consumer_checkpoints_without_replacement(self):
        consumer = self.base / "consumer"
        shutil.copytree(self.checkout, consumer)
        (consumer / "runtime").write_text(hashlib.sha256((consumer / "content").read_bytes()).hexdigest())
        with self.config.open("a") as output:
            output.write(f'\n[projects.consumer]\npath={json.dumps(str(consumer))}\n'
                         f'command={json.dumps([sys.executable, str(self.base / "hook.py")])}\n'
                         'lifecycle="consumer"\ndepends_on=["fixture"]\n')
        rows = self.invoke("restart", "fixture")
        current = next(row for row in rows if row["project"] == "consumer")
        self.assertEqual(current["target_results"][0]["completed"], ["checkpoint", "restore", "verify"])
        self.assertEqual([json.loads(line)[0] for line in self.log.read_text().splitlines()].count("restart"), 1)

    def stateless_approval_consumer(self, project="keylease"):
        installed = self.base / ".local/bin" / project
        installed.parent.mkdir(parents=True)
        calls = self.base / "approval-native-calls.jsonl"
        owner = self.base / "approval-owner"
        installed.write_text(f"""#!{sys.executable}
import hashlib,json,pathlib,sys
binary=pathlib.Path(__file__)
with pathlib.Path({str(calls)!r}).open('a') as log:
    log.write(json.dumps(sys.argv[1:])+'\\n')
action=sys.argv[-1]
if action=='artifact':
    print(json.dumps({{'expected_identity':'build:idle-'+binary.name,'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()}}))
elif action=='backends':
    print(json.dumps(['mock'] if pathlib.Path({str(owner)!r}).exists() else []))
elif action=='profiles':
    print('[]')
elif action=='inventory':
    print(json.dumps({{'schema_version':1,'targets':[{{
        'target':'broker:mock','expected_identity':'build:idle-keylease',
        'running_identity':'build:idle-keylease','ready':True,'sessions':[],
        'process':{{'pid':12345,'start_identity':'new-owner','native_id':'broker-id','owner_verified':True}}
    }}]}}))
else:
    raise SystemExit('unexpected native lifecycle effect')
""")
        installed.chmod(0o755)
        source = self.base / f"idle-{project}-source"
        source.mkdir()
        with self.config.open("a") as output:
            output.write(f'\n[projects.{project}]\npath={json.dumps(str(source))}\n'
                         f'command={json.dumps([sys.executable, str(ADAPTER), project])}\n'
                         'lifecycle="consumer"\ndepends_on=["fixture"]\n')
        return source, calls, owner

    def test_stateless_approval_consumer_recovers_without_a_process_binding(self):
        self.assert_stateless_approval_recovery("keylease")

    def test_stateless_intent_consumer_recovers_without_a_process_binding(self):
        self.assert_stateless_approval_recovery("intent")

    def assert_stateless_approval_recovery(self, project):
        source, calls, _ = self.stateless_approval_consumer(project)
        rows = self.invoke("restart", "fixture")
        idle = next(row for row in rows if row["project"] == project)
        self.assertEqual(idle["target_results"][0]["completed"], ["checkpoint", "restore", "verify"])
        self.assertEqual(idle["phase"], "verified")
        operation = Path(idle["recovery_path"])
        observations = [json.loads(path.read_text()) for path in (operation / "evidence").iterdir()]
        checkpoint = next(value["response"]["targets"][0]["checkpoint"] for value in observations
                          if value.get("project") == project and value.get("action") == "checkpoint"
                          and value.get("state") == "observed")
        self.assertEqual(checkpoint, {"state": "confirmed", "run_id": idle["run_id"]})
        env = {**self.env, "PROJECT_UPDATE_OPERATION_DIR": str(operation),
               "PROJECT_UPDATE_RUN_ID": idle["run_id"], "PROJECT_UPDATE_TARGET": f"{project}-cli"}
        env.pop("PROJECT_UPDATE_EXPECTED_PROCESS", None)
        env.pop("PROJECT_UPDATE_RECOVER_ORIGINAL", None)
        restored = subprocess.run([sys.executable, str(ADAPTER), project, "restore"],
                                  cwd=source, env=env, text=True, capture_output=True)
        self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
        target = json.loads(restored.stdout)["targets"][0]
        self.assertIsNone(target["process"])
        self.assertNotIn("checkpoint", target)
        self.assertEqual([json.loads(line)[0] for line in self.log.read_text().splitlines()].count("restart"), 1)
        self.assertTrue(all(json.loads(line)[-1] in ("artifact", "backends", "profiles")
                            for line in calls.read_text().splitlines()))

    def test_stateless_approval_recovery_refuses_an_owner_appearing_after_checkpoint(self):
        _, calls, owner = self.stateless_approval_consumer()
        hook = self.base / "hook.py"
        hook.write_text(hook.read_text().replace(
            "if action=='restart': runtime.write_text(expected)",
            f"if action=='restart': runtime.write_text(expected);pathlib.Path({str(owner)!r}).touch()"))
        rows = self.invoke("restart", "fixture", code=3)
        idle = next(row for row in rows if row["project"] == "keylease")
        self.assertIn("stateless-approval-target-is-no-longer-idle", idle["reason"])
        self.assertTrue(owner.exists())
        self.assertEqual(idle["outcome"], "incomplete")
        self.assertNotIn("verify", idle["target_results"][0]["completed"])
        self.assertTrue(all(json.loads(line)[-1] in ("artifact", "backends", "inventory")
                            for line in calls.read_text().splitlines()))

    def test_terminal_owns_current_application_restore_and_final_process_binding(self):
        helper = self.base / "terminal-fixture.py"
        helper.write_text('''import hashlib,json,os,pathlib,sys
root=pathlib.Path(os.environ['HOME'])
name=pathlib.Path.cwd().name
app=name=='app'
action=sys.argv[-1]
with (root/'terminal-actions').open('a') as out: out.write(json.dumps([name,action])+'\\n')
old={'pid':101,'start_identity':'app-old','native_id':'app-old','owner_verified':True}
new={'pid':202,'start_identity':'app-new','native_id':'app-new','owner_verified':True}
terminal_old={'pid':303,'start_identity':'terminal-old','native_id':'terminal-old','owner_verified':True}
terminal_new={'pid':404,'start_identity':'terminal-new','native_id':'terminal-new','owner_verified':True}
session={'session_id':'conversation','transcript_path':str(root/'transcript.jsonl'),
         'branch_id':'checkpoint-leaf','cwd':str(root/'app')}
owner={'project':'terminal','target':'native-terminal-uuid','pane_id':7}
launched=(root/'terminal-launched').exists()
expected=hashlib.sha256(pathlib.Path('content').read_bytes()).hexdigest()
target={'target':'application' if app else 'main','expected_identity':expected,
        'running_identity':expected if app or launched else 'previous-terminal-image',
        'ready':True,'process':new if app and launched else old if app else terminal_new if launched else terminal_old,
        'sessions':[{**session,'restoration':'restored' if launched else 'unchanged','restoration_owner':owner}]
                   if app else [{'session_id':'native-terminal-uuid','layout_identity':'layout','restoration':'restored' if launched else 'unchanged'}]}
if not app: target['native_session_id']='native-terminal-uuid'
if action=='checkpoint': target['checkpoint']={'state':'confirmed','run_id':os.environ['PROJECT_UPDATE_RUN_ID']}
if action=='restart':
 if app: raise AssertionError('A current app must launch only through terminal restoration')
 (root/'terminal-launched').touch()
 target.update(process=terminal_new,running_identity=expected)
 target['sessions'][0]['restoration']='restored'
if app and action=='restore':
 assert os.environ.get('PROJECT_UPDATE_DEFER_RESTORATION')=='1'
 (root/'app-stopped-once').write_text('stopped')
 target['ready']=False
 target['sessions'][0]['restoration']='pending'
if not app and action in ('restart','restore'):
 target['restored_applications']=[{'project':'app','target':'application','original_process':old,
   'process':new,'wrapper_process':{'pid':new['pid'],'start_identity':new['start_identity']},
   'session':session,'terminal_session_id':'native-terminal-uuid','pane_id':7}]
if app and action=='verify' and (root/'swap-after-terminal').exists():
 target['process']={'pid':505,'start_identity':'foreign','native_id':'foreign','owner_verified':True}
print(json.dumps({'schema_version':1,'targets':[target]}))
''')
        for path in (self.base / "app", self.base / "terminal"):
            shutil.copytree(self.checkout, path)
        self.config.write_text(
            f'[projects.app]\npath={json.dumps(str(self.base / "app"))}\n'
            f'command={json.dumps([sys.executable, str(helper)])}\nlifecycle="consumer"\n'
            f'[projects.terminal]\npath={json.dumps(str(self.base / "terminal"))}\n'
            f'command={json.dumps([sys.executable, str(helper)])}\nlifecycle="terminal"\ndepends_on=["app"]\n')
        rows = self.invoke("restart", "terminal")
        self.assertEqual({row["project"] for row in rows}, {"app", "terminal"})
        app = next(row for row in rows if row["project"] == "app")
        self.assertEqual(app["target_results"][0]["completed"], ["checkpoint", "restore", "verify"])
        self.assertEqual(app["target_results"][0]["restored_process"]["native_id"], "app-new")
        actions = [json.loads(line) for line in (self.base / "terminal-actions").read_text().splitlines()]
        self.assertEqual(actions.count(["terminal", "restart"]), 1)
        self.assertNotIn(["app", "restart"], actions)
        # Repeat the isolated update with a same-image foreign owner at final verification.
        (self.base / "terminal-launched").unlink()
        (self.base / "swap-after-terminal").touch()
        rows = self.invoke("restart", "terminal", code=3)
        app = next(row for row in rows if row["project"] == "app")
        self.assertIn("final-process-incarnation-changed", app["reason"])

    def test_coordinator_survives_invoking_process_replacement(self):
        (self.checkout / "pause-build").touch()
        parent = subprocess.Popen([sys.executable, str(COMMAND), "update", "fixture", "--config", str(self.config)],
                                  env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  start_new_session=True)
        try:
            deadline = time.monotonic() + 10
            while not (self.checkout / "build-started").exists():
                if time.monotonic() > deadline:
                    self.fail("detached coordinator never reached the build")
                time.sleep(0.02)
            parent.terminate()
            _, error = parent.communicate(timeout=5)
            run_id = error.split("project-update: run ", 1)[1].split(";", 1)[0]
            (self.checkout / "continue-build").touch()
            rows = self.invoke("wait", run_id)
            self.assertEqual(rows[0]["outcome"], "ok")
            self.assertIn("verify", rows[0]["completed"])
        finally:
            (self.checkout / "continue-build").touch()
            if parent.poll() is None:
                parent.terminate()
                parent.wait(timeout=5)

    def test_wait_invalid_usage(self):
        result = subprocess.run([sys.executable, str(COMMAND), "wait", "partial-id"],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_unknown_target_is_not_replayed_and_other_target_can_update_again(self):
        hook = self.base / "multi-target.py"
        hook.write_text('''import json, os, pathlib, sys
action=sys.argv[-1]
selected=os.environ.get('PROJECT_UPDATE_TARGET')
targets=['remote-a','remote-b'] if selected is None else [selected]
expected=pathlib.Path('content').read_text()
values=[]
for name in targets:
    with pathlib.Path('native-actions').open('a') as out:
        out.write(json.dumps([action,name])+'\\n')
    runtime=pathlib.Path(name)
    target={'target':name,'expected_identity':expected,
            'running_identity':runtime.read_text() if runtime.exists() else 'old',
            'ready':True,'process':None,'sessions':[]}
    if action=='checkpoint':
        target['checkpoint']={'state':'confirmed','run_id':os.environ['PROJECT_UPDATE_RUN_ID']}
    if action=='restart':
        if name=='remote-a': sys.exit(3)  # unknown post-request outcome
        runtime.write_text(expected)
        target['running_identity']=expected
    values.append(target)
print(json.dumps({'schema_version':1,'targets':values}))
''')
        self.config.write_text(f'[projects.fixture]\npath={json.dumps(str(self.checkout))}\n'
                               f'command={json.dumps([sys.executable, str(hook)])}\n')
        first = self.invoke("restart", "fixture", code=3)[0]
        self.assertEqual([value["outcome"] for value in first["target_results"]], ["incomplete", "ok"])
        log = self.checkout / "native-actions"
        issued = log.read_text().splitlines()
        (self.checkout / "content").write_text("second")
        second = self.invoke("restart", "fixture", code=3)[0]
        self.assertEqual([value["outcome"] for value in second["target_results"]], ["incomplete", "ok"])
        later = [json.loads(line) for line in log.read_text().splitlines()[len(issued):]]
        self.assertFalse(any(target == "remote-a" and action in ("checkpoint", "restart", "restore")
                             for action, target in later))
        self.assertIn(["checkpoint", "remote-b"], later)
        self.assertIn(["restart", "remote-b"], later)
        self.assertEqual((self.checkout / "remote-b").read_text(), "second")

    def test_zellij_build_includes_plugins_for_selected_runtime(self):
        make = self.base / "tools/make"
        make.parent.mkdir()
        log = self.base / "make-actions"
        make.write_text(f"#!{sys.executable}\nimport json, sys\nwith open({str(log)!r}, 'a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n")
        make.chmod(0o755)
        # The build boundary controls Make; stage still needs a selected image.
        binary = self.base / ".local/bin/zellij"
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        (self.base / ".local/.dotfiles-zellij-install").write_text("controlled-build-image\n")
        config = self.base / "machine.toml"
        env = {**self.env, "DOTFILES_CONFIG": str(config),
               "PATH": str(make.parent) + os.pathsep + self.env["PATH"],
               "ZELLIJ_SOCKET_DIR": str(self.base / "zellij-sockets"),
               "XDG_CACHE_HOME": str(self.base / "zellij-cache")}
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
        (scripts / "beads_lifecycle.py").write_text('''import hashlib, json
from pathlib import Path
def artifact_identity(home):
    share=home/'.local/share/beads-service'
    return hashlib.sha256((share/'beads-service.py').read_bytes()).hexdigest()
def inspect(home, action):
    state=home/'beads-runtime.json'
    target=json.loads(state.read_text()) if state.exists() else {
        'target':'local','running_identity':None,'ready':False,'process':None,'sessions':[]}
    target['expected_identity']=artifact_identity(home)
    return {'schema_version':1,'targets':[target]}
''')
        catalog = scripts / "tool.toml"
        catalog.write_text('[tools.beads]\nversion="1.3.4"\ndolt_version="2.7.4"\n')
        profile = self.checkout / "config/beads/trial.toml"
        profile.parent.mkdir(parents=True)
        profile.write_text('profile="trial"\n')
        controller = scripts / "beads-service.py"
        controller.write_text('''import fcntl, json, os, shutil, sys
from pathlib import Path
from beads_lifecycle import inspect
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
    shutil.copyfile(Path(__file__).with_name('beads_lifecycle.py'),share/'beads_lifecycle.py')
    binaries={}
    for name, version in (('bd','9.8.7'),('dolt','8.7.6')):
        binary=share/name
        binary.write_text('#!'+sys.executable+'\\nimport sys\\n'
                          'assert sys.argv[1:] == ["version"]\\n'
                          'print('+repr(name+' version '+version)+')\\n')
        binary.chmod(0o755)
        binaries[name]=str(binary)
    (share/'runtime.json').write_text(json.dumps(binaries))
elif action=='restart':
    if (home/'beads-native-refusal').exists():
        print('Registered Beads service owner differs',file=sys.stderr)
        sys.exit(3)
    with (home/'beads-restarts').open('a') as output: output.write('restart\\n')
    target=inspect(home,'inventory')['targets'][0]
    target.update(running_identity=target['expected_identity'],ready=True)
    target.pop('checkpoint',None)
    (home/'beads-runtime.json').write_text(json.dumps(target))
elif action=='status':
    print(json.dumps({'ready':True}))
elif action in ('inventory','checkpoint','verify','restore'):
    value=inspect(home,action)
    if action=='checkpoint':
        value['targets'][0]['checkpoint']={'state':'confirmed','run_id':os.environ['PROJECT_UPDATE_RUN_ID']}
        (home/'beads-runtime.json').write_text(json.dumps(value['targets'][0]))
    print(json.dumps(value))
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
        self.invoke("restart", "beads", code=3)
        self.invoke("build", "beads")
        self.assertFalse((self.base / "beads-restarts").exists())
        status = self.invoke("status", "beads")[0]["runtime"]
        self.assertEqual(status["installed_revision"], revision)
        self.assertIsNone(status["running_revision"])
        # Darwin receipts report staged native versions, not the catalog pins.
        expected_versions = ({"beads": "9.8.7", "dolt": "8.7.6"} if sys.platform == "darwin"
                             else {"beads": "1.3.4", "dolt": "2.7.4"})
        receipt = json.loads((self.base / ".local/share/beads-service/project-update.json").read_text())
        self.assertEqual(receipt["versions"], expected_versions)
        self.assertEqual(status["installed_versions"], expected_versions)
        self.invoke("restart", "beads")
        self.git(self.checkout, "commit", "--allow-empty", "-m", "Unrelated source revision")
        self.assertEqual(self.invoke("status", "beads")[0]["runtime"]["installed_revision"], revision)
        # Unrelated legacy pins are not Beads artifacts; its local recipe is.
        legacy = self.checkout / "bootstrap/tools.toml"
        legacy.parent.mkdir()
        legacy.write_text('[tools.fzf]\nversion="0.99.0"\n')
        before = json.loads((self.base / ".local/share/beads-service/project-update.json").read_text())
        self.invoke("restart", "beads")
        after = json.loads((self.base / ".local/share/beads-service/project-update.json").read_text())
        self.assertEqual(after, before, "Unrelated catalog edit invalidated Beads staging")
        current = subprocess.check_output([sys.executable, "-c",
            "import json,runpy,sys; print(json.dumps(runpy.run_path(sys.argv[1])['beads_source']()))", str(adapter)],
            env=self.env, text=True)
        self.assertEqual(json.loads(current)["fingerprint"], before["source"]["fingerprint"],
                         "Legacy catalog participates in Beads source identity")
        catalog.write_text(catalog.read_text() + "# changed Beads recipe\n")
        rejected = subprocess.run([sys.executable, str(adapter), "restart"], env=self.env, text=True, capture_output=True)
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
        self.assertIn("Build this Beads source before restarting", rejected.stdout + rejected.stderr)
        self.invoke("build", "beads")
        changed = json.loads((self.base / ".local/share/beads-service/project-update.json").read_text())
        self.assertNotEqual(changed["source"]["fingerprint"], before["source"]["fingerprint"])
        profile.write_text(profile.read_text() + "# local configuration edit\n")
        self.invoke("restart", "beads")  # the selected installation is already running
        controller.write_text(controller.read_text() + "# updated controller image\n")
        self.invoke("build", "beads")
        status = self.invoke("status", "beads")[0]["runtime"]
        self.assertIsNone(status["installed_revision"])
        self.assertTrue(status["installed_source_dirty"])
        self.invoke("restart", "beads")
        state = self.base / "beads-runtime.json"
        runtime = json.loads(state.read_text())
        restarts_before = (self.base / "beads-restarts").read_text().splitlines()
        runtime["ready"] = False
        state.write_text(json.dumps(runtime))
        self.invoke("restart", "beads")
        self.assertTrue(json.loads(state.read_text())["ready"])
        self.assertEqual(len((self.base / "beads-restarts").read_text().splitlines()),
                         len(restarts_before) + 1)
        self.invoke("restart", "beads")
        self.assertEqual(len((self.base / "beads-restarts").read_text().splitlines()),
                         len(restarts_before) + 1, "A healthy current owner was replaced")
        runtime = json.loads(state.read_text())
        runtime["running_identity"] = "previous-native-image"
        state.write_text(json.dumps(runtime))
        (self.base / "beads-native-refusal").touch()
        refused = self.invoke("restart", "beads", code=3)
        self.assertIn("Registered Beads service owner differs", refused[0]["reason"])
        (self.base / "beads-native-refusal").unlink()
        runtime["running_identity"] = runtime["expected_identity"]
        runtime.pop("checkpoint", None)
        state.write_text(json.dumps(runtime))
        installed_helper = self.base / ".local/share/beads-service/beads_config.py"
        installed_helper.write_text("modified outside staging\n")
        self.assertIsNone(self.invoke("status", "beads")[0]["runtime"]["installed_versions"])
        self.invoke("restart", "beads", code=3)
        self.assertEqual((self.base / "beads-restarts").read_text().splitlines(),
                         [*restarts_before, "restart"])
        self.assertEqual(persistent.read_text(), "retained task data")
        self.assertEqual(local_config.read_text(), "# retained operator settings\n")

    def test_worktree_manager_pulls_sources_then_builds_and_activates(self):
        scripts = self.checkout / "scripts"
        scripts.mkdir()
        adapter = scripts / "worktree-manager-update.sh"
        shutil.copyfile(ROOT / "scripts/worktree-manager-update.sh", adapter)
        shutil.copyfile(ROOT / "scripts/worktree-manager-activation.py",
                        scripts / "worktree-manager-activation.py")
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
        actual_git = shutil.which("git")
        self.env["PATH"] = str(self.base / ".local/bin") + os.pathsep + self.env["PATH"]
        (scripts / "install-git-worktree-hooks.sh").write_text('''#!/bin/sh
set -eu
[ -f "$HOME/pulled-git" ]
mkdir -p "$HOME/.local/bin"
''' + f'''cat > "$HOME/.local/bin/git" <<'GIT'
#!/bin/sh
if [ "$1" = --version ]; then
  echo "git version 2.57.0.worktree-hooks.1"
else
  exec {shlex.quote(actual_git)} "$@"
fi
GIT
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
        self.invoke("restart", "worktree-manager", code=3)
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
        stamp = self.base / ".local/.dotfiles-zellij-install"
        stamp.write_text("controlled-selected-image\n")
        env = {**self.env, "PATH": str(binary.parent) + os.pathsep + self.env["PATH"],
               "ZELLIJ_SOCKET_DIR": str(self.base / "zellij-sockets"),
               "XDG_CACHE_HOME": str(self.base / "zellij-cache")}
        # Formatted titles and exit annotations are never native checkpoint evidence.
        for output in ("main [Created 1h ago]", "main [Created 1h ago] (EXITED - attach to resurrect)",
                       "No active zellij sessions found."):
            with self.subTest(output=output):
                binary.write_text(f"#!/bin/sh\nprintf '%s\\n' '{output}'\n")
                binary.chmod(0o755)
                result = subprocess.run([sys.executable, str(ADAPTER), "zellij", "restart"],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 3, result.stderr)
                target = json.loads(result.stdout)["targets"][0]
                self.assertFalse(target["ready"])
                self.assertEqual(target["reason"], "zellij-session-restoration-not-supported")
                self.assertFalse(target["session_replacement_supported"])
                self.assertEqual(target["sessions"], [])

    def test_octo_staging_preserves_legacy_cli_and_requires_native_activation(self):
        (self.checkout / "package.json").write_text(json.dumps({"engines": {"bun": ">=1.4.4"}}))
        binary = self.base / ".local/bin/bun"
        binary.parent.mkdir(parents=True)
        log = self.base / "bun-args"
        binary.write_text(f'#!{sys.executable}\n'
                          'import json, os, pathlib, sys\n'
                          'if sys.argv[1:]==["--version"]: print("1.10.0");sys.exit(0)\n'
                          f'with open({str(log)!r}, "a") as out: out.write(json.dumps(sys.argv[1:]) + "\\n")\n'
                          'if "lifecycle" in sys.argv:\n'
                          ' if sys.argv[-1]=="artifact": print(json.dumps({"expected_identity":"managed-fixture"}))\n'
                          ' elif os.environ.get("PROJECT_UPDATE_OPERATION_DIR"):\n'
                          '  operation=pathlib.Path(os.environ["PROJECT_UPDATE_OPERATION_DIR"])\n'
                          '  observed=operation/"octo-observed.json"\n'
                          '  value=json.loads((observed if observed.exists() else operation/"octo-manager-inventory.json").read_text())\n'
                          '  if sys.argv[-1]=="restore":\n'
                          '   value["targets"][0].pop("checkpoint",None);value["targets"][0]["ready"]=True\n'
                          '   observed.write_text(json.dumps(value))\n'
                          '  print(json.dumps(value))\n'
                          'if "scripts/install-local.ts" in sys.argv:\n'
                          ' if "--stage-only" in sys.argv:\n'
                          '  import shutil, subprocess\n'
                          '  revision=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()\n'
                          '  release=(pathlib.Path(os.environ["HOME"])/".local/share/octo-manager/releases"/revision).resolve()\n'
                          '  (release/"dist").mkdir(parents=True,exist_ok=True)\n'
                          '  (release/"dist/cli.js").write_text("fixture")\n'
                          '  (release/"release.json").write_text(json.dumps({"revision":revision}))\n'
                          '  shutil.copyfile("package.json",release/"package.json")\n'
                          '  print(json.dumps({"schema_version":1,"staged":True,"promoted":False,"release_path":str(release),"revision":revision,"expected_identity":"managed-fixture","bun_requirement":">=1.4.4","platform":"darwin","architecture":"arm64"}));sys.exit(0)\n'
                          ' if os.environ.get("OCTO_NATIVE_REFUSAL"):\n'
                          '  print(json.dumps({"incomplete_activation":True,"reason":"native-service-owner-differs"}));sys.exit(3)\n'
                          ' print(json.dumps({"started":False,"manualCommand":"foreground"}))\n')
        binary.chmod(0o755)
        env = {**self.env, "PATH": str(binary.parent) + os.pathsep + self.env["PATH"]}
        def invoke(action):
            return subprocess.run([sys.executable, str(ADAPTER), "octo-manager", action],
                                  cwd=self.checkout, env=env, text=True, capture_output=True)
        self.assertEqual(invoke("restart").returncode, 1)
        self.assertFalse(log.exists())
        metadata = self.base / ".local/share/octo-manager/current/release.json"
        metadata.parent.mkdir(parents=True)
        metadata.write_text(json.dumps({"revision": "legacy-v1"}))
        legacy_cli = metadata.parent / "dist/cli.js"
        legacy_cli.parent.mkdir()
        legacy_cli.write_text("working legacy CLI")
        before = {path: path.read_bytes() for path in (metadata, legacy_cli)}
        result = invoke("build")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(calls[:2],
                         [["install", "--frozen-lockfile", "--ignore-scripts"], ["scripts/install-local.ts", "--stage-only"]])
        selected = json.loads((self.base / ".local/state/dotfiles/project-update/selected-octo-manager.json").read_text())
        self.assertFalse(selected["promoted"])
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(Path(calls[2][0]), Path(selected["release_path"]) / "dist/cli.js")
        result = invoke("restart")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("detached update checkpoint", json.loads(result.stdout)["targets"][0]["reason"])
        self.assertEqual(len(log.read_text().splitlines()), 5)  # staged artifact/inventory only; no service mutation
        operation = self.base / "octo-operation"
        operation.mkdir(mode=0o700)
        run_id = "11111111-2222-4333-8444-555555555555"
        target = {"target": "local", "expected_identity": "managed-fixture",
                  "running_identity": "old-image", "ready": False,
                  "process": {"pid": 123, "start_identity": "original-start",
                              "native_id": "original-native", "owner_verified": True}, "sessions": [],
                  "checkpoint": {"state": "confirmed", "run_id": run_id}}
        (operation / "octo-manager-inventory.json").write_text(json.dumps({"schema_version": 1, "targets": [target]}))
        (operation / "octo-manager-inventory.json").chmod(0o600)
        env.update(PROJECT_UPDATE_OPERATION_DIR=str(operation), PROJECT_UPDATE_RUN_ID=run_id,
                   OCTO_NATIVE_REFUSAL="1")
        result = invoke("restart")
        self.assertEqual(result.returncode, 3, result.stderr)
        refused = json.loads(result.stdout)["targets"][0]
        self.assertEqual(refused["reason"], "native-service-owner-differs")
        self.assertIn("do not repeat", refused["replacement_outcome"])
        env["PROJECT_UPDATE_RECOVER_ORIGINAL"] = "1"
        released = invoke("restore")
        self.assertEqual(released.returncode, 0, released.stderr)
        restored = json.loads(released.stdout)["targets"][0]
        self.assertTrue(restored["ready"])
        self.assertFalse(restored["selected_cli_ready"])
        self.assertEqual(restored["running_identity"], "old-image")
        self.assertEqual(restored["process"], target["process"])
        self.assertNotIn("checkpoint", restored)
        self.assertEqual(invoke("verify").returncode, 3,
                         "Releasing the original was incorrectly reported as selected-version completion")
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        env.pop("PROJECT_UPDATE_RECOVER_ORIGINAL")
        # A runnable host below the shared minimum cannot establish identity or issue a checkpoint.
        binary.write_text(binary.read_text().replace('print("1.10.0")', 'print("1.4.4")'))
        before = log.read_bytes()
        for action in ("verify", "checkpoint"):
            result = invoke(action)
            self.assertEqual(result.returncode, 3, result.stderr)
            unavailable = json.loads(result.stdout)["targets"][0]
            self.assertIsNone(unavailable["expected_identity"])
            self.assertIn("required-shared-runtime-unavailable", unavailable["reason"])
            if action == "checkpoint":
                self.assertEqual(unavailable["checkpoint"]["state"], "refused")
        self.assertEqual(log.read_bytes(), before, "An incompatible host received a native lifecycle request")

    def test_registered_scope_includes_beads_and_both_approval_projects(self):
        result = subprocess.run([sys.executable, str(COMMAND), "update", "--all", "--dry-run"],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({row["project"] for row in json.loads(result.stdout)},
                         {"octo-manager", "zellij", "beads", "bedrock-router", "intent", "keylease", "worktree-manager", "studio"})
        terminal = next(row for row in json.loads(result.stdout) if row["project"] == "zellij")
        self.assertEqual(terminal["activation"], "deferred")
        self.assertEqual(terminal["steps"], ["pull", "inventory"])

    def test_dotfiles_install_clones_and_preserves_both_tools(self):
        for project, directory in (("intent", "intent"), ("keylease", "1password-agent")):
            with self.subTest(project=project):
                fixture = (f"#!{sys.executable}\n"
                           "import hashlib, json, pathlib, sys\n"
                           f"project = {project!r}\n"
                           "if sys.argv[-1:] == ['artifact']:\n"
                           " print(json.dumps({'expected_identity':'build:fixture-'+project,'sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}))\n"
                           "elif sys.argv[-1:] == ['profiles']: print('[]')\n"
                           "else: sys.exit('unsupported fixture command')\n")
                (self.source / "payload").write_text(fixture)
                (self.source / ".gitignore").write_text("bin/\n")
                (self.source / "Makefile").write_text(
                    "install:\n\tmkdir -p bin $(PREFIX)/bin\n"
                    f"\tcp payload bin/{project}\n\tcp bin/{project} $(PREFIX)/bin/{project}\n\tchmod +x bin/{project} $(PREFIX)/bin/{project}\n")
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
                self.assertEqual((self.base / ".local/bin" / project).read_text(), fixture)

    def test_studio_bootstrap_installs_selected_source_with_shared_runtime(self):
        (self.source / "package.json").write_text(json.dumps({"engines": {"bun": ">=1.4.5"}}))
        (self.source / "scripts").mkdir()
        (self.source / "scripts/lifecycle.mjs").write_text("// Controlled Studio boundary\n")
        self.git(self.source, "add", ".")
        self.git(self.source, "commit", "-m", "Studio fixture")
        self.git(self.source, "push")
        runtime = self.base / ".local/bin/bun"
        runtime.parent.mkdir(parents=True)
        calls = self.base / "studio-calls"
        runtime.write_text(f"#!{sys.executable}\n" + f'''import json, os, sys
from pathlib import Path
args=sys.argv[1:]
if args == ["--version"]:
    print("1.10.0"); sys.exit(0)
assert args[0] == "scripts/lifecycle.mjs", args
with open({str(calls)!r}, "a") as out: out.write(json.dumps([str(Path.cwd()), *args])+"\\n")
if args[1] == "build":
    if Path("fail-build").exists(): sys.exit(12)
    installed=Path.home()/".local/bin/studio"
    installed.parent.mkdir(parents=True,exist_ok=True)
    installed.write_text("installed Studio")
elif args[1] == "status": print(json.dumps({{"installed":True,"running_revision":None}}))
elif args[1] in ("inventory", "verify", "checkpoint"):
    target={{"target":"fixture","expected_identity":"fixture-bundle","running_identity":None,"ready":False,"process":None,"sessions":[],"reason":"legacy-studio-checkpoint-unavailable"}}
    if args[1] == "checkpoint":
        target["checkpoint"]={{"state":"refused","run_id":os.environ.get("PROJECT_UPDATE_RUN_ID")}}
    print(json.dumps({{"schema_version":1,"targets":[target]}}))
    if args[1] != "inventory": sys.exit(3)
elif args[1] == "restart": sys.exit(3)
else: raise AssertionError(args)
''')
        runtime.chmod(0o755)
        env = {**self.env, "PATH": str(runtime.parent) + os.pathsep + self.env["PATH"], "GIT_CONFIG_COUNT": "1",
               "GIT_CONFIG_KEY_0": f"url.{self.origin}.insteadOf",
               "GIT_CONFIG_VALUE_0": "https://github.com/lanej/studio.git"}
        script = '''source "$1"
install_config_runtime() { :; }
load_dotfiles_config() { DOTFILES_TOOLS=studio; DOTFILES_INSTALL_PLAN=$'studio\\tstudio\\tstudio\\t-'; }
install_dependencies
'''
        def install():
            return subprocess.run(["bash", "-c", script, "test", str(ROOT / "bootstrap.sh")],
                                  env=env, text=True, capture_output=True, timeout=20)
        first=install()
        self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
        source=(self.base/"src/studio").resolve()
        self.config.write_text(
            f'[projects.studio]\npath = {json.dumps(str(source))}\n'
            f'command = {json.dumps([sys.executable, str(ROOT / "scripts/install-studio.py")])}\n')
        studio_command = [sys.executable, str(COMMAND), "--config", str(self.config)]
        self.assertEqual((self.base/".local/bin/studio").read_text(),"installed Studio")
        declaration = self.base / ".config/dotfiles/runtime-requirements.d/studio.json"
        self.assertEqual(json.loads(declaration.read_text())["engines"], {"bun": ">=1.4.5"})
        self.assertFalse((self.base / ".local/share/studio/runtime").exists())
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
        status=subprocess.run([*studio_command,"status","studio"],env=env,text=True,capture_output=True)
        self.assertEqual(status.returncode,0,status.stderr)
        self.assertTrue(json.loads(status.stdout)[0]["runtime"]["installed"])
        restart=subprocess.run([*studio_command,"restart","studio"],env=env,text=True,capture_output=True)
        self.assertEqual(restart.returncode,3,restart.stderr + "\n" + restart.stdout)
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
            rejected=subprocess.run([*studio_command,action,"studio"],env=env,text=True,capture_output=True)
            self.assertEqual(rejected.returncode,1,rejected.stderr)
            self.assertIn("Preserve unrecognized Studio checkout",rejected.stdout+rejected.stderr)
        self.assertEqual(calls.read_bytes(),before)
        self.assertFalse(unexpected.exists())

    def test_approval_projects_install_and_preserve_active_sessions(self):
        make = self.base / "tools/make"
        make.parent.mkdir()
        log = self.base / "native-installs"
        fixture = (f"#!{sys.executable}\n"
                   "import hashlib, json, pathlib, sys\n"
                   "project = pathlib.Path(__file__).name\n"
                   "action = sys.argv[-1]\n"
                   "if action == 'artifact':\n"
                   " print(json.dumps({'expected_identity':'build:fixture-'+project,'sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}))\n"
                   "elif action == 'profiles': print('[]')\n"
                   "elif action == 'backends': print('[\"mock\"]')\n"
                   "else: sys.exit('legacy fixture has no activation control')\n")
        make.write_text(f"#!{sys.executable}\n"
                        "import json, os, pathlib, sys\n"
                        f"with open({str(log)!r}, 'a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                        "project = pathlib.Path('selected-project').read_text()\n"
                        "prefix = pathlib.Path(sys.argv[2].split('=', 1)[1])\n"
                        "built = pathlib.Path('bin') / project\n"
                        "built.parent.mkdir(exist_ok=True)\n"
                        f"built.write_text({fixture!r})\n"
                        "built.chmod(0o755)\n"
                        "installed = prefix / 'bin' / project\n"
                        "installed.parent.mkdir(parents=True, exist_ok=True)\n"
                        "installed.write_bytes(built.read_bytes())\n"
                        "installed.chmod(0o755)\n"
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
                self.assertEqual(invoke("restart").returncode, 3)
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
                self.assertEqual(invoke("restart").returncode, 3)
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
                     "if sys.argv[1:]==['lifecycle','identity']:\n"
                     " print(json.dumps({'identity':'build:fixture'}));sys.exit(0)\n"
                     "if sys.argv[1]=='lifecycle':\n"
                     " operation=os.environ.get('PROJECT_UPDATE_OPERATION_DIR')\n"
                     " if operation:\n"
                     "  value=json.loads((pathlib.Path(operation)/'bedrock-router-inventory.json').read_text())\n"
                     "  if (pathlib.Path(os.environ['HOME'])/'router-native-running').exists(): value['targets'][0].update(running_identity='build:fixture',ready=True)\n"
                     "  print(json.dumps(value));sys.exit(0)\n"
                     " sys.exit(3)\n"
                     "if os.environ.get('ROUTER_NATIVE_REFUSAL') and '--no-start' not in sys.argv:\n"
                     " print('Registered router owner differs',file=sys.stderr);sys.exit(3)\n"
                     f"with open({str(log)!r}, 'a') as out: out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                     "installed = pathlib.Path(os.environ.get('CODEX_HOME') or pathlib.Path(os.environ['HOME']) / '.codex') / 'bedrock-router/bedrock-router'\n"
                     "installed.parent.mkdir(parents=True, exist_ok=True)\n"
                     "shutil.copyfile(__file__, installed)\n"
                     "installed.chmod(0o700)\n"
                     "if '--no-start' not in sys.argv: (pathlib.Path(os.environ['HOME'])/'router-native-running').touch()\n"
                     "print('Installed Bedrock router. Original Codex config: fixture')\n")
        go.write_text(f"#!{sys.executable}\nimport pathlib, sys\np = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\np.write_text({installer!r})\np.chmod(0o755)\n")
        go.chmod(0o755)
        builder = self.checkout / "scripts/build-lifecycle.py"
        builder.parent.mkdir()
        builder.write_text("import hashlib, json, pathlib, sys\n"
                           f"p=pathlib.Path(sys.argv[sys.argv.index('--output')+1]);p.write_text({installer!r});p.chmod(0o755)\n"
                           "manifest=pathlib.Path(sys.argv[sys.argv.index('--manifest')+1])\n"
                           "manifest.write_text(json.dumps({'expected_identity':'build:fixture','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))\n")
        self.git(self.checkout, "add", "scripts/build-lifecycle.py")
        self.git(self.checkout, "commit", "-m", "Native builder fixture")
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
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("detached update checkpoint", json.loads(result.stdout)["targets"][0]["reason"])
        staged, = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(staged, ["install", "--config", str(self.checkout.resolve() / "config.json"),
                                  "--keep-env", "--preserve-mcp", "--no-start"])
        operation = self.base / "router-operation"
        operation.mkdir(mode=0o700)
        target = {"target": "local", "expected_identity": "build:fixture",
                  "running_identity": "build:previous", "ready": False, "process": None, "sessions": [],
                  "checkpoint": {"state": "confirmed", "run_id": "11111111-2222-4333-8444-555555555555"}}
        (operation / "bedrock-router-inventory.json").write_text(json.dumps({"schema_version": 1, "targets": [target]}))
        (operation / "bedrock-router-inventory.json").chmod(0o600)
        env.update(PROJECT_UPDATE_OPERATION_DIR=str(operation),
                   PROJECT_UPDATE_RUN_ID=target["checkpoint"]["run_id"], ROUTER_NATIVE_REFUSAL="1")
        refused = invoke("restart")
        self.assertEqual(refused.returncode, 3, refused.stderr)
        refused_target = json.loads(refused.stdout)["targets"][0]
        self.assertIn("Registered router owner differs", refused_target["reason"])
        self.assertIn("do not repeat", refused_target["replacement_outcome"])
        env.pop("ROUTER_NATIVE_REFUSAL")
        successful = invoke("restart")
        self.assertEqual(successful.returncode, 0, successful.stderr)
        self.assertTrue(json.loads(successful.stdout)["targets"][0]["ready"])
        for name in ("PROJECT_UPDATE_OPERATION_DIR", "PROJECT_UPDATE_RUN_ID", "ROUTER_NATIVE_REFUSAL"):
            env.pop(name, None)
        installed = codex_home / "bedrock-router/bedrock-router"
        config = installed.parent / "config.json"
        config.write_text('{"port":18088}\n')
        self.assertEqual(invoke("build").returncode, 0)
        custom = json.loads(log.read_text().splitlines()[-1])
        self.assertEqual(custom[custom.index("--config") + 1], str(config))
        self.assertEqual(config.read_text(), '{"port":18088}\n')
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
        self.assertEqual(len(log.read_text().splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
