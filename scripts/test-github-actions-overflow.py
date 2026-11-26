"""Exercise watcher cooldown and dispatch reservations using recorded HTTP shapes."""

from contextlib import ExitStack
from datetime import datetime, timezone
from email.utils import formatdate
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("github-actions-overflow.py")
WATCHER = runpy.run_path(str(SCRIPT))["main"].__globals__


def response(status, body=None, headers=None, stderr=""):
    code = int(status.split()[0])
    lines = [f"HTTP/2.0 {status}"]
    lines.extend(f"{name}: {value}" for name, value in (headers or {}).items())
    output = "\r\n".join(lines) + "\r\n\r\n"
    if body is not None:
        output += json.dumps(body)
    return subprocess.CompletedProcess(["gh", "api"], int(code >= 400), output, stderr)


class OverflowBackoffTest(unittest.TestCase):
    def setUp(self):
        resources = ExitStack()
        self.addCleanup(resources.close)
        tmp = resources.enter_context(TemporaryDirectory())
        self.state = Path(tmp) / "state.json"
        self.backoff = self.state.with_suffix(".backoff.json")
        resources.enter_context(patch.object(sys, "argv", [str(SCRIPT), "--state", str(self.state)]))
        self.log = resources.enter_context(patch.object(sys, "stderr", new_callable=io.StringIO))
        resources.enter_context(patch.object(sys, "stdout", new_callable=io.StringIO))
        self.gh = resources.enter_context(patch.object(subprocess, "run"))

    def run_watcher(self, *results):
        self.gh.reset_mock()
        self.gh.side_effect = results
        WATCHER["main"]()
        return [call.args[0][3] for call in self.gh.call_args_list]

    def test_graphql_throttle_stops_rest_fallback_and_later_polls(self):
        now = int(datetime.now(timezone.utc).timestamp())
        deadline = now + 180
        limited = response(
            "200 OK", {"errors": [{"type": "RATE_LIMITED", "message": "Quota exhausted"}]},
            {"X-RateLimit-Remaining": 0, "Retry-After": formatdate(deadline, usegmt=True),
             "X-RateLimit-Reset": now + 90},
        )
        rest_fallback = response("200 OK", {"workflow_runs": []})
        self.assertEqual(self.run_watcher(limited, rest_fallback), ["graphql"])
        self.assertEqual(json.loads(self.backoff.read_text()), {
            "retry_at": deadline, "consecutive": 1, "reason": "GitHub GraphQL primary rate limit",
        })
        self.assertEqual(self.run_watcher(), [])
        self.assertFalse(self.state.exists())
        self.assertIn("Polling resumes after", self.log.getvalue())

    def test_primary_403_uses_reset_and_headerless_throttling_backs_off(self):
        now = int(datetime.now(timezone.utc).timestamp())
        denied = response("403 Forbidden", {"message": "Resource not accessible by integration"})
        exhausted = response("403 Forbidden", {"message": "API rate limit exceeded"}, {
            "x-ratelimit-remaining": "0", "x-ratelimit-reset": now + 420, "Retry-After": "60",
        })
        paths = self.run_watcher(denied, exhausted)
        self.assertEqual(paths[0], "graphql")
        self.assertIn("/actions/workflows/pi-resources.yml/runs?", paths[1])
        backoff = json.loads(self.backoff.read_text())
        self.assertGreaterEqual(backoff["retry_at"], now + 420)
        self.backoff.write_text(json.dumps(dict(backoff, retry_at=now - 1)))
        headerless = response("429 Too Many Requests")
        self.assertEqual(self.run_watcher(headerless), ["graphql"])
        next_backoff = json.loads(self.backoff.read_text())
        self.assertEqual(next_backoff["consecutive"], 2)
        self.assertGreaterEqual(next_backoff["retry_at"], now + 120)

    def test_ordinary_errors_keep_rest_fallback_and_clear_expired_backoff(self):
        self.backoff.write_text(json.dumps({
            "retry_at": 1, "consecutive": 1, "reason": "GitHub GraphQL rate limit",
        }))
        denied = response("200 OK", {"errors": [
            {"type": "FORBIDDEN", "message": "Resource not accessible by integration"},
        ]})
        paths = self.run_watcher(denied, response("200 OK", {"workflow_runs": []}))
        self.assertEqual(paths[0], "graphql")
        self.assertIn("/actions/workflows/pi-resources.yml/runs?", paths[1])
        self.assertFalse(self.backoff.exists())

    def test_throttled_dispatch_retries_once_after_cooldown_and_keeps_receipt(self):
        commit, head = "a" * 40, "b" * 40
        job, pr = {"id": 42}, {"number": 7, "merge_commit_sha": commit, "head": {"sha": head}}
        empty_runs = response("200 OK", {"workflow_runs": []})
        runner = response("200 OK", {"runners": [
            {"name": WATCHER["RUNNER"], "status": "online", "busy": False},
        ]})
        refused = response(
            "429 Too Many Requests", {"message": "You have exceeded a secondary rate limit"},
            {"Retry-After": "120"},
        )
        with patch.dict(WATCHER, {"queue_hint": lambda _: {7},
                                  "select_job": lambda *_: iter([(job, pr)])}):
            paths = self.run_watcher(empty_runs, runner, refused)
            self.assertTrue(paths[-1].endswith("/mac-overflow.yml/dispatches"))
            key = f"42:{commit}"
            entry = json.loads(self.state.read_text())[key]
            self.assertEqual(entry["attempts"], 0)
            self.assertEqual(entry["retry_at"], json.loads(self.backoff.read_text())["retry_at"])
            self.assertEqual(self.run_watcher(), [])
            self.assertEqual(json.loads(self.state.read_text())[key], entry)
            entry["retry_at"] = 1
            self.state.write_text(json.dumps({key: entry}))
            backoff = json.loads(self.backoff.read_text())
            self.backoff.write_text(json.dumps(dict(backoff, retry_at=1)))
            accepted = response("200 OK", {"workflow_run_id": 101})
            paths = self.run_watcher(empty_runs, runner, accepted)
            self.assertTrue(paths[-1].endswith("/mac-overflow.yml/dispatches"))
            self.assertEqual(json.loads(self.state.read_text())[key]["run_id"], 101)
            self.assertFalse(self.backoff.exists())
            self.assertEqual(self.run_watcher(empty_runs), [paths[0]])


if __name__ == "__main__":
    unittest.main()
