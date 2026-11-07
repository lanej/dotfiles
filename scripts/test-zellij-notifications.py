#!/usr/bin/env python3
"""Exercise the actual notification recorder and history CLI without a runtime."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin/zellij-notify"
loader = importlib.machinery.SourceFileLoader("notifications", str(TOOL))
spec = importlib.util.spec_from_loader(loader.name, loader)
notify = importlib.util.module_from_spec(spec)
loader.exec_module(notify)


def event(identifier, **values):
    return {"id": str(identifier), "session": "main", "pane_id": "terminal_3",
            "server_pid": 100, "pane_pid": 200, "time_ms": 1700000000000 + int(identifier),
            "level": "warn", "title": "Tests", "message": "Needs a decision", **values}


class History(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.environment = patch.dict(os.environ, {"XDG_STATE_HOME": self.work.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def run_tool(self, *args):
        return subprocess.run([str(TOOL), *args], check=True, capture_output=True, text=True)

    def test_concurrent_clients_deduplicate_without_losing_distinct_events(self):
        processes = [subprocess.Popen([str(TOOL), "record", json.dumps([
            event(1), event(index + 2)])], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for index in range(8)]
        results = [(process, process.communicate(timeout=10)) for process in processes]
        for process, (out, error) in results:
            self.assertEqual(process.returncode, 0, error.decode())
        rows = json.loads(self.run_tool("list").stdout)
        self.assertEqual({row["id"] for row in rows}, {str(i) for i in range(1, 10)})
        path = Path(self.work.name) / "dotfiles/zellij/notifications.json"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)

    def test_retention_is_bounded_and_preview_strips_control_sequences(self):
        for start in range(0, 540, 30):
            self.run_tool("record", json.dumps([event(i, message="\x1b\x07\nresult" + "界" * 900)
                                               for i in range(start, start + 30)], ensure_ascii=False))
        rows = json.loads(self.run_tool("list").stdout)
        self.assertEqual(len(rows), notify.LIMIT)
        self.assertEqual(rows[0]["id"], "40")
        self.assertLessEqual(len(rows[-1]["message"]), 512)
        preview = self.run_tool("show", "539").stdout
        self.assertNotIn("\x1b", preview)
        self.assertNotIn("\x07", preview)
        self.assertIn("Tests", preview)
        self.assertIn("terminal_3", preview)

    def test_corrupt_history_is_reported_and_preserved(self):
        self.run_tool("record", json.dumps([event(1)]))
        path = Path(self.work.name) / "dotfiles/zellij/notifications.json"
        path.write_text("damaged history")
        result = subprocess.run([str(TOOL), "record", json.dumps([event(2)])],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), "damaged history")

    def test_jump_refuses_stale_pane_and_preserves_literal_session_names(self):
        row = event(1, session="--a session's name")
        with patch.dict(os.environ, {"ZELLIJ_SESSION_NAME": "origin"}):
            with patch.object(notify, "zellij", return_value="stale\n") as run:
                with self.assertRaisesRegex(ValueError, "closed or changed"):
                    notify.jump(row)
                self.assertEqual(run.call_count, 1)
            with patch.object(notify, "zellij", side_effect=["valid\nvalid\n", ""]) as run:
                notify.jump(row)
                self.assertEqual(run.call_args.args,
                                 ("action", "switch-session", "--pane-id", "terminal_3", "--", row["session"]))
                self.assertEqual(run.call_args.kwargs, {"session": "origin"})


if __name__ == "__main__":
    unittest.main()
