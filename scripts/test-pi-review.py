#!/usr/bin/env python3
"""One review workflow through dispatcher-worker and pi-review.

Use --native to exercise Pi 1.4.0 against a local fixture model. Without it,
only the external Pi process is simulated; no live model credentials are used.
"""

import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parent.parent
REVIEW = {"verdict": "changes_requested", "review": "## Code Review Summary\n"
          "price.py subtracts the fee. The total must add it. Verification was not run."}


def fake_pi():
    if "--version" in sys.argv:
        print("1.4.0")
        return
    def option(name):
        return sys.argv[sys.argv.index(name) + 1]
    assert set(option("--tools").split(",")) == {"read", "grep", "find", "ls"}
    assert {"--no-extensions", "--no-mcp", "--no-skills", "--no-prompt-templates",
            "--no-context-files", "--no-approve"} <= set(sys.argv)
    assert "PHA-P03" in Path(option("--append-system-prompt")).read_text()
    session_id = option("--session-id")
    session_file = Path(option("--session-dir")) / (session_id + ".jsonl")
    session_file.parent.mkdir(parents=True)
    session_file.write_text('{"type":"session"}\n')
    def emit(event):
        print(json.dumps(event), flush=True)
    for line in sys.stdin.buffer:
        request = json.loads(line)
        if request["type"] == "get_state":
            emit({"type": "response", "id": request["id"], "success": True, "data": {
                "sessionId": session_id, "sessionFile": str(session_file),
                "model": {"provider": "review-fixture", "id": "tiny"}}})
        elif request["type"] == "prompt":
            assert "return amount - fee" in request["message"]
            emit({"type": "response", "id": request["id"], "success": True,
                  "data": {"disposition": "started"}})
            # A recoverable failed run must not be mistaken for a finished review.
            emit({"type": "message_end", "message": {"role": "assistant",
                  "stopReason": "error", "content": []}})
            emit({"type": "agent_end", "willRetry": True})
            time.sleep(0.02)
            emit({"type": "tool_execution_start", "toolName": "read"})
            assert "return amount - fee" in Path("price.py").read_text()
            emit({"type": "message_end", "message": {"role": "assistant", "stopReason": "stop",
                  "content": [{"type": "text", "text": json.dumps(REVIEW)}]}})
            emit({"type": "agent_end", "willRetry": False})
            emit({"type": "agent_settled", "aborted": False})


class FixtureModel(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(payload)
        tools = {tool["function"]["name"] for tool in payload.get("tools", [])}
        if tools != {"read", "grep", "find", "ls"}:
            self.server.failures.append(f"Unexpected exposed tools: {tools}")
        messages = payload["messages"]
        serialized = json.dumps(messages)
        if "PHA-P03" not in serialized or "code review" not in serialized.lower():
            self.server.failures.append("Shared reviewer/Builder instructions missing")
        if len(self.server.requests) == 1:
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"fixture retry","type":"server_error"}}')
            return
        if any(message.get("role") == "tool" for message in messages):
            if "return amount - fee" not in serialized:
                self.server.failures.append("Reviewed source never reached the model")
            delta = {"content": json.dumps(REVIEW)}
            finish = "stop"
        else:
            delta = {"tool_calls": [{"index": 0, "id": "review-read", "type": "function",
                     "function": {"name": "read", "arguments": '{"path":"price.py"}'}}]}
            finish = "tool_calls"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for part, reason in (({"role": "assistant", **delta}, None), ({}, finish)):
            chunk = {"id": "fixture", "object": "chat.completion.chunk", "created": 0,
                     "model": "tiny", "choices": [{"index": 0, "delta": part, "finish_reason": reason}]}
            self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


