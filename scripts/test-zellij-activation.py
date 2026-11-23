#!/usr/bin/env python3
"""Exercise native session identity and checkpoint refusal in an owned Zellij."""

import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parent.parent
COMMAND = ROOT / "scripts/zellij-activation.py"
Terminal = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))["Terminal"]


class NativeActivationTest(unittest.TestCase):
    def test_native_owned_server_is_preserved_when_application_checkpoint_is_missing(self):
        binary = Path.home() / ".local/bin/zellij"
        helper = Path.home() / ".local/bin/zellij-context"
        self.assertTrue(binary.is_file(), "Install the pinned Zellij runtime before native acceptance")
        self.assertTrue(helper.is_file(), "Install the native Zellij collaboration helpers")
        with tempfile.TemporaryDirectory(prefix="z-act-") as temporary:
            base = Path(temporary)
            home = base / "home"
            (home / ".local/bin").mkdir(parents=True)
            (home / ".local/bin/zellij").symlink_to(binary)
            (home / ".local/bin/zellij-context").symlink_to(helper)
            (home / ".local/.dotfiles-zellij-install").write_text("native-test-selected-runtime\n")
            sockets = base / "sockets"
            sockets.mkdir()
            temp_files = base / "tmp"
            temp_files.mkdir(mode=0o700)
            # This is an explicit independent test-terminal baseline, not an
            # agent-runner environment or a claim about the user's baseline.
            env = {
                "HOME": str(home), "PATH": str(home / ".local/bin") + ":/usr/bin:/bin:/usr/sbin:/sbin",
                "TERM": "xterm-256color", "COLORTERM": "truecolor", "SHELL": "/bin/sh",
                "USER": os.environ.get("USER", "fixture"), "LC_ALL": "C", "TZ": "UTC",
                "ZELLIJ_SOCKET_DIR": str(sockets), "XDG_CACHE_HOME": str(home / ".cache"),
                "XDG_STATE_HOME": str(home / ".local/state"), "TMPDIR": str(temp_files),
            }
            session = "activation-" + uuid.uuid4().hex[:12]
            data = home / "Library/Application Support/org.Zellij-Contributors.Zellij" if sys.platform == "darwin" else home / ".local/share/zellij"
            data.mkdir(parents=True)
            (data / "desktop_integration.json").write_text('{"flags":["SetupNeverShow"]}\n')
            terminal = Terminal(str(binary), env, session, command=[
                str(binary), "--layout-string",
                'layout {\n pane command="/bin/sh" {\n args "-c" "sleep 120"\n }\n}\n',
                "attach", "--create", session],
                install_navigation=False)
            managed = None
            try:
                selected = os.environ.get("ZELLIJ_TEST_SELECTED_RUNTIME")
                if selected:
                    installed = subprocess.run(
                        [sys.executable, str(ROOT / "scripts/zellij-artifacts.py"), "runtime", selected],
                        env=env, text=True, capture_output=True)
                    self.assertEqual(installed.returncode, 0, installed.stderr)
                    managed = Terminal(str(home / ".local/bin/zellij"), env, session, command=[
                        str(home / ".local/bin/zellij"), "--activation-client", "attach", session],
                        install_navigation=False)
                    managed.drain(1)
                    self.assertEqual(os.waitpid(terminal.pid, os.WNOHANG)[0], 0,
                                     "A new managed CLI attachment must preserve the original legacy client")
                    self.assertEqual(os.waitpid(managed.pid, os.WNOHANG)[0], 0,
                                     "The actual new managed CLI must attach compatibly to the old curated server")
                staged = subprocess.run([sys.executable, str(COMMAND), "stage"], env=env,
                                        text=True, capture_output=True)
                self.assertEqual(staged.returncode, 0, staged.stderr)
                deadline = time.monotonic() + 15
                target = None
                while time.monotonic() < deadline:
                    terminal.drain()
                    observed = subprocess.run([sys.executable, str(COMMAND), "inventory"],
                                              env=env, text=True, capture_output=True)
                    if observed.returncode == 0:
                        target = next((row for row in json.loads(observed.stdout)["targets"]
                                       if row["target"] == session), None)
                        if target is not None and target.get("native_ready"):
                            break
                    time.sleep(0.05)
                self.assertIsNotNone(target, observed.stderr + "\n" +
                                     terminal.output[-3000:].decode(errors="replace") +
                                     "\n" + observed.stdout)
                self.assertTrue(target["native_ready"])
                if managed is not None:
                    self.assertEqual(os.waitpid(managed.pid, os.WNOHANG)[0], 0)
                self.assertEqual(target["process"]["owner_verified"], True)
                self.assertIsNotNone(target["expected_identity"])
                self.assertIsNone(target["running_identity"], "Installed identity cannot prove loaded artifacts")
                self.assertTrue(target["uncheckpointed_panes"], "The real native terminal pane must be accounted for")
                operation = base / "operation"
                checkpoints = operation / "checkpoints"
                checkpoints.mkdir(parents=True, mode=0o700)
                run_id = str(uuid.uuid4())
                frozen = operation / "zellij-inventory.json"
                frozen.write_text(json.dumps({"schema_version": 1, "targets": [target]}))
                frozen.chmod(0o600)
                activation_env = {**env, "PROJECT_UPDATE_RUN_ID": run_id,
                                  "PROJECT_UPDATE_OPERATION_DIR": str(operation),
                                  "PROJECT_UPDATE_CHECKPOINT_DIR": str(checkpoints),
                                  "PROJECT_UPDATE_TARGET": session}
                result = subprocess.run([sys.executable, str(COMMAND), "checkpoint"],
                                        env=activation_env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 3, result.stderr)
                response = json.loads(result.stdout)["targets"][0]
                self.assertEqual(response["process"], target["process"])
                self.assertEqual(response["checkpoint"], {"state": "refused", "run_id": run_id})
                key = hashlib.sha256(target["process"]["native_id"].encode()).hexdigest()
                saved = json.loads((checkpoints / f"zellij-{key}.json").read_text())
                self.assertEqual(saved["state"], "refused")
                self.assertIn("layout", saved["layout"])
                self.assertEqual(saved["persistent_identity"], target["persistent_identity"])
                os.kill(target["process"]["pid"], 0)
                self.assertEqual(os.waitpid(terminal.pid, os.WNOHANG)[0], 0,
                                 "Refused checkpoint must preserve the native server and client")
            finally:
                # This exact disposable session and its processes belong to the test.
                subprocess.run([str(binary), "kill-session", session], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                terminal.close()
                if managed is not None:
                    managed.close()


if __name__ == "__main__":
    unittest.main()
