#!/usr/bin/env python3
"""Exercise notification history through native commands and simulated CLI boundaries."""
import json
from datetime import datetime
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin/zellij-notify"


def event(identifier, **values):
    return {"id": str(identifier), "session": "main", "pane_id": "terminal_3",
            "server_pid": 100, "pane_pid": 200, "time_ms": 1700000000000 + int(identifier),
            "level": "warn", "title": "Tests", "message": "Needs a decision", **values}


class History(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.directory = Path(self.work.name)
        self.env = {**os.environ, "XDG_STATE_HOME": self.work.name,
                    "PATH": f"{self.directory}:{os.environ['PATH']}",
                    "FIXTURE": self.work.name, "ZELLIJ_SESSION_NAME": "origin"}
        for name, script in {
            "zellij": '''
args = sys.argv[1:]
with (root / "calls").open("a") as log:
    log.write(json.dumps(args) + "\\n")
replies = json.loads((root / "replies").read_text())
reply = replies.pop(0)
(root / "replies").write_text(json.dumps(replies))
print(reply, end="")
''',
            "fzf": '''
(root / "choices").write_text(sys.stdin.read())
(root / "fzf-args").write_text(json.dumps(sys.argv[1:]))
selected = root / "selected"
if selected.exists():
    print(selected.read_text())
else:
    sys.exit(130)
''',
        }.items():
            path = self.directory / name
            path.write_text(f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\nroot = Path(os.environ['FIXTURE'])\n" + script)
            path.chmod(0o755)

    def run_tool(self, *args, check=True):
        return subprocess.run([str(TOOL), *args], env=self.env, check=check,
                              capture_output=True, text=True, timeout=10)

    def replies(self, values):
        (self.directory / "replies").write_text(json.dumps(values))
        (self.directory / "calls").unlink(missing_ok=True)

    def calls(self):
        path = self.directory / "calls"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def record(self, rows):
        self.run_tool("record", json.dumps(rows, ensure_ascii=False))

    def picker_text(self, rows):
        path = self.directory / "dotfiles/zellij/notifications.json"
        path.unlink(missing_ok=True)
        self.record(rows)
        self.run_tool("history")
        return (self.directory / "choices").read_text()

    def test_concurrent_clients_deduplicate_without_losing_distinct_events(self):
        processes = [subprocess.Popen([str(TOOL), "record", json.dumps([
            event(1), event(index + 2)])], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for index in range(8)]
        for process in processes:
            _, error = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, error.decode())
        rows = json.loads(self.run_tool("list").stdout)
        self.assertEqual({row["id"] for row in rows}, {str(i) for i in range(1, 10)})
        path = self.directory / "dotfiles/zellij/notifications.json"
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)

    def test_retention_is_bounded_and_recorded_messages_strip_controls(self):
        for start in range(0, 540, 30):
            self.record([event(i, message="\x1b\x07\nresult" + "界" * 900)
                         for i in range(start, start + 30)])
        rows = json.loads(self.run_tool("list").stdout)
        self.assertEqual(len(rows), 500)
        self.assertEqual(rows[0]["id"], "40")
        self.assertLessEqual(len(rows[-1]["message"]), 512)
        self.assertNotIn("\x1b", rows[-1]["message"])
        self.assertNotIn("\x07", rows[-1]["message"])

    def test_preview_shows_validated_pane_contents_with_colors(self):
        self.record([event(1)])
        content = "\x1b[32mApprove the deployment?\x1b[0m\n> Yes    No\n"
        self.replies(["valid\n", content, "valid\n"])
        self.assertEqual(self.run_tool("show", "1").stdout, content)
        self.assertEqual(self.calls()[1],
                         ["--session=main", "action", "dump-screen", "--ansi", "--pane-id", "terminal_3"])

    def test_preview_does_not_show_replaced_or_missing_sources(self):
        self.record([event(1)])
        for replies in [["stale\n"], ["valid\n", "OTHER PROCESS", "stale\n"]]:
            self.replies(replies)
            self.assertEqual(self.run_tool("show", "1").stdout, "Pane unavailable\n")
            self.assertEqual(len(self.calls()), len(replies))
        self.assertEqual(self.run_tool("show", "expired").stdout, "Pane unavailable\n")

    def test_dates_only_appear_when_entries_span_days(self):
        first = event(1, time_ms=int(datetime(2026, 11, 7, 9, 30).timestamp() * 1000))
        second = event(2, time_ms=int(datetime(2026, 11, 7, 11, 45).timestamp() * 1000))
        same_day = self.picker_text([first, second])
        self.assertIn("09:30", same_day)
        self.assertIn("11:45", same_day)
        self.assertNotIn("11-07", same_day)
        duplicate_time = self.picker_text([first, {**second, "time_ms": first["time_ms"]}])
        self.assertNotIn("09:30", duplicate_time)
        second["time_ms"] = int(datetime(2026, 11, 8, 11, 45).timestamp() * 1000)
        mixed_days = self.picker_text([first, second])
        self.assertIn("11-07 09:30", mixed_days)
        self.assertIn("11-08 11:45", mixed_days)

    def test_picker_hides_internal_identifiers_and_generated_labels(self):
        choices = self.picker_text([event(1, title="Pane #23", session="opaque-session"),
                                    event(2, title="Build checks", session="opaque-session")])
        labels = "\n".join(choice.split("\t", 1)[1] for choice in choices.splitlines())
        self.assertIn("Build checks", labels)
        self.assertIn("Needs a decision", labels)
        self.assertNotIn("Pane #23", labels)
        self.assertNotIn("opaque-session", labels)
        self.assertIn("--with-nth=2..", json.loads((self.directory / "fzf-args").read_text()))

    def test_corrupt_history_is_reported_and_preserved(self):
        self.record([event(1)])
        path = self.directory / "dotfiles/zellij/notifications.json"
        path.write_text("damaged history")
        result = self.run_tool("record", json.dumps([event(2)]), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), "damaged history")

    def test_empty_history_can_be_read_and_cancelled(self):
        self.run_tool("history")
        self.assertIn("No notifications", (self.directory / "fzf-args").read_text())
        self.assertEqual(self.calls(), [])

    def test_jump_refuses_stale_pane_and_preserves_literal_session_names(self):
        row = event(1, session="--a session's name")
        self.record([row])
        (self.directory / "selected").write_text("1")
        self.replies(["stale\n"])
        result = self.run_tool("history", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("closed or changed", result.stderr)
        self.assertEqual(len(self.calls()), 1)
        self.replies(["valid\nvalid\n", ""])
        self.run_tool("history")
        self.assertEqual(self.calls()[-1], ["--session=origin", "action", "switch-session",
                                          "--pane-id", "terminal_3", "--", row["session"]])
        self.picker_text([event(2, session="origin")])
        (self.directory / "selected").write_text("2")
        self.replies(["valid\n", ""])
        self.run_tool("history")
        self.assertEqual(self.calls()[-1], ["--session=origin", "action", "focus-pane-id", "terminal_3"])


if __name__ == "__main__":
    unittest.main()
