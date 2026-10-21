"""Exercise report and cleanup through the CLI and a real Unix WebSocket."""

import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import tempfile
import time


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
loaded = ["primary", "protected", "finished", "resuming", "queued", "subtree", "blocked", "stale"]
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
                if thread_id == "resuming" and reads[thread_id] >= 2:
                    threads[thread_id]["status"] = {"type": "active", "activeFlags": []}
                result = {"thread": threads[thread_id]}
            elif method == "thread/list":
                child = threads["unloaded-child"]
                visible = (
                    params.get("ancestorThreadId") == child["parentThreadId"]
                    and "subAgentThreadSpawn" in params.get("sourceKinds", [])
                    and params.get("archived") is not True
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
            elif method == "thread/archive":
                # The fake daemon independently rejects unsafe effects.
                if thread_id != "finished":
                    raise AssertionError("cleanup attempted to archive live or pending work")
                original = Path(threads[thread_id]["path"])
                original.rename(folder / "archived" / original.name)
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


def test_reports_then_retires_only_finished_helpers():
    uv = shutil.which("uv")
    assert uv, "uv is required to run the self-contained cleanup command"
    # Keep Unix socket paths below macOS's length limit.
    with tempfile.TemporaryDirectory(prefix="codex-cleanup-", dir="/tmp") as name:
        folder = Path(name)
        (folder / "archived").mkdir()
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
            "unloaded-parent": {"parentThreadId": None, "status": {"type": "notLoaded"}},
        }
        for thread_id, thread in threads.items():
            transcript = folder / f"{thread_id}.jsonl"
            transcript.write_text(f"saved conversation for {thread_id}\n")
            thread.update(id=thread_id, path=str(transcript), ephemeral=False,
                          agentRole="reviewer" if thread["parentThreadId"] else None,
                          cwd="/project", completed=completed)
        archived = folder / "archived_sessions/stale.jsonl"
        Path(threads["stale"]["path"]).rename(archived)
        threads["stale"]["path"] = str(archived)
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
                           "--socket", str(folder / "daemon.sock"), "--json"]
                preview = subprocess.run(command + ["--color", "always"],
                                         capture_output=True, text=True, timeout=30)
                assert preview.returncode == 0, preview.stderr
                plan = json.loads(preview.stdout)
                assert {r["id"] for r in plan["threads"] if r["action"] == "candidate"} == {
                    "finished", "resuming",
                }
                human = subprocess.run(
                    command[:-1] + ["--color", "always"], capture_output=True, text=True,
                    timeout=30, env={**os.environ, "COLUMNS": "160"},
                )
                assert human.returncode == 0, human.stderr
                assert "\033[36mretained" in human.stdout
                assert "\033[33mcandidate" in human.stdout
                lines = re.sub(r"\033\[[0-9;]*m", "", human.stdout).splitlines()
                header = next(line for line in lines if line.startswith("ACTION"))
                primary = next(line for line in lines
                               if line.split()[:2] == ["retained", "primary"])
                finished = next(line for line in lines
                                if line.split()[:2] == ["candidate", "finished"])
                assert primary.index("primary") == finished.index("finished") == header.index("THREAD")
                assert primary.index("primary", header.index("ROLE")) == header.index("ROLE")
                assert finished.index("reviewer") == header.index("ROLE")
                assert finished[header.index("REASON"):].startswith("eligible for archive")
                assert not any(c["method"] == "thread/archive"
                               for c in json.loads((folder / "calls.json").read_text()))
                applied = subprocess.run(command + ["--apply"], capture_output=True,
                                         text=True, timeout=30)
                assert applied.returncode == 0, applied.stderr
                result = json.loads(applied.stdout)
                assert {r["id"] for r in result["threads"] if r["action"] == "archived"} == {
                    "finished",
                }
                assert {r["id"] for r in result["threads"] if r["action"] == "retained"} == {
                    "primary", "protected", "resuming", "queued", "subtree", "blocked", "stale",
                }
                calls = json.loads((folder / "calls.json").read_text())
                assert [c["thread_id"] for c in calls if c["method"] == "thread/archive"] == [
                    "finished",
                ]
                assert (folder / "archived/finished.jsonl").read_text() == (
                    "saved conversation for finished\n"
                )
                assert (folder / "resuming.jsonl").exists()
                assert result["after"]["gauges"]["mcp.connections.live"] == 77
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
