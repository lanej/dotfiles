"""One detector for AC-only sleep control through the real watcher entrypoint."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parent.parent


class AcAwakeWorkflow(unittest.TestCase):
    def test_ac_battery_ac_then_shutdown_restores_sleep(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            fake = work / "pmset"
            fake.write_text(
                f"#!{sys.executable}\n"
                "from pathlib import Path\n"
                "import sys\n"
                "root = Path(__file__).parent\n"
                "if sys.argv[1:] == ['-g', 'batt']:\n"
                "    counter = root / 'reads'\n"
                "    n = int(counter.read_text()) if counter.exists() else 0\n"
                "    counter.write_text(str(n + 1))\n"
                "    source = 'Battery Power' if n == 1 else 'AC Power'\n"
                "    print(\"Now drawing from '\" + source + \"'\")\n"
                "elif sys.argv[1:3] == ['-a', 'disablesleep']:\n"
                "    with (root / 'writes').open('a') as stream:\n"
                "        stream.write(sys.argv[3] + '\\n')\n"
                "else:\n"
                "    raise SystemExit(2)\n"
            )
            fake.chmod(0o755)
            controller = Path(os.environ.get("AC_AWAKE_TEST_CONTROLLER", ROOT / "bin/ac-awake"))
            process = subprocess.Popen(
                ["/bin/bash", str(controller), "watch", "--pmset", str(fake), "--interval", "1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            writes = work / "writes"
            try:
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    observed = writes.read_text().splitlines() if writes.exists() else []
                    if observed == ["1", "0", "1"]:
                        break
                    if process.poll() is not None:
                        break
                    time.sleep(0.05)
                self.assertEqual(observed, ["1", "0", "1"])
            finally:
                if process.poll() is None:
                    process.terminate()
                output, error = process.communicate(timeout=4)
            self.assertEqual(process.returncode, 0, output + error)
            self.assertEqual(writes.read_text().splitlines(), ["1", "0", "1", "0"])


if __name__ == "__main__":
    unittest.main()
