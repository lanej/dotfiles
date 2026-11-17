"""Exercise the real coordinator entrypoints against local Git and controlled gh."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GIT = shutil.which("git")
PYTHON = shutil.which("python3")
GH = r"""
import json, os, subprocess, sys
from pathlib import Path
args = sys.argv[1:]
state_path = Path(os.environ["FIXTURE_STATE"])
state = json.loads(state_path.read_text())
remote = state["remote"]
with Path(os.environ["FIXTURE_TRACE"]).open("a") as out:
    out.write(json.dumps(args) + "\n")
def git(*items):
    return subprocess.check_output([state["git"], "--git-dir", remote, *items], text=True).strip()
if args[:2] == ["repo", "view"]:
    print(json.dumps({"url": Path(remote).as_uri(), "sshUrl": Path(remote).as_uri()}))
elif args[:2] == ["pr", "view"]:
    head = git("rev-parse", "refs/heads/feature")
    published = head != state["captured"]
    if state["mode"] == "api-error" and published:
        sys.exit("fixture API unavailable")
    if state["mode"] == "malformed" and published:
        print("not json")
        sys.exit(0)
    check = {"__typename": "CheckRun", "name": "acceptance", "status": "COMPLETED", "conclusion": "SUCCESS"}
    if published and state["mode"] == "pending":
        check.update(status="IN_PROGRESS", conclusion="")
    if published and state["mode"] in ("failed", "cancelled"):
        check["conclusion"] = "FAILURE" if state["mode"] == "failed" else "CANCELLED"
    checks = [] if state["mode"] == "empty" else [check]
    response = {"state": "MERGED" if state.get("merged") else "OPEN", "headRefName": "feature",
                "headRefOid": head, "baseRefName": "main", "isDraft": False,
                "isCrossRepository": False, "reviewDecision": "", "statusCheckRollup": checks,
                "mergeCommit": {"oid": state.get("merge_commit")} if state.get("merged") else None}
    if published and state["mode"] == "head-change":
        subprocess.run([state["git"], "--git-dir", remote, "update-ref", "refs/heads/feature", state["base"]], check=True)
        response["headRefOid"] = state["base"]
    if not published:
        state["previews"] = state.get("previews", 0) + 1
        if state["mode"] == "concurrent-push" and state["previews"] == 2:
            subprocess.run([state["git"], "--git-dir", remote, "update-ref", "refs/heads/feature", state["base"]], check=True)
    state_path.write_text(json.dumps(state))
    print(json.dumps(response))
elif args[:2] == ["pr", "merge"]:
    assert "--match-head-commit" in args, args
    expected = args[args.index("--match-head-commit") + 1]
    if state["mode"] == "merge-error" or git("rev-parse", "refs/heads/feature") != expected:
        sys.exit("fixture merge refused")
    if state["mode"] != "unconfirmed":
        state["merged"] = True
        state["merge_commit"] = state["captured"] if state["mode"] == "false-confirmation" else expected
        if state["mode"] != "false-confirmation":
            subprocess.run([state["git"], "--git-dir", remote, "update-ref", "refs/heads/main", expected], check=True)
        state_path.write_text(json.dumps(state))
else:
    sys.exit("unexpected fixture gh command: " + repr(args))
