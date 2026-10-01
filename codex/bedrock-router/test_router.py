import gzip
import http.client
import http.server
import json
import tempfile
import threading
import unittest
from pathlib import Path

from router import RouterServer


class RouterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seen = []
        cls.release_stream = threading.Event()

        class Upstream(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                cls.seen.append(
                    {
                        "body": body,
                        "auth": self.headers.get("Authorization"),
                        "path": self.path,
                        "encoding": self.headers.get("Content-Encoding"),
                        "region": self.server.region,
                    }
                )
                if self.headers.get("X-Test-Region-Error"):
                    data = json.loads(body)
                    origin = self.headers.get("X-Test-Context-Region", "us-east-1")
                    if self.server.region != origin and any(
                        x.get("encrypted_content") for x in data.get("input", [])
                    ):
                        error = json.dumps(
                            {
                                "error": {
                                    "code": "validation_error",
                                    "message": "Encrypted content cannot be used in a different region from the one that created it.",
                                    "type": "invalid_request_error",
                                }
                            }
                        ).encode()
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(error)))
                        self.end_headers()
                        self.wfile.write(error)
                        return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(b"data: first\n\n")
                self.wfile.flush()
                if self.headers.get("X-Test-Stream"):
                    cls.release_stream.wait(5)
                self.wfile.write(b"data: [DONE]\n\n")

        cls.upstreams = {}
        for region in ("us-west-2", "us-east-1"):
            upstream = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
            upstream.region = region
            cls.upstreams[region] = upstream
            threading.Thread(target=upstream.serve_forever, daemon=True).start()
        cls.regions = []
        cls.state_dir = tempfile.TemporaryDirectory()
        cls.state_file = Path(cls.state_dir.name) / "sessions.sqlite3"

        def connect(region):
            cls.regions.append(region)
            return http.client.HTTPConnection(
                "127.0.0.1", cls.upstreams[region].server_port, timeout=5
            )

        cls.connect = staticmethod(connect)
        cls.start_router()

    @classmethod
    def start_router(cls):
        cls.router = RouterServer(
            ("127.0.0.1", 0), cls.connect, state_file=cls.state_file
        )
        threading.Thread(target=cls.router.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.release_stream.set()
        cls.router.shutdown()
        cls.router.server_close()
        for upstream in cls.upstreams.values():
            upstream.shutdown()
            upstream.server_close()
        cls.state_dir.cleanup()

    def request(self, model, compress=False, chunked=False, headers=None, timeout=5):
        body = json.dumps({"model": model, "input": "test"}).encode()
        headers = {
            "Authorization": "Bearer test-only",
            "Content-Type": "application/json",
            **(headers or {}),
        }
        if compress:
            body = gzip.compress(body)
            headers["Content-Encoding"] = "gzip"
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.router.server_port, timeout=timeout
        )
        conn.request(
            "POST",
            "/openai/v1/responses",
            iter([body[:5], body[5:]]) if chunked else body,
            headers=headers,
            encode_chunked=chunked,
        )
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn(b"[DONE]", response.read())
        conn.close()
        self.assertEqual(self.seen[-1]["body"], body)
        self.assertEqual(self.seen[-1]["auth"], "Bearer test-only")

    def test_session_region_survives_model_change_fork_and_restart(self):
        west = {"thread-id": "west-session"}
        east = {"thread-id": "east-session"}
        self.request("openai.gpt-6-astra", headers=west)
        self.assertEqual(self.regions[-1], "us-west-2")

        before = len(self.seen)
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.router.server_port, timeout=5
        )
        conn.request(
            "POST",
            "/openai/v1/responses",
            json.dumps({"model": "openai.gpt-6.1-sol", "input": "test"}),
            {"Authorization": "Bearer test-only", **west},
        )
        response = conn.getresponse()
        self.assertEqual(response.status, 409)
        self.assertIn(b"Start a new session", response.read())
        conn.close()
        self.assertEqual(len(self.seen), before)

        self.release_stream.clear()
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.router.server_port, timeout=2
        )
        conn.request(
            "POST",
            "/openai/v1/responses",
            json.dumps({"model": "openai.gpt-6.1-sol", "input": "test"}),
            {"Authorization": "Bearer test-only", "X-Test-Stream": "1", **east},
        )
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(13), b"data: first\n\n")
        self.assertEqual(self.regions[-1], "us-east-1")
        try:
            self.request(
                "openai.gpt-5.6-luna",
                headers={
                    "thread-id": "guardian-during-stream",
                    "x-codex-parent-thread-id": "east-session",
                },
                timeout=2,
            )
            self.assertEqual(self.regions[-1], "us-east-1")
        finally:
            self.release_stream.set()
            response.read()
            conn.close()
        self.request("openai.gpt-6-astra", headers=east)
        self.assertEqual(self.regions[-1], "us-east-1")

        self.router.shutdown()
        self.router.server_close()
        type(self).start_router()
        self.request("openai.gpt-6-astra", headers=east)
        self.assertEqual(self.regions[-1], "us-east-1")
        self.request(
            "openai.gpt-5.6-luna",
            headers={
                "thread-id": "guardian-session",
                "x-codex-turn-metadata": json.dumps(
                    {"parent_thread_id": "east-session"}
                ),
            },
        )
        self.assertEqual(self.regions[-1], "us-east-1")
        self.request("openai.gpt-6-astra", headers=west)
        self.assertEqual(self.regions[-1], "us-west-2")

    def test_compressed_chunked_request_preserves_payload_and_auth(self):
        self.request("openai.gpt-6.1-sol", compress=True, chunked=True)
        self.assertEqual(self.regions[-1], "us-east-1")
        self.assertEqual(self.seen[-1]["encoding"], "gzip")

    def test_stream_is_forwarded_before_upstream_finishes(self):
        self.release_stream.clear()
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.router.server_port, timeout=2
        )
        conn.request(
            "POST",
            "/openai/v1/responses",
            json.dumps({"model": "openai.gpt-6-astra"}),
            {"Authorization": "Bearer test-only", "X-Test-Stream": "1"},
        )
        response = conn.getresponse()
        try:
            self.assertEqual(response.read(13), b"data: first\n\n")
        finally:
            self.release_stream.set()
        self.assertIn(b"[DONE]", response.read())
        conn.close()

    def test_missing_auth_and_invalid_paths_never_reach_upstream(self):
        for path, auth, status in [
            ("/openai/v1/responses", "", 401),
            ("https://example.com/openai/v1/responses", "Bearer test-only", 404),
            ("/unrelated", "Bearer test-only", 404),
        ]:
            before = len(self.regions)
            conn = http.client.HTTPConnection(
                "127.0.0.1", self.router.server_port, timeout=2
            )
            conn.request("POST", path, b"{}", {"Authorization": auth})
            response = conn.getresponse()
            self.assertEqual(response.status, status)
            response.read()
            conn.close()
            self.assertEqual(len(self.regions), before)

    def test_old_session_recovers_its_region_with_encrypted_context_intact(self):
        self.request(
            "openai.gpt-6.1-sol", headers={"thread-id": "old-session-parent"}
        )
        payload = {
            "model": "openai.gpt-5.6-luna",
            "input": [
                {"role": "user", "content": "Keep this task context."},
                {
                    "type": "reasoning",
                    "id": "rs_1",
                    "encrypted_content": "foreign",
                    "summary": [
                        {"type": "summary_text", "text": "Retain this summary."}
                    ],
                },
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "echo",
                    "arguments": '{"message":"test"}',
                },
                {"type": "function_call_output", "call_id": "call_1", "output": "test"},
                {"type": "compaction", "encrypted_content": "task-context"},
            ],
        }
        before = len(self.seen)
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.router.server_port, timeout=5
        )
        conn.request(
            "POST",
            "/openai/v1/responses",
            json.dumps(payload),
            {
                "Authorization": "Bearer test-only",
                "X-Test-Region-Error": "1",
                "X-Test-Context-Region": "us-west-2",
                "thread-id": "old-session",
                "x-codex-parent-thread-id": "old-session-parent",
            },
        )
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn(b"[DONE]", response.read())
        conn.close()
        self.assertEqual(len(self.seen) - before, 2)
        self.assertEqual(json.loads(self.seen[-2]["body"]), payload)
        self.assertEqual(json.loads(self.seen[-1]["body"]), payload)
        self.assertEqual(self.seen[-2]["region"], "us-east-1")
        self.assertEqual(self.seen[-1]["region"], "us-west-2")
        self.assertEqual(self.seen[-1]["auth"], "Bearer test-only")
        before = len(self.seen)
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.router.server_port, timeout=5
        )
        conn.request(
            "POST",
            "/openai/v1/responses",
            json.dumps(payload),
            {
                "Authorization": "Bearer test-only",
                "X-Test-Region-Error": "1",
                "X-Test-Context-Region": "us-west-2",
                "thread-id": "old-session",
                "x-codex-parent-thread-id": "old-session-parent",
            },
        )
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn(b"[DONE]", response.read())
        conn.close()
        self.assertEqual(len(self.seen) - before, 1)
        self.assertEqual(json.loads(self.seen[-1]["body"]), payload)
        self.assertEqual(self.seen[-1]["region"], "us-west-2")


if __name__ == "__main__":
    unittest.main()
