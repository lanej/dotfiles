#!/usr/bin/env python3
"""Exercise host configuration/reload entrypoints without a terminal runtime."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HELPER = Path(__file__).resolve().parents[1] / "bin/zellij-status"
DEFAULT = {"priority": [["marked", "needs_you", "failed"], ["working", "new_output", "bell"]]}


class StatusConfig(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.config = self.home / ".config/zellij/lane-status.toml"
        self.config.parent.mkdir(parents=True)
        self.log = self.home / "calls"
        self.env = {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": "",
                    "ZELLIJ_SESSION_NAME": "current", "PATH": f"{self.home}:{os.environ['PATH']}",
                    "TEST_LOG": str(self.log), "TEST_MODE": "ok"}
        fake = self.home / "zellij"
        fake.write_text('''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
with open(os.environ["TEST_LOG"], "a") as log:
    log.write(json.dumps(args) + "\\n")
mode = os.environ["TEST_MODE"]
if "list-panes" in args:
    if mode == "missing-session":
        sys.exit("session does not exist")
    rows = [{"id": 7, "is_plugin": True, "is_suppressed": True,
             "plugin_url": "file:" + os.environ["HOME"] + "/.config/zellij/plugins/lane-status.wasm"}]
    print(json.dumps([] if mode == "no-plugin" else rows))
elif "list-tabs" in args:
    print(json.dumps([{"other_focused_clients": [1, 2]}]))
elif "pipe" in args:
    payload = json.loads(args[-1])
    if mode == "timeout":
        time.sleep(8)
    for client in ([] if mode == "no-ack" else [1] if mode == "partial" else [1, 2]):
        reply = {"request": payload["request"], "plugin_id": payload["plugin_id"],
                 "client_id": client, "ok": True}
        if mode == "wrong-request":
            reply["request"] = "stale"
        if mode == "wrong-plugin":
            reply["plugin_id"] = 99
        if mode == "rejected":
            reply["error"] = "permission denied"
        print(json.dumps(reply))
else:
    sys.exit("unexpected command")
''')
        fake.chmod(0o755)

    def run_helper(self, *args):
        return subprocess.run([str(HELPER), *args], env=self.env, capture_output=True,
                              text=True, timeout=10)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_missing_defaults_and_view_compatibility(self):
        result = self.run_helper("config")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), DEFAULT)
        self.config.write_text("invalid = [")
        result = self.run_helper("view")
        self.assertEqual(result.returncode, 0, result.stderr)
        view = json.loads(result.stdout)
        self.assertEqual(set(view), {"session", "auto_titles", "host", "clock", "battery"})
        self.assertIsNone(view["session"])
        self.assertEqual(view["auto_titles"], {})

    def test_config_and_xdg(self):
        self.config.write_text('[attention]\npriority = [["done"], ["quiet", "marked"]]\n')
        self.env["XDG_CONFIG_HOME"] = "relative/ignored"
        self.assertEqual(json.loads(self.run_helper("config").stdout),
                         {"priority": [["done"], ["quiet", "marked"]]})
        xdg = self.home / "custom"
        (xdg / "zellij").mkdir(parents=True)
        (xdg / "zellij/lane-status.toml").write_text('[attention]\npriority = [["bell"]]\n')
        self.env["XDG_CONFIG_HOME"] = str(xdg)
        self.assertEqual(json.loads(self.run_helper("config").stdout), {"priority": [["bell"]]})

    def test_invalid_config_never_sends(self):
        cases = ["", "[attention", '[attention]\npriority = []',
                 '[attention]\npriority = [[]]', '[attention]\npriority = ["marked"]',
                 '[attention]\npriority = [["marked"], ["marked"]]',
                 '[attention]\npriority = [["unknown"]]', '[attention]\npriority = [[3]]',
                 '[attention]\npriority = [["marked"]]\nextra = true',
                 '[other]\npriority = [["marked"]]',
                 '[attention]\npriority = [["marked"]]\n[other]', "#" * (16 * 1024 + 1)]
        for content in cases:
            with self.subTest(content=content[:100]):
                self.config.write_text(content)
                for command in ("config", "reload"):
                    result = self.run_helper(command)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(str(self.config), result.stderr)
                self.assertEqual(self.calls(), [])

    def test_fifo_is_rejected_without_blocking(self):
        os.mkfifo(self.config)
        result = self.run_helper("config")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("regular file", result.stderr)

    def test_reload_targets_only_selected_session_and_receiver(self):
        self.config.write_text('[attention]\npriority = [["bell"], ["failed", "marked"]]\n')
        for selected, arguments in (("current", ()), ("other session", ("--session", "other session"))):
            with self.subTest(selected=selected):
                self.log.unlink(missing_ok=True)
                result = self.run_helper("reload", *arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("2 attached client(s)", result.stdout)
                calls = self.calls()
                self.assertEqual(len(calls), 4)
                self.assertTrue(all(call[0] == "--session=" + selected for call in calls))
                self.assertEqual(calls[0][1:], ["action", "list-panes", "--all", "--json"])
                pipe = calls[2]
                self.assertEqual(pipe[1:-1], ["pipe", "--name", "lane-attention-reload", "--"])
                payload = json.loads(pipe[-1])
                self.assertEqual(payload["priority"], [["bell"], ["failed", "marked"]])
                self.assertEqual(payload["plugin_id"], 7)
                self.assertTrue(payload["request"])

    def test_reload_requires_existing_session_and_receiver(self):
        for mode in ("no-plugin", "missing-session"):
            with self.subTest(mode=mode):
                self.env["TEST_MODE"] = mode
                self.log.unlink(missing_ok=True)
                result = self.run_helper("reload")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any("pipe" in call for call in self.calls()))
        self.env.pop("ZELLIJ_SESSION_NAME")
        self.log.unlink()
        self.assertNotEqual(self.run_helper("reload").returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_reload_requires_complete_matching_acknowledgements(self):
        for mode in ("no-ack", "partial", "wrong-request", "wrong-plugin", "rejected", "timeout"):
            with self.subTest(mode=mode):
                self.env["TEST_MODE"] = mode
                result = self.run_helper("reload")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("outcome may be partial", result.stderr)
                self.assertNotIn("Reloaded", result.stdout)


if __name__ == "__main__":
    unittest.main()