"""


class Coordinator(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coordinator-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(
            os.environ,
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Fixture",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_NAME="Fixture",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
        )
        self.remote = self.root / "remote.git"
        seed = self.root / "seed"
        self.command("init", "--bare", "--initial-branch=main", str(self.remote))
        self.command("init", "--initial-branch=main", str(seed))
        self.configure(seed)
        (seed / "README").write_text("baseline\n")
        (seed / ".golangci.yml").write_text("  path-except: ^internal/(base/)\n")
        self.commit(seed, "baseline")
        self.command("-C", str(seed), "remote", "add", "origin", str(self.remote))
        self.command("-C", str(seed), "push", "origin", "main")
        self.command("-C", str(seed), "checkout", "-b", "feature")
        (seed / "feature").write_text("retained behavior\n")
        self.commit(seed, "feature")
        self.captured = self.command(
            "-C", str(seed), "rev-parse", "HEAD"
        ).stdout.strip()
        self.command("-C", str(seed), "push", "origin", "feature")
        self.command("-C", str(seed), "checkout", "main")
        (seed / "base-update").write_text("new main\n")
        self.commit(seed, "advance main")
        self.base = self.command("-C", str(seed), "rev-parse", "HEAD").stdout.strip()
        self.command("-C", str(seed), "push", "origin", "main")
        self.work = self.root / "work"
        self.command("clone", str(self.remote), str(self.work))
        self.configure(self.work)
        self.meta = self.root / "metadata"
        self.meta.mkdir()
        self.metadata()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(f"#!{PYTHON}\n" + GH)
        gh.chmod(0o755)
        self.state_path = self.root / "state.json"
        self.trace = self.root / "trace"
        self.env.update(
            PATH=str(self.bin) + os.pathsep + self.env["PATH"],
            EPSCTL_REPO="fixture/repo",
            EPSCTL_MERGE_DIR=str(self.work),
            EPSCTL_MERGE_META=str(self.meta),
            EPSCTL_MERGE_ATTEMPTS="2",
            EPSCTL_MERGE_INTERVAL="0",
            FIXTURE_STATE=str(self.state_path),
            FIXTURE_TRACE=str(self.trace),
        )
        self.mode("success")

    def command(self, *args):
        return subprocess.run(
            [GIT, *args], env=self.env, text=True, capture_output=True, check=True
        )

    def configure(self, path):
        for key, value in (("core.hooksPath", os.devnull), ("commit.gpgsign", "false")):
            self.command("-C", str(path), "config", key, value)

    def commit(self, path, message):
        self.command("-C", str(path), "add", ".")
        self.command("-C", str(path), "commit", "-m", message)

    def metadata(self, captured=None, replay=None):
        fields = [
            "feature",
            "main",
            "OPEN",
            replay or self.captured,
            captured or self.captured,
        ]
        (self.meta / "1.tsv").write_text("\t".join(fields) + "\n")

    def mode(self, name):
        self.state_path.write_text(
            json.dumps(
                {
                    "mode": name,
                    "git": GIT,
                    "remote": str(self.remote),
                    "captured": self.captured,
                    "base": self.base,
                }
            )
        )

    def execute(self, *numbers):
        return subprocess.run(
            ["bash", str(ROOT / "bin/merge-seq.sh"), *(numbers or ("1",))],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def calls(self):
        return (
            [json.loads(line) for line in self.trace.read_text().splitlines()]
            if self.trace.exists()
            else []
        )

    def assert_stopped(self, result, merge_requested=False):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls()
        self.assertEqual(
            any(c[:2] == ["pr", "merge"] for c in calls), merge_requested, calls
        )
        self.assertFalse(any(c[:3] == ["pr", "view", "2"] for c in calls), calls)
        self.assertNotIn("ALL DONE", result.stdout)
        self.assertNotIn(" MERGED:", result.stdout)

    def test_publishes_checks_and_confirms_exact_head(self):
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        state = json.loads(self.state_path.read_text())
        self.assertTrue(state["merged"])
        head = self.command(
            "--git-dir", str(self.remote), "rev-parse", "feature"
        ).stdout.strip()
        merge = next(c for c in self.calls() if c[:2] == ["pr", "merge"])
        self.assertEqual(merge[merge.index("--match-head-commit") + 1], head)
        self.assertEqual(
            self.command(
                "--git-dir", str(self.remote), "rev-parse", "main"
            ).stdout.strip(),
            head,
        )

    def test_push_failure_cannot_reach_merge(self):
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.assert_stopped(self.execute("1", "2"))
        self.assertEqual(
            self.command(
                "--git-dir", str(self.remote), "rev-parse", "feature"
            ).stdout.strip(),
            self.captured,
        )

    def test_stale_head_and_incomplete_metadata_are_rejected_before_replay(self):
        self.metadata(captured=self.base)
        self.assert_stopped(self.execute())
        self.assertEqual(
            self.command(
                "-C", str(self.work), "branch", "--show-current"
            ).stdout.strip(),
            "main",
        )
        self.metadata(replay=self.base)
        self.assert_stopped(self.execute())

    def test_legacy_metadata_requires_a_captured_head(self):
        (self.meta / "1.tsv").write_text(f"feature\tmain\tOPEN\t{self.captured}\n")
        self.assert_stopped(self.execute())

    def test_concurrent_remote_update_is_not_overwritten(self):
        self.mode("concurrent-push")
        self.assert_stopped(self.execute("1", "2"))
        self.assertEqual(
            self.command(
                "--git-dir", str(self.remote), "rev-parse", "feature"
            ).stdout.strip(),
            self.base,
        )

    def test_unavailable_unsuccessful_or_unpinned_checks_cannot_merge(self):
        for mode in (
            "pending",
            "empty",
            "failed",
            "cancelled",
            "api-error",
            "malformed",
            "head-change",
        ):
            with self.subTest(mode=mode):
                self.mode(mode)
                self.trace.unlink(missing_ok=True)
                # Every attempt begins from the captured, unchanged remote head.
                self.command(
                    "--git-dir",
                    str(self.remote),
                    "update-ref",
                    "refs/heads/feature",
                    self.captured,
                )
                result = self.execute("1", "2")
                self.assert_stopped(result)

    def test_merge_error_and_unconfirmed_outcome_do_not_advance_sequence(self):
        for mode in ("merge-error", "unconfirmed", "false-confirmation"):
            with self.subTest(mode=mode):
                self.mode(mode)
                self.trace.unlink(missing_ok=True)
                self.command(
                    "--git-dir",
                    str(self.remote),
                    "update-ref",
                    "refs/heads/feature",
                    self.captured,
                )
                self.assert_stopped(self.execute("1", "2"), merge_requested=True)

    def test_repository_local_pr_numbers_do_not_select_vendor_scopes(self):
        shutil.copy2(self.meta / "1.tsv", self.meta / "414.tsv")
        result = self.execute("414")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = self.command(
            "--git-dir", str(self.remote), "show", "main:.golangci.yml"
        ).stdout
        self.assertEqual(config, "  path-except: ^internal/(base/)\n")

    def test_dirty_checkout_is_preserved(self):
        (self.work / "local-work").write_text("keep me\n")
        self.assert_stopped(self.execute())
        self.assertEqual((self.work / "local-work").read_text(), "keep me\n")

    def test_git_failures_stop_before_publication(self):
        for operation in ("checkout", "cherry-pick"):
            with self.subTest(operation=operation):
                self.mode("success")
                self.command(
                    "--git-dir",
                    str(self.remote),
                    "update-ref",
                    "refs/heads/feature",
                    self.captured,
                )
                self.trace.unlink(missing_ok=True)
                shim = self.bin / "git"
                shim.write_text(
                    f"#!{PYTHON}\nimport os,sys\nif {operation!r} in sys.argv[1:]: sys.exit(1)\nos.execv({GIT!r}, [{GIT!r}, *sys.argv[1:]])\n"
                )
                shim.chmod(0o755)
                self.assert_stopped(self.execute("1", "2"))

    def test_multiple_push_destinations_are_rejected(self):
        self.command(
            "-C",
            str(self.work),
            "config",
            "--add",
            "remote.origin.pushurl",
            str(self.remote),
        )
        self.command(
            "-C",
            str(self.work),
            "config",
            "--add",
            "remote.origin.pushurl",
            str(self.root / "other.git"),
        )
        self.assert_stopped(self.execute())
        self.assertEqual(
            self.command(
                "--git-dir", str(self.remote), "rev-parse", "feature"
            ).stdout.strip(),
            self.captured,
        )

    def test_lint_adapter_preserves_surroundings_and_rejects_broader_hunks(self):
        directory = self.root / "lint"
        directory.mkdir()
        path = directory / ".golangci.yml"
        one_line = "before: keep\n<<<<<<< HEAD\n  path-except: ^internal/(base/|ours/)\n||||||| base\n  path-except: ^internal/(base/)\n=======\n  path-except: ^internal/(base/|theirs/)\n>>>>>>> theirs\nafter: keep\n"
        path.write_text(one_line)
        command = [PYTHON, str(ROOT / "bin/resolve-golangci.py")]
        result = subprocess.run(
            command, cwd=directory, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            path.read_text(),
            "before: keep\n  path-except: ^internal/(base/|ours/|theirs/)\nafter: keep\n",
        )
        combined = one_line.replace(
            "<<<<<<< HEAD\n", "<<<<<<< HEAD\n  another-setting: keep-me\n"
        )
        path.write_text(combined)
        rejected = subprocess.run(
            command, cwd=directory, capture_output=True, text=True, check=False
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertEqual(
            path.read_text(), combined, "unsupported conflicts must be left untouched"
        )

    def test_init_preserves_state_and_reports_persistence_failure(self):
        destination = self.root / "live"
        command = ["bash", str(ROOT / "init.sh"), str(destination)]
        first = subprocess.run(
            command, check=False, env=self.env, text=True, capture_output=True
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        installed = subprocess.run(
            ["bash", str(destination / "bin/merge-seq.sh")],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(installed.returncode, 64, installed.stderr)
        self.assertIn("usage: merge-seq.sh", installed.stderr)
        state = destination / "STATE.md"
        state.write_text("retained operator state\n")
        second = subprocess.run(
            command, check=False, env=self.env, text=True, capture_output=True
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(state.read_text(), "retained operator state\n")
        shim = self.bin / "git"
        shim.write_text(
            f"#!{PYTHON}\nimport os,sys\nif 'commit' in sys.argv: sys.exit(17)\nos.execv({GIT!r}, [{GIT!r}, *sys.argv[1:]])\n"
        )
        shim.chmod(0o755)
        state.write_text("new state needing persistence\n")
        failed = subprocess.run(
            command, check=False, env=self.env, text=True, capture_output=True
        )
        self.assertEqual(failed.returncode, 17, failed.stdout + failed.stderr)
        self.assertNotIn("coordinator state ready:", failed.stdout)
        self.assertEqual(state.read_text(), "new state needing persistence\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