class ReviewWorkflow(unittest.TestCase):
    def test_dispatcher_review_keeps_finish_with_the_caller(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            repo = directory / "repo"
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
            git("init", "-q")
            git("config", "user.name", "Review Fixture")
            git("config", "user.email", "review@example.invalid")
            (repo / "price.py").write_text("def total(amount, fee):\n    return amount + fee\n")
            (repo / ".pi/extensions").mkdir(parents=True)
            marker = directory / "extension-executed"
            (repo / ".pi/extensions/unwanted.ts").write_text(
                "import {writeFileSync} from 'node:fs';\nexport default function () {"
                f"writeFileSync({json.dumps(str(marker))}, 'unexpected');" + "}\n")
            git("add", ".")
            git("commit", "-qm", "Base")
            git("update-ref", "refs/remotes/origin/main", "HEAD")
            (repo / "price.py").write_text("def total(amount, fee):\n    return amount - fee\n")
            git("add", ".")
            git("commit", "-qm", "Introduce fee regression")
            head = git("rev-parse", "HEAD")

            task_home = directory / "home"
            state = task_home / ".local/state/dispatcher/repo"
            state.mkdir(parents=True)
            (state / "builder1.json").write_text(json.dumps({"repo": str(repo), "slug": "review"}))
            config = directory / "dispatcher.json"
            config.write_text('{"targetBranch":"main"}')
            executables = directory / "bin"
            executables.mkdir()
            (executables / "python3").symlink_to(sys.executable)
            claude = executables / "claude"
            claude.write_text(f"#!{sys.executable}\nimport json\nprint(json.dumps(["
                              f"{{'id':'builder1','cwd':{str(repo)!r}}}]))\n")
            claude.chmod(0o755)
            env = dict(os.environ, HOME=str(task_home),
                       PATH=f"{executables}:{os.environ['PATH']}",
                       DISPATCHER_CONFIG=str(config), DISPATCHER_PI_REVIEW=str(ROOT / "bin/pi-review"),
                       PI_SKIP_VERSION_CHECK="1", PI_TELEMETRY="0")
            server = None
            if NATIVE:
                pi = shutil.which("pi")
                self.assertIsNotNone(pi, "Install Pi 1.4.0 before running --native")
                server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixtureModel)
                server.requests = []
                server.failures = []
                threading.Thread(target=server.serve_forever, daemon=True).start()
                agent_dir = directory / "pi-agent"
                agent_dir.mkdir()
                (agent_dir / "models.json").write_text(json.dumps({"providers": {"review-fixture": {
                    "baseUrl": f"http://127.0.0.1:{server.server_port}/v1", "api": "openai-completions",
                    "apiKey": "fixture", "models": [{"id": "tiny"}]}}}))
                env["PI_CODING_AGENT_DIR"] = str(agent_dir)
            else:
                pi = executables / "pi"
                pi.write_text(f"#!{sys.executable}\nimport runpy, sys\nsys.argv.insert(1, '--fixture-pi')\n"
                              f"runpy.run_path({str(Path(__file__).resolve())!r}, run_name='__main__')\n")
                pi.chmod(0o755)
            output = directory / "review-result"
            try:
                result = subprocess.run(
                    ["bash", str(ROOT / "ai/skills/dispatcher/scripts/dispatcher-worker"),
                     "review-pi", "builder1", "--model", "review-fixture/tiny", "--timeout", "45",
                     "--pi-bin", str(pi), "--output-dir", str(output)],
                    cwd=repo, env=env, capture_output=True, text=True, timeout=55,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr +
                                 ((output / "stderr.log").read_text() if (output / "stderr.log").exists() else ""))
                record = json.loads(result.stdout)
                self.assertEqual(record["status"], "reviewed")
                self.assertEqual(record["verdict"], "changes_requested")
                self.assertEqual(record["cwd"], str(repo.resolve()))
                self.assertEqual(record["head"], head)
                self.assertEqual(record["model"], {"provider": "review-fixture", "id": "tiny"})
                self.assertTrue(Path(record["sessionFile"]).is_file())
                self.assertEqual((output / "review.md").read_text().strip(), REVIEW["review"])
                self.assertEqual(json.loads((output / "result.json").read_text()), record)
                self.assertFalse(marker.exists(), "Project extension ran during a restricted review")
                self.assertEqual(git("rev-parse", "HEAD"), head)
                self.assertEqual(git("status", "--porcelain"), "")
                self.assertTrue((state / "builder1.json").exists(), "Review consumed the builder's state")
                if server:
                    self.assertFalse(server.failures, server.failures)
                    self.assertGreaterEqual(len(server.requests), 3)
            finally:
                if server:
                    server.shutdown()
                    server.server_close()


if __name__ == "__main__":
    if "--fixture-pi" in sys.argv:
        fake_pi()
    else:
        NATIVE = "--native" in sys.argv
        if NATIVE:
            sys.argv.remove("--native")
        print("Review workflow boundary: " + ("native Pi, fixture model" if NATIVE else "simulated Pi RPC"))
        unittest.main()
