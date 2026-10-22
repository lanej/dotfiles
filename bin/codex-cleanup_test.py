"""Exercise report and cleanup through the CLI and a real Unix WebSocket."""

import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time

import pytest


ROOT = Path(__file__).resolve().parent.parent

SERVER = '''
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets==15.0.1"]
# ///
import json
import sys
import threading
from pathlib import Path
from websockets.sync.server import unix_serve

folder = Path(sys.argv[1])
threads = json.loads((folder / "threads.json").read_text())
loaded = [thread_id for thread_id, thread in threads.items()
          if thread["status"]["type"] != "notLoaded"]
calls = []
lock = threading.Lock()

def handler(connection):
    reads = {}
    for raw in connection:
        message = json.loads(raw)
        if "id" not in message:
            continue
        method, params = message["method"], message["params"]
        thread_id = params.get("threadId")
        with lock:
            calls.append({"method": method, "thread_id": thread_id})
            if method == "initialize":
                result = {}
            elif method == "server/diagnostics":
                result = {
                    "process": {"residentMemoryBytes": 1048576},
                    "gauges": [{"name": "mcp.connections.live", "value": len(loaded) * 11}],
                }
            elif method == "thread/loaded/list":
                if params.get("cursor") is None:
                    result = {"data": loaded[:2], "nextCursor": "second-page"}
                else:
                    result = {"data": loaded[2:], "nextCursor": None}
            elif method == "thread/read":
                reads[thread_id] = reads.get(thread_id, 0) + 1
                if thread_id == "changed" and reads[thread_id] > 1:
                    threads[thread_id]["status"] = {"type": "active"}
                if thread_id == "reloaded" and thread_id not in loaded:
                    threads[thread_id]["status"] = {"type": "active"}
                    loaded.append(thread_id)
                result = {"thread": threads[thread_id]}
            elif method == "thread/list":
                child = threads["unloaded-child"]
                visible = (
                    params.get("ancestorThreadId") == child["parentThreadId"]
                    and "subAgentThreadSpawn" in params.get("sourceKinds", [])
                    and params.get("archived") == (
                        Path(child["path"]).parent.name == "archived_sessions"
                    )
                )
                result = {"data": [child] if visible else [], "nextCursor": None}
            elif method == "thread/queue/list":
                result = {"data": [{"id": "pending-prompt"}] if thread_id == "queued" else [],
                          "nextCursor": None}
            elif method == "thread/backgroundTerminals/list":
                if threads[thread_id]["status"]["type"] == "notLoaded":
                    raise AssertionError("unloaded ancestor has no runtime terminals to inspect")
                result = {"data": [], "nextCursor": None}
            elif method == "thread/goal/get":
                blocked = thread_id in {"unloaded-child", "unloaded-busy-parent"}
                result = {"goal": {"status": "blocked"} if blocked else None}
            elif method == "thread/turns/list":
                result = {"data": [{"status": "completed", "completedAt": threads[thread_id]["completed"]}],
                          "nextCursor": None}
            elif method == "thread/unarchive":
                thread = threads[thread_id]
                transcript = Path(thread["path"])
                restored = folder / transcript.name
                transcript.rename(restored)
                thread["path"] = str(restored)
                if thread_id == "resuming":
                    thread["status"] = {"type": "active"}
                result = {"thread": thread}
            elif method == "thread/archive":
                thread = threads[thread_id]
                assert thread["status"]["type"] == "idle", "attempted to archive active helper"
                assert thread_id in {"finished", "stale", "reloaded"}, (
                    "attempted to archive protected helper"
                )
                transcript = Path(thread["path"])
                if transcript.parent.name != "archived_sessions":
                    archived = folder / "archived_sessions" / transcript.name
                    transcript.rename(archived)
                    thread["path"] = str(archived)
                    thread["status"] = {"type": "notLoaded"}
                    loaded.remove(thread_id)
                result = {}
            else:
                raise AssertionError(f"unexpected RPC: {method}")
            (folder / "calls.json").write_text(json.dumps(calls))
        connection.send(json.dumps({"id": message["id"], "result": result}))

with unix_serve(handler, str(folder / "daemon.sock"), ping_interval=None) as server:
    (folder / "ready").touch()
    server.serve_forever()
'''


