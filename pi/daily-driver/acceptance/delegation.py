"""Run the managed driver through Pi RPC and a deterministic loopback provider."""
import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Event, Thread
from queue import Queue

parser = argparse.ArgumentParser()
scenario = parser.add_mutually_exclusive_group()
scenario.add_argument("--lost-allocation", action="store_true")
scenario.add_argument("--cancel", action="store_true")
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"


@contextmanager
def provider():
    requests = []
    child_started = Event()
    release_child = Event()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            model = request["model"]
            if model == "explorer" and args.cancel:
                child_started.set()
                release_child.wait(25)
            tools = {item["function"]["name"] for item in request.get("tools", [])}
            had_result = any(message["role"] == "tool" for message in request["messages"])
            call = None
            if model == "lead" and not had_result:
                call = ("driver_delegate", {"role": "explorer", "brief": "Read fixture.txt"})
            elif model == "explorer" and not had_result:
                call = ("read", {"path": "fixture.txt"})
            delta = {"role": "assistant"}
            if call is not None and call[0] in tools:
                delta["tool_calls"] = [{"index": 0, "id": "call_" + model, "type": "function",
                                        "function": {"name": call[0], "arguments": json.dumps(call[1])}}]
                finish = "tool_calls"
            else:
                delta["content"] = "finished"
                finish = "stop"
            chunk = {"id": "fixture", "object": "chat.completion.chunk", "created": 1, "model": model,
                     "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
            data = ("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                if not args.cancel:
                    raise

        def log_message(self, *_args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield server.server_port, requests, child_started
        finally:
            release_child.set()
            server.shutdown()
            worker.join()


with tempfile.TemporaryDirectory(prefix="pi-driver-delegation-") as temp, provider() as (port, requests, child_started):
    fixture = Path(temp).resolve()
    repo = fixture / "repo"
    repo.mkdir()
    agent = fixture / "agent"
    config = fixture / "config.json"
    env = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "PI_", "WORKTREE_"))}
    env.update(HOME=str(fixture), PI_CODING_AGENT_DIR=str(agent), PI_DRIVER_CONFIG=str(config),
               PI_TELEMETRY="0", PI_SKIP_VERSION_CHECK="1", XDG_STATE_HOME=str(fixture / "state"),
               XDG_CONFIG_HOME=str(fixture / "config"), XDG_CACHE_HOME=str(fixture / "cache"))

    if args.lost_allocation:
        manager = shutil.which("worktree")
        assert manager is not None
        tools_path = fixture / "bin"
        tools_path.mkdir()
        wrapper = tools_path / "worktree"
        wrapper.write_text(f"""#!/usr/bin/env python3
import subprocess
import sys
if sys.argv[1] == "create":
    subprocess.run([{manager!r}, *sys.argv[1:]], check=True, stdout=subprocess.DEVNULL)
    sys.exit(1)
sys.exit(subprocess.call([{manager!r}, *sys.argv[1:]]))
""")
        wrapper.chmod(0o755)
        env["PATH"] = str(tools_path) + os.pathsep + env["PATH"]

    def run(*argv):
        return subprocess.check_output(argv, env=env, cwd=repo, text=True, timeout=30).strip()

    run("git", "init", "-q")
    (repo / ".gitignore").write_text(".worktrees/\n")
    (repo / "fixture.txt").write_text("committed fixture evidence\n")
    (repo / "outside").symlink_to(fixture / "outside.txt")
    (fixture / "outside.txt").write_text("outside fixture\n")
    run("git", "add", ".")
    run("git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Fixture")
    source = run("git", "rev-parse", "HEAD")
    (repo / "fixture.txt").write_text("uncommitted change\n")
    run("python3", str(ROOT / "../../scripts/configure-pi-driver.py"), str(ROOT), str(agent))
    models = [{"id": role, "reasoning": True} for role in ("lead", "worker", "reviewer", "explorer")]
    (agent / "models.json").write_text(json.dumps({"providers": {"openai-codex": {
        "baseUrl": f"http://127.0.0.1:{port}/v1", "api": "openai-completions",
        "apiKey": "fixture", "models": models,
    }}}))
    config.write_text(json.dumps({"delegation": {"enabled": True}, "profiles": {"personal": {
        role: {"provider": "openai-codex", "model": role, "reasoning": effort}
        for role, effort in (("lead", "high"), ("worker", "medium"), ("reviewer", "medium"), ("explorer", "low"))
    }}}))
    proc = subprocess.Popen(["node", str(CLI), "--mode", "rpc", "--offline", "--no-mcp",
                             "--model", "openai-codex/lead"], env=env, cwd=repo,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    events = []
    # Consume stdout in a thread so the test can bound both phases and print native evidence on failure.
    output = Queue()
    def read_output():
        for line in proc.stdout:
            output.put(line)

    reader = Thread(target=read_output, daemon=True)
    reader.start()

    def send(id, message):
        proc.stdin.write(json.dumps({"id": id, "type": "prompt", "message": message}) + "\n")
        proc.stdin.flush()

    def wait_for(predicate):
        while True:
            event = json.loads(output.get(timeout=25))
            events.append(event)
            if predicate(event):
                return event

    try:
        send("profile", "/driver-profile personal")
        assert wait_for(lambda event: event.get("id") == "profile")["success"]
        send("lead", "Delegate repository inspection")
        assert wait_for(lambda event: event.get("id") == "lead")["success"]
        if args.cancel:
            assert child_started.wait(20)
            proc.stdin.write('{"id":"cancel","type":"abort"}\n')
            proc.stdin.flush()
            assert wait_for(lambda event: event.get("id") == "cancel")["success"]
        else:
            wait_for(lambda event: event.get("type") == "agent_settled")
        rows = list((fixture / "state/pi-driver/attempts").glob("*.json"))
        assert len(rows) == 1, events[-12:]
        attempt = json.loads(rows[0].read_text())
        expected_state = "uncertain" if args.lost_allocation else "cancelled" if args.cancel else "complete"
        assert attempt["state"] == expected_state, (attempt, events[-12:])
        lead_tools = {tool["function"]["name"] for tool in requests[0]["tools"]}
        assert not lead_tools.intersection({"Agent", "SubagentWorkflow", "subagent"})
        assert attempt["role"] == "explorer" and attempt["reasoning"] == "low"
        assert attempt["source"] == source
        checkout = Path(attempt["worktree"]["path"])
        assert checkout.parent == repo / ".worktrees" and attempt["worktree"]["owner_id"] == attempt["id"]
        assert (checkout / "fixture.txt").read_text() == "committed fixture evidence\n"
        if args.lost_allocation:
            assert len(list((repo / ".worktrees").iterdir())) == 1
            assert all(request["model"] == "lead" for request in requests)
            print("Lost worktree response recovered by owner. One checkout, zero child launches.")
        elif args.cancel:
            assert attempt["session"] and attempt["sessionFile"]
            print("Native Pi abort settled the child and retained its session locator.")
        else:
            transcript = Path(attempt["sessionFile"]).read_text()
            child_requests = [request for request in requests if request["model"] == "explorer"]
            assert len(child_requests) == 2
            assert {tool["function"]["name"] for tool in child_requests[0]["tools"]} == {"read", "ls", "find", "grep"}
            assert "committed fixture evidence" in transcript and "uncommitted change" not in transcript
            print("Native Pi delegation, exact worktree and snapshot tools verified.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        if proc.stderr is not None:
            stderr = proc.stderr.read()
            if stderr:
                print(stderr)
