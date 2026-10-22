#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets==15.0.1"]
# ///
"""Exercise SessionEnd registration and cleanup against real Git and lsof."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time

from websockets.sync.server import unix_serve


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "bin/codex-worktree-exit-hook"


def wait_for(predicate):
    deadline = time.monotonic() + 40
    while not predicate():
        assert time.monotonic() < deadline, "exit worker did not finish"
        time.sleep(0.1)


def main():
    with tempfile.TemporaryDirectory(prefix="cx-exit-", dir="/tmp") as name:
        folder = Path(name).resolve()
        home = folder / "codex"
        socket = home / "app-server-control/app-server-control.sock"
        socket.parent.mkdir(parents=True)
        original = {"hooks": {"SessionEnd": [{"matcher": "existing", "hooks": [
            {"type": "command", "command": "existing-hook", "timeout": 1},
        ]}]}, "custom": "preserve"}
        (home / "hooks.json").write_text(json.dumps(original))
        wrappers = folder / "wrappers"
        wrappers.mkdir()
        paseo = wrappers / "paseo"
        paseo.write_text("#!/bin/sh\nprintf '[]\\n'\n")
        paseo.chmod(0o755)
        env = {**os.environ, "CODEX_HOME": str(home),
               "PATH": str(wrappers) + os.pathsep + os.environ["PATH"],
               "UV_CACHE_DIR": subprocess.check_output(
                   ["uv", "cache", "dir"], text=True).strip(),
               "XDG_CACHE_HOME": str(folder / "cache"),
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        env.pop("WORKTREE_CLEANUP_BASE_BRANCH", None)
        env.pop("WORKTREE_CLEANUP_AGE_HOURS", None)

        def git(repo, *args):
            return subprocess.check_output(
                ["git", "-c", "user.name=Exit check",
                 "-c", "user.email=exit@example.invalid",
                 "-c", "commit.gpgsign=false", "-C", str(repo), *args],
                env=env, text=True, stderr=subprocess.PIPE,
            ).strip()

        project = folder / "project"
        project.mkdir()
        git(project, "init", "-q", "--initial-branch", "main")
        (project / ".gitignore").write_text(".worktrees/\n.codex/\n")
        git(project, "add", ".gitignore")
        git(project, "commit", "-qm", "Initialize exit fixture")
        ended = project / ".worktrees/ended"
        sibling = project / ".worktrees/other-completed-task"
        git(project, "worktree", "add", "-b", "completed-task", str(ended))
        git(project, "worktree", "add", "-b", "other-task", str(sibling))
        (ended / "completed.txt").write_text("Preserve the completed change.\n")
        git(ended, "add", "completed.txt")
        git(ended, "commit", "-qm", "Complete the task")
        completed_head = git(ended, "rev-parse", "HEAD")
        git(project, "merge", "--squash", "completed-task")
        git(project, "commit", "-qm", "Squash the completed task")
        config = ended / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text("[desktop]\ngit-worktree-root = " +
                          json.dumps(str(project / ".worktrees")) + "\n")
        expected_config = config.read_bytes()

        for _ in range(2):
            subprocess.run([sys.executable, str(HOOK), "--install"], env=env,
                           cwd=folder, check=True, timeout=3)
        installed = json.loads((home / "hooks.json").read_text())
        assert installed["custom"] == original["custom"]
        assert installed["hooks"]["SessionEnd"][:-1] == original["hooks"]["SessionEnd"]
        assert len(installed["hooks"]["SessionEnd"]) == 2
        command = installed["hooks"]["SessionEnd"][-1]["hooks"][0]["command"]
        event = {"hook_event_name": "SessionEnd", "session_id": "ending",
                 "cwd": str(ended)}
        threads = {
            "ending": {"id": "ending", "cwd": str(ended), "status": {"type": "idle"}},
            "other": {"id": "other", "cwd": str(ended), "status": {"type": "idle"}},
        }
        lock = threading.Lock()

        def handler(connection):
            for raw in connection:
                message = json.loads(raw)
                if "id" not in message:
                    continue
                method = message["method"]
                with lock:
                    if method == "initialize":
                        result = {}
                    elif method == "thread/loaded/list":
                        result = {"data": list(threads), "nextCursor": None}
                    elif method == "thread/read":
                        result = {"thread": threads[message["params"]["threadId"]]}
                    elif method in {"thread/queue/list", "thread/backgroundTerminals/list"}:
                        result = {"data": [], "nextCursor": None}
                    elif method == "thread/goal/get":
                        result = {"goal": None}
                    else:
                        raise AssertionError("unexpected RPC: " + method)
                connection.send(json.dumps({"id": message["id"], "result": result}))

        log = home / "log/worktree-exit.jsonl"

        def records():
            return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

        def end():
            subprocess.run(["/bin/sh", "-c", command], input=json.dumps(event),
                           text=True, env=env, cwd=ended, check=True, timeout=3)

        with unix_serve(handler, str(socket), ping_interval=None) as server:
            serving = threading.Thread(target=server.serve_forever)
            serving.start()
            process = None
            try:
                end()
                wait_for(lambda: records())
                assert records()[-1]["reason"] == "another Codex session references this checkout"
                assert config.read_bytes() == expected_config and ended.is_dir()
                with lock:
                    del threads["other"]
                custom_config = b"# Keep my settings.\n" + expected_config
                config.write_bytes(custom_config)
                end()
                wait_for(lambda: len(records()) == 2)
                assert records()[-1]["action"] == "retained"
                assert records()[-1]["reason"] == "ignored files"
                assert ended.is_dir() and config.read_bytes() == custom_config
                config.write_bytes(expected_config)
                # The exiting process can still hold its cwd after SessionEnd.
                process = subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(120)"], cwd=ended,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                end()
                time.sleep(1)
                assert ended.is_dir(), "removed a checkout with an active process"
                process.terminate()
                process.wait(timeout=5)
                wait_for(lambda: any(row["action"] == "removed" for row in records()))
                assert not ended.exists() and sibling.is_dir()
                registered = git(project, "worktree", "list", "--porcelain")
                assert str(ended) not in registered and str(sibling) in registered
                assert git(project, "rev-parse", "refs/heads/completed-task") == completed_head
                assert (project / "completed.txt").read_text() == "Preserve the completed change.\n"
                assert git(project, "show-ref", "--verify", "refs/heads/other-task")
                assert git(project, "status", "--porcelain") == ""
                git(project, "worktree", "remove", str(sibling))
            finally:
                if process is not None and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                server.shutdown()
                serving.join(timeout=5)
    print("PASS: SessionEnd retains another agent and an exiting process, then removes "
          "only the squash-integrated checkout, preserving commits and existing hooks.")


if __name__ == "__main__":
    main()
