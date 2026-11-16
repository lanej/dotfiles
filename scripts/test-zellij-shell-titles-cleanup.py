#!/usr/bin/env python3
"""Protect teardown against an exit-time writer outliving the client shutdown."""
import importlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

workflow = importlib.import_module("test-zellij-shell-titles")


class Teardown(unittest.TestCase):
    def test_waits_for_exit_time_writes_before_removing_the_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "history"
            with subprocess.Popen([sys.executable, "-c", '''import pathlib,sys,time
print("ready",flush=True)
sys.stdin.readline()
time.sleep(0.2)
pathlib.Path(sys.argv[1]).write_text("exit-time history")
''', str(marker)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as writer:
                self.assertEqual(writer.stdout.readline().strip(), "ready")
                writer.stdin.write("shutdown\n")
                writer.stdin.flush()
                workflow.wait_for_exit({writer.pid})
                self.assertEqual(marker.read_text(), "exit-time history")
                writer.wait(timeout=1)
        self.assertFalse(Path(directory).exists())

    def test_shutdown_timeout_reports_the_remaining_owned_process(self):
        with subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"]) as writer:
            try:
                with self.assertRaisesRegex(TimeoutError, str(writer.pid)):
                    workflow.wait_for_exit({writer.pid}, timeout=0.05)
            finally:
                writer.terminate()
                writer.wait(timeout=1)


if __name__ == "__main__":
    unittest.main()
