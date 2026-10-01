#!/usr/bin/env python3
"""Route local Bedrock requests by model without storing credentials or prompts."""

import argparse
import collections
import gzip
import http.client
import http.server
import json
import threading
import urllib.parse

DEFAULT_REGION = "us-west-2"
MODEL_REGIONS = {"openai.gpt-6.1-sol": "us-east-1"}
HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
MAX_BODY_BYTES = 128 * 1024 * 1024


def region_for_model(model):
    return MODEL_REGIONS.get(model, DEFAULT_REGION)


def json_from_body(body, encoding):
    if encoding.lower() == "gzip":
        # Limit decompression independently of the encoded request size.
        import io

        with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
            body = stream.read(MAX_BODY_BYTES + 1)
        if len(body) > MAX_BODY_BYTES:
            raise ValueError("Request body exceeds the router limit")
    elif encoding and encoding.lower() != "identity":
        raise ValueError("Unsupported request content encoding")
    if not body:
        return {}
    value = json.loads(body)
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object")
    return value


def model_from_body(body, encoding):
    value = json_from_body(body, encoding)
    model = value.get("model")
    if model is not None and not isinstance(model, str):
        raise ValueError("Expected a string model")
    return model


def without_encrypted_reasoning(body, encoding):
    """Retain replayable history; never try to remove encrypted compaction."""
    payload = json_from_body(body, encoding)
    items = payload.get("input")
    if not isinstance(items, list):
        return None

    def contains_encrypted(value):
        if isinstance(value, dict):
            return bool(value.get("encrypted_content")) or any(
                contains_encrypted(x) for x in value.values()
            )
        if isinstance(value, list):
            return any(contains_encrypted(x) for x in value)
        return False

    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "compaction":
            return None
        if item.get("type") != "reasoning" and contains_encrypted(item):
            return None

    removed = 0
    for item in items:
        if (
            isinstance(item, dict)
            and item.get("type") == "reasoning"
            and item.pop("encrypted_content", None)
        ):
            removed += 1
    if not removed:
        return None
    clean = json.dumps(payload, separators=(",", ":")).encode()
    return gzip.compress(clean) if encoding.lower() == "gzip" else clean


def is_region_state_error(status, body):
    if status != 400:
        return False
    try:
        error = json.loads(body).get("error", {})
        return (
            error.get("code") == "validation_error"
            and "Encrypted content cannot be used in a different region"
            in error.get("message", "")
        )
    except (ValueError, AttributeError):
        return False


def upstream_connection(region):
    return http.client.HTTPSConnection(f"bedrock-mantle.{region}.api.aws", timeout=300)


class RouterServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, connection_factory=upstream_connection):
        super().__init__(address, RouterHandler)
        self.connection_factory = connection_factory
        self.route_counts = collections.Counter()
        self.count_lock = threading.Lock()

    def handle_error(self, request, client_address):
        # Avoid default traceback logging, which can contain request details.
        print("Bedrock router: local connection failed", flush=True)


class RouterHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "BedrockRegionalRouter"
    sys_version = ""

    def log_message(self, *_args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(300)

    def send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_GET(self):
        if self.path == "/healthz":
            with self.server.count_lock:
                counts = dict(self.server.route_counts)
            self.send_json(
                200,
                {
                    "status": "ok",
                    "default_region": DEFAULT_REGION,
                    "model_regions": MODEL_REGIONS,
                    "requests_by_region": counts,
                },
            )
            return
        self.proxy()

    def do_POST(self):
        self.proxy()

    def do_DELETE(self):
        self.proxy()

    def read_body(self):
        transfer_encoding = self.headers.get("Transfer-Encoding", "").lower()
        if transfer_encoding:
            if transfer_encoding != "chunked" or "Content-Length" in self.headers:
                raise ValueError("Invalid request framing")
            chunks, total = [], 0
            while True:
                line = self.rfile.readline(256)
                length = int(line.split(b";", 1)[0].strip(), 16)
                if length < 0:
                    raise ValueError("Invalid chunk length")
                if length == 0:
                    trailer_size = 0
                    while True:
                        trailer = self.rfile.readline(8192)
                        trailer_size += len(trailer)
                        if trailer in (b"\r\n", b"\n"):
                            return b"".join(chunks)
                        if not trailer or trailer_size > 65536:
                            raise ValueError("Invalid request trailer")
                total += length
                if total > MAX_BODY_BYTES:
                    raise ValueError("Request body exceeds the router limit")
                chunk = self.rfile.read(length)
                if len(chunk) != length or self.rfile.read(2) != b"\r\n":
                    raise ValueError("Invalid request chunk")
                chunks.append(chunk)
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 <= length <= MAX_BODY_BYTES:
            raise ValueError("Invalid request length")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValueError("Incomplete request body")
        return body

    def proxy(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith("/openai/v1/"):
            self.send_json(404, {"error": {"message": "Unknown router endpoint"}})
            return
        # Credentials are supplied by the app and passed directly to AWS.
        # The router never loads, saves, or logs the user's token.
        if not self.headers.get("Authorization", "").startswith("Bearer "):
            self.send_json(401, {"error": {"message": "Bearer token required"}})
            return
        try:
            body = self.read_body()
            model = model_from_body(body, self.headers.get("Content-Encoding", ""))
        except (ValueError, TypeError, OSError, EOFError):
            self.send_json(
                400, {"error": {"message": "Invalid JSON request body or framing"}}
            )
            return
        # Model-less response lookups cannot be safely routed by model.
        if (
            "/responses/" in parsed.path
            and parsed.path.rsplit("/", 1)[-1] != "compact"
            and model is None
        ):
            self.send_json(
                400,
                {
                    "error": {
                        "message": "A model is required for regional response routing"
                    }
                },
            )
            return
        region = region_for_model(model)
        excluded = HOP_HEADERS | {"host", "content-length"}
        excluded |= {
            x.strip().lower() for x in self.headers.get("Connection", "").split(",")
        }
        headers = {k: v for k, v in self.headers.items() if k.lower() not in excluded}
        headers["Connection"] = "close"
        upstream = self.server.connection_factory(region)
        response_started = False
        try:
            upstream.request(self.command, self.path, body=body, headers=headers)
            response = upstream.getresponse()
            prefetched = None
            if response.status == 400:
                prefetched = response.read(1048576)
                if is_region_state_error(response.status, prefetched):
                    clean = without_encrypted_reasoning(
                        body, self.headers.get("Content-Encoding", "")
                    )
                    if clean is not None:
                        # A rejected validation request did not generate a
                        # response. Retry once, retaining the complete visible
                        # history and all tool calls, outputs, and summaries.
                        upstream.close()
                        upstream = self.server.connection_factory(region)
                        upstream.request(
                            self.command, self.path, body=clean, headers=headers
                        )
                        response = upstream.getresponse()
                        prefetched = None
                        print(
                            json.dumps(
                                {
                                    "event": "retry_without_cross_region_reasoning",
                                    "region": region,
                                    "model": model,
                                    "status": response.status,
                                }
                            ),
                            flush=True,
                        )
            with self.server.count_lock:
                self.server.route_counts[region] += 1
            print(
                json.dumps(
                    {"region": region, "model": model, "status": response.status}
                ),
                flush=True,
            )
            self.send_response(response.status, response.reason)
            response_excluded = HOP_HEADERS | {"server", "date"}
            response_excluded |= {
                x.strip().lower()
                for x in response.getheader("Connection", "").split(",")
            }
            for name, value in response.getheaders():
                if name.lower() not in response_excluded:
                    self.send_header(name, value)
            self.send_header("Connection", "close")
            self.end_headers()
            response_started = True
            if prefetched:
                self.wfile.write(prefetched)
                self.wfile.flush()
            # read1 forwards SSE events as they arrive instead of buffering a
            # whole response or waiting for a large read buffer to fill.
            while chunk := response.read1(65536):
                self.wfile.write(chunk)
                self.wfile.flush()
        except (TimeoutError, OSError, http.client.HTTPException):
            if not response_started:
                self.send_json(
                    502, {"error": {"message": "Bedrock upstream connection failed"}}
                )
        finally:
            self.close_connection = True
            upstream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18081)
    args = parser.parse_args()
    with RouterServer(("127.0.0.1", args.port)) as server:
        print(
            json.dumps(
                {
                    "event": "listening",
                    "host": "127.0.0.1",
                    "port": server.server_port,
                    "default_region": DEFAULT_REGION,
                    "model_regions": MODEL_REGIONS,
                }
            ),
            flush=True,
        )
        server.serve_forever()


if __name__ == "__main__":
    main()