def test_archives_old_idle_helpers_with_unknown_attachment_and_retains_busy_or_recent_work():
    uv = shutil.which("uv")
    assert uv, "uv is required to run the self-contained cleanup command"
    # Keep Unix socket paths below macOS's length limit.
    with tempfile.TemporaryDirectory(prefix="codex-cleanup-", dir="/tmp") as name:
        folder = Path(name)
        (folder / "archived_sessions").mkdir()
        completed = int(time.time()) - 3600
        threads = {
            "primary": {"parentThreadId": None, "status": {"type": "active"}},
            "protected": {"parentThreadId": "primary", "status": {"type": "idle"}},
            "finished": {"parentThreadId": "unloaded-parent", "status": {"type": "idle"}},
            "resuming": {"parentThreadId": "unloaded-parent", "status": {"type": "idle"}},
            "queued": {"parentThreadId": "unloaded-parent", "status": {"type": "idle"}},
            "subtree": {"parentThreadId": "unloaded-parent", "status": {"type": "idle"}},
            "unloaded-child": {"parentThreadId": "subtree", "status": {"type": "notLoaded"}},
            "blocked": {"parentThreadId": "unloaded-busy-parent", "status": {"type": "idle"}},
            "unloaded-busy-parent": {"parentThreadId": None, "status": {"type": "notLoaded"}},
            "stale": {"parentThreadId": "unloaded-parent", "status": {"type": "idle"}},
            "recent": {"parentThreadId": "unloaded-parent", "status": {"type": "idle"}},
            "changed": {"parentThreadId": "unloaded-parent", "status": {"type": "idle"}},
            "reloaded": {"parentThreadId": "unloaded-parent", "status": {"type": "idle"}},
            "unloaded-parent": {"parentThreadId": None, "status": {"type": "notLoaded"}},
        }
        for thread_id, thread in threads.items():
            transcript = folder / f"{thread_id}.jsonl"
            transcript.write_text(f"saved conversation for {thread_id}\n")
            thread.update(id=thread_id, path=str(transcript), ephemeral=False,
                          agentRole="reviewer" if thread["parentThreadId"] else None,
                          cwd="/project", completed=completed)
        threads["recent"]["completed"] = int(time.time()) - 1800
        archived = folder / "archived_sessions/stale.jsonl"
        Path(threads["stale"]["path"]).rename(archived)
        threads["stale"]["path"] = str(archived)
        queued = folder / "archived_sessions/queued.jsonl"
        Path(threads["queued"]["path"]).rename(queued)
        threads["queued"]["path"] = str(queued)
        resuming = folder / "archived_sessions/resuming.jsonl"
        Path(threads["resuming"]["path"]).rename(resuming)
        threads["resuming"]["path"] = str(resuming)
        (folder / "threads.json").write_text(json.dumps(threads))
        server_file = folder / "server.py"
        server_file.write_text(SERVER)
        with (folder / "server.log").open("w") as log:
            server = subprocess.Popen(
                [uv, "run", "--script", str(server_file), str(folder)],
                stdout=log, stderr=log, start_new_session=True,
            )
            try:
                deadline = time.monotonic() + 30
                while not (folder / "ready").exists():
                    if server.poll() is not None or time.monotonic() >= deadline:
                        raise AssertionError((folder / "server.log").read_text())
                    time.sleep(0.02)
                command = [uv, "run", "--script", str(ROOT / "bin/codex-cleanup"),
                           "--socket", str(folder / "daemon.sock"),
                           "--worktree-root", str(folder), "--json"]
                script_env = {**os.environ, "CODEX_HOME": str(folder)}
                preview = subprocess.run(command + ["--color", "always"],
                                         capture_output=True, text=True, timeout=30,
                                         env=script_env)
                assert preview.returncode == 0, preview.stderr
                plan = json.loads(preview.stdout)
                assert {r["id"] for r in plan["threads"] if r["action"] == "candidate"} == {
                    "finished", "stale", "resuming", "changed", "reloaded",
                }
                assert next(r for r in plan["threads"] if r["id"] == "finished")["reason"] == (
                    "old idle helper; client attachment status unavailable"
                )
                assert next(r for r in plan["threads"] if r["id"] == "recent")["reason"] == (
                    "completed less than 60 minutes ago"
                )
                human = subprocess.run(
                    command[:-1] + ["--color", "always"], capture_output=True, text=True,
                    timeout=30, env={**script_env, "COLUMNS": "160"},
                )
                assert human.returncode == 0, human.stderr
                assert "\033[36mretained" in human.stdout
                assert "\033[33mcandidate" in human.stdout
                assert "client attachment status unavailable" in human.stdout
                lines = re.sub(r"\033\[[0-9;]*m", "", human.stdout).splitlines()
                header = next(line for line in lines if line.startswith("ACTION"))
                primary = next(line for line in lines
                               if line.split()[:2] == ["retained", "primary"])
                finished = next(line for line in lines
                                if line.split()[:2] == ["candidate", "finished"])
                assert primary.index("primary") == finished.index("finished") == header.index("THREAD")
                assert primary.index("primary", header.index("ROLE")) == header.index("ROLE")
                assert finished.index("reviewer") == header.index("ROLE")
                assert finished[header.index("REASON"):].startswith(
                    "old idle helper; client attachment status unavailable"
                )
                assert not any(c["method"] in {"thread/archive", "thread/unarchive"}
                               for c in json.loads((folder / "calls.json").read_text()))
                applied = subprocess.run(command + ["--apply"], capture_output=True,
                                         text=True, timeout=30, env=script_env)
                assert applied.returncode == 1, applied.stderr
                result = json.loads(applied.stdout)
                assert {r["id"] for r in result["threads"] if r["action"] == "archived"} == {
                    "finished", "stale",
                }
                assert {r["id"] for r in result["threads"] if r["action"] == "retained"} == {
                    "primary", "protected", "resuming", "queued", "subtree", "blocked",
                    "recent", "changed",
                }
                assert next(r for r in result["threads"] if r["id"] == "stale")["reason"] == (
                    "runtime unloaded; client attachment status unavailable"
                )
                changed = next(r for r in result["threads"] if r["id"] == "changed")
                assert changed["reason"] == "runtime status: active"
                resuming = next(r for r in result["threads"] if r["id"] == "resuming")
                assert resuming["reason"] == "runtime status: active"
                assert resuming["transcript_restored"] is True
                reloaded = next(r for r in result["threads"] if r["id"] == "reloaded")
                assert reloaded["action"] == "unconfirmed"
                assert reloaded["reason"] == "archive returned; runtime reloaded"
                calls = json.loads((folder / "calls.json").read_text())
                assert {c["thread_id"] for c in calls if c["method"] == "thread/archive"} == {
                    "finished", "stale", "reloaded",
                }
                assert {c["thread_id"] for c in calls if c["method"] == "thread/unarchive"} == {
                    "stale", "resuming",
                }
                assert not (folder / "finished.jsonl").exists()
                assert (folder / "archived_sessions/finished.jsonl").read_text() == (
                    "saved conversation for finished\n"
                )
                assert (folder / "archived_sessions/stale.jsonl").read_text() == (
                    "saved conversation for stale\n"
                )
                assert (folder / "resuming.jsonl").read_text() == (
                    "saved conversation for resuming\n"
                )
                assert (folder / "archived_sessions/queued.jsonl").exists()
                assert result["after"]["gauges"]["mcp.connections.live"] == 99
            finally:
                try:
                    os.killpg(server.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait(timeout=5)


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS provides verified stdio pipe peers")
def test_mcp_cleanup_exits_orphaned_stdio_server_and_preserves_live_client():
    uv = shutil.which("uv")
    assert uv, "uv is required to run the cleanup command"
    with tempfile.TemporaryDirectory(prefix="codex-mcp-", dir="/tmp") as name:
        folder = Path(name)
        fixture = folder / "stdio.py"
        fixture.write_text(
            "import os,signal,time\n"
            "from pathlib import Path\n"
            "pid_file = Path(os.environ['MCP_FIXTURE_PID'])\n"
            "pid_file.write_text(str(os.getpid()))\n"
            "def stop(signum, frame):\n"
            "    pid_file.with_suffix('.stopped').touch()\n"
            "    raise SystemExit(0)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "while True: time.sleep(1)\n"
        )
        config = (f"[mcp_servers.fixture]\ncommand = {json.dumps(sys.executable)}\n"
                  f"args = [{json.dumps(str(fixture))}]\n")
        (folder / "config.toml").write_text(config)
        (folder / "threads.json").write_text(json.dumps({
            "primary": {"id": "primary", "parentThreadId": None, "status": {"type": "active"}},
        }))
        server_file = folder / "server.py"
        server_file.write_text(SERVER)
        owned = subprocess.Popen(
            [sys.executable, str(fixture)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            env={**os.environ, "MCP_FIXTURE_PID": str(folder / "owned.pid")},
        )
        launcher = ("import subprocess,sys; child = subprocess.Popen(sys.argv[1:], "
                    "stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, "
                    "start_new_session=True); "
                    "print(child.pid)")
        orphan_pid = None
        with (folder / "server.log").open("w") as log:
            server = subprocess.Popen(
                [uv, "run", "--script", str(server_file), str(folder)],
                stdout=log, stderr=log, start_new_session=True,
            )
            try:
                launched = subprocess.run(
                    [sys.executable, "-c", launcher, sys.executable, str(fixture)],
                    check=True, timeout=5, capture_output=True, text=True,
                    env={**os.environ, "MCP_FIXTURE_PID": str(folder / "orphan.pid")},
                )
                orphan_pid = int(launched.stdout)
                deadline = time.monotonic() + 30
                while not all((folder / file).exists()
                              for file in ["ready", "owned.pid", "orphan.pid"]):
                    if server.poll() is not None or time.monotonic() >= deadline:
                        raise AssertionError((folder / "server.log").read_text())
                    time.sleep(0.02)
                command = [uv, "run", "--script", str(ROOT / "bin/codex-cleanup"),
                           "--socket", str(folder / "daemon.sock"),
                           "--worktree-root", str(folder),
                           "--min-idle-minutes", "0", "--json"]
                script_env = {**os.environ, "CODEX_HOME": str(folder)}
                preview = subprocess.run(command, capture_output=True, text=True,
                                         timeout=30, env=script_env)
                assert preview.returncode == 0, preview.stderr
                plan = json.loads(preview.stdout)
                assert {row["pid"] for row in plan["mcp_processes"]
                        if row["action"] == "candidate"} == {orphan_pid}
                assert next(row for row in plan["mcp_processes"]
                            if row["pid"] == owned.pid)["reason"] == "live client parent"
                assert not (folder / "orphan.stopped").exists()
                applied = subprocess.run(command + ["--apply"], capture_output=True,
                                         text=True, timeout=30, env=script_env)
                assert applied.returncode == 0, applied.stderr
                result = json.loads(applied.stdout)
                assert result["mcp_summary"]["terminated"] == 1
                assert next(row for row in result["mcp_processes"]
                            if row["pid"] == orphan_pid)["action"] == "terminated"
                assert (folder / "orphan.stopped").exists()
                assert owned.poll() is None
                assert (folder / "config.toml").read_text() == config
                assert result["threads"][0]["action"] == "retained"
            finally:
                owned.terminate()
                owned.wait(timeout=5)
                if orphan_pid is None and (folder / "orphan.pid").exists():
                    orphan_pid = int((folder / "orphan.pid").read_text())
                if orphan_pid and not (folder / "orphan.stopped").exists():
                    try:
                        os.kill(orphan_pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                try:
                    os.killpg(server.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                server.wait(timeout=5)


def test_worktree_audit_identifies_merged_unused_checkout_and_retains_agent_checkouts():
    uv = shutil.which("uv")
    assert uv, "uv is required to run the cleanup command"
    with tempfile.TemporaryDirectory(prefix="codex-worktrees-", dir="/tmp") as name:
        folder = Path(name).resolve()
        repo = folder / "project"
        repo.mkdir()
        git_env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}

        def git(directory, *args):
            return subprocess.check_output(
                ["git", "-c", "user.name=Cleanup fixture",
                 "-c", "user.email=cleanup@example.invalid", "-c", "commit.gpgsign=false",
                 "-C", str(directory), *args], env=git_env, text=True,
            ).strip()

        git(repo, "init", "-q", "--initial-branch", "main")
        (repo / ".gitignore").write_text(".worktrees/\n")
        git(repo, "add", ".gitignore")
        git(repo, "commit", "-qm", "Initialize fixture")
        merged = repo / ".worktrees/merged"
        git(repo, "worktree", "add", "-b", "merged-task", str(merged))
        (merged / "feature.txt").write_text("merged feature\n")
        git(merged, "add", "feature.txt")
        git(merged, "commit", "-qm", "Complete feature")
        git(repo, "merge", "--ff-only", "merged-task")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        active = repo / ".worktrees/codex-held"
        git(repo, "worktree", "add", "-b", "codex-task", str(active))
        (active / "src").mkdir()
        paseo_held = repo / ".worktrees/paseo-held"
        git(repo, "worktree", "add", "-b", "paseo-task", str(paseo_held))
        unmerged = repo / ".worktrees/unmerged"
        git(repo, "worktree", "add", "-b", "unfinished-task", str(unmerged))
        (unmerged / "future.txt").write_text("unmerged feature\n")
        git(unmerged, "add", "future.txt")
        git(unmerged, "commit", "-qm", "Unmerged work")
        wrappers = folder / "wrappers"
        wrappers.mkdir()
        paseo = wrappers / "paseo"
        paseo.write_text(
            "#!" + sys.executable + "\nprint(" + repr(json.dumps([
                {"id": "paseo-fixture", "cwd": str(paseo_held), "status": "running"},
            ])) + ")\n"
        )
        paseo.chmod(0o755)
        (folder / "threads.json").write_text(json.dumps({
            "primary": {"id": "primary", "parentThreadId": None,
                        "status": {"type": "active"}, "cwd": str(active / "src")},
        }))
        server_file = folder / "server.py"
        server_file.write_text(SERVER)
        with (folder / "server.log").open("w") as log:
            server = subprocess.Popen(
                [uv, "run", "--script", str(server_file), str(folder)],
                stdout=log, stderr=log, start_new_session=True,
            )
            try:
                deadline = time.monotonic() + 30
                while not (folder / "ready").exists():
                    if server.poll() is not None or time.monotonic() >= deadline:
                        raise AssertionError((folder / "server.log").read_text())
                    time.sleep(0.02)
                command = [uv, "run", "--script", str(ROOT / "bin/codex-cleanup"),
                           "--socket", str(folder / "daemon.sock"),
                           "--worktree-root", str(repo), "--worktree-age-hours", "0", "--json"]
                script_env = {
                    **git_env, "CODEX_HOME": str(folder),
                    "PATH": str(wrappers) + os.pathsep + os.environ["PATH"],
                    "XDG_CACHE_HOME": str(folder / "cache"),
                    "UV_CACHE_DIR": subprocess.check_output([uv, "cache", "dir"], text=True).strip(),
                }
                preview = subprocess.run(command, capture_output=True, text=True,
                                         timeout=30, env=script_env)
                assert preview.returncode == 0, preview.stderr + preview.stdout
                plan = json.loads(preview.stdout)
                rows = {row["path"]: row for row in plan["worktrees"]}
                assert rows[str(merged)]["action"] == "candidate"
                assert rows[str(merged)]["base"] == "origin/main"
                assert rows[str(active)]["action"] == "retained"
                assert rows[str(active)]["agent_references"][0]["source"] == "Codex"
                assert rows[str(paseo_held)]["action"] == "retained"
                assert rows[str(paseo_held)]["agent_references"][0]["source"] == "Paseo"
                assert rows[str(unmerged)]["action"] == "retained"
                assert rows[str(unmerged)]["reason"] == "not merged"
                assert plan["worktree_repositories_checked"] == 1
                applied = subprocess.run(command + ["--apply"], capture_output=True,
                                         text=True, timeout=30, env=script_env)
                assert applied.returncode == 0, applied.stderr + applied.stdout
                assert json.loads(applied.stdout)["worktree_summary"]["candidate"] == 1
                assert merged.is_dir() and active.is_dir() and paseo_held.is_dir()
                assert (unmerged / "future.txt").read_text() == "unmerged feature\n"
                assert git(repo, "show-ref", "--verify", "refs/heads/merged-task")
            finally:
                try:
                    os.killpg(server.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                server.wait(timeout=5)
