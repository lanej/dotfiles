import gzip
import http.client
import http.server
import json
import threading
import unittest

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
                cls.seen.append({
                    "body": body, "auth": self.headers.get("Authorization"),
                    "path": self.path, "encoding": self.headers.get("Content-Encoding"),
                })
                if self.headers.get("X-Test-Region-Error"):
                    data = json.loads(body)
                    if any(x.get("encrypted_content") for x in data.get("input", [])):
                        error = json.dumps({"error": {
                            "code": "validation_error",
                            "message": "Encrypted content cannot be used in a different region from the one that created it.",
                            "type": "invalid_request_error",
                        }}).encode()
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

        cls.upstream = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        threading.Thread(target=cls.upstream.serve_forever, daemon=True).start()
        cls.regions = []

        def connect(region):
            cls.regions.append(region)
            return http.client.HTTPConnection("127.0.0.1", cls.upstream.server_port, timeout=5)

        cls.router = RouterServer(("127.0.0.1", 0), connect)
        threading.Thread(target=cls.router.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.release_stream.set()
        cls.router.shutdown()
        cls.router.server_close()
        cls.upstream.shutdown()
        cls.upstream.server_close()

    def request(self, model, compress=False, chunked=False):
        body = json.dumps({"model": model, "input": "test"}).encode()
        headers = {"Authorization": "Bearer test-only", "Content-Type": "application/json"}
        if compress:
            body = gzip.compress(body)
            headers["Content-Encoding"] = "gzip"
        conn = http.client.HTTPConnection("127.0.0.1", self.router.server_port, timeout=5)
        conn.request("POST", "/openai/v1/responses",
                     iter([body[:5], body[5:]]) if chunked else body,
                     headers=headers, encode_chunked=chunked)
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn(b"[DONE]", response.read())
        conn.close()
        self.assertEqual(self.seen[-1]["body"], body)
        self.assertEqual(self.seen[-1]["auth"], "Bearer test-only")

    def test_exact_model_routes_east_and_other_models_west(self):
        for model, region in [
            ("openai.gpt-6.1-sol", "us-east-1"),
            ("openai.gpt-6-astra", "us-west-2"),
            ("openai.gpt-6-sol", "us-west-2"),
            ("openai.gpt-6.1-sol-other", "us-west-2"),
        ]:
            with self.subTest(model=model):
                self.request(model)
                self.assertEqual(self.regions[-1], region)

    def test_compressed_chunked_request_preserves_payload_and_auth(self):
        self.request("openai.gpt-6.1-sol", compress=True, chunked=True)
        self.assertEqual(self.regions[-1], "us-east-1")
        self.assertEqual(self.seen[-1]["encoding"], "gzip")

    def test_stream_is_forwarded_before_upstream_finishes(self):
        self.release_stream.clear()
        conn = http.client.HTTPConnection("127.0.0.1", self.router.server_port, timeout=2)
        conn.request("POST", "/openai/v1/responses",
                     json.dumps({"model": "openai.gpt-6-astra"}),
                     {"Authorization": "Bearer test-only", "X-Test-Stream": "1"})
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
            conn = http.client.HTTPConnection("127.0.0.1", self.router.server_port, timeout=2)
            conn.request("POST", path, b"{}", {"Authorization": auth})
            response = conn.getresponse()
            self.assertEqual(response.status, status)
            response.read()
            conn.close()
            self.assertEqual(len(self.regions), before)

    def test_region_error_retries_preserving_visible_history_and_tool_results(self):
        payload = {"model": "openai.gpt-6-astra", "input": [
            {"role": "user", "content": "Keep this task context."},
            {"type": "reasoning", "id": "rs_1", "encrypted_content": "foreign",
             "summary": [{"type": "summary_text", "text": "Retain this summary."}]},
            {"type": "function_call", "call_id": "call_1", "name": "echo",
             "arguments": "{\"message\":\"test\"}"},
            {"type": "function_call_output", "call_id": "call_1", "output": "test"},
        ]}
        before = len(self.seen)
        conn = http.client.HTTPConnection("127.0.0.1", self.router.server_port, timeout=5)
        conn.request("POST", "/openai/v1/responses", json.dumps(payload),
                     {"Authorization": "Bearer test-only", "X-Test-Region-Error": "1"})
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn(b"[DONE]", response.read())
        conn.close()
        self.assertEqual(len(self.seen) - before, 2)
        self.assertEqual(json.loads(self.seen[-2]["body"]), payload)
        del payload["input"][1]["encrypted_content"]
        self.assertEqual(json.loads(self.seen[-1]["body"]), payload)
        self.assertEqual(self.seen[-1]["auth"], "Bearer test-only")

    def test_encrypted_compaction_is_never_removed_or_retried(self):
        payload = {"model": "openai.gpt-6-astra", "input": [
            {"type": "reasoning", "encrypted_content": "foreign", "summary": []},
            {"type": "compaction", "encrypted_content": "task-context"},
        ]}
        before = len(self.seen)
        conn = http.client.HTTPConnection("127.0.0.1", self.router.server_port, timeout=5)
        conn.request("POST", "/openai/v1/responses", json.dumps(payload),
                     {"Authorization": "Bearer test-only", "X-Test-Region-Error": "1"})
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertIn(b"Encrypted content", response.read())
        conn.close()
        self.assertEqual(len(self.seen) - before, 1)
        self.assertEqual(json.loads(self.seen[-1]["body"]), payload)


if __name__ == "__main__":
    unittest.main()
