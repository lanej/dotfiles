#!/usr/bin/env python3
"""Exercise migrated native entrypoints with controlled CLI responses and real files.

Live sockets, rendering and multi-client races remain in the native Zellij suites.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from zellij_ipc_fixture import action_server, fields, message

ROOT = Path(__file__).resolve().parents[1]


def pane(identifier, x=0, width=60, **changes):
    return {"id": identifier, "tab_id": 4, "is_plugin": False, "is_floating": False,
            "is_fullscreen": False, "is_suppressed": False, "is_collapsed": False,
            "exited": False, "is_focused": True, "is_selectable": True,
            "index_in_pane_group": {}, "pane_x": x, "pane_y": 1,
            "pane_columns": width, "pane_rows": 20, "pane_content_columns": width - 2,
            "title": "shell", "tab_name": "Tab #5", **changes}


class Helpers(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.home = Path(self.work.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "XDG_STATE_HOME": str(self.home / "state"),
                    "XDG_CACHE_HOME": str(self.home / "cache"), "XDG_RUNTIME_DIR": str(self.home),
                    "PATH": f"{self.bin}:{ROOT / 'bin'}:{os.environ['PATH']}", "FIXTURE": str(self.home),
                    "ZELLIJ_SESSION_NAME": "--session's literal name", "ZELLIJ_PANE_ID": "7",
                    "ZELLIJ_ORIGIN_PANE_ID": "terminal_1", "PARENT_PID": str(os.getpid())}
        for name, body in {
            "ps": 'print(os.environ["PARENT_PID"] + " 1 zellij")',
            "fzf": '''(root / "choices").write_text(sys.stdin.read())
(root / "fzf-args").write_text(json.dumps(sys.argv[1:]))
print((root / "selection").read_text())''',
            "zellij": '''args = sys.argv[1:]
with (root / "calls").open("a") as log:
    log.write(json.dumps(args) + "\\n")
plan = json.loads((root / "plan").read_text())
if not plan:
    sys.exit("unexpected native request: " + repr(args))
reply = plan.pop(0)
(root / "plan").write_text(json.dumps(plan))
if isinstance(reply, dict) and "error" in reply:
    sys.exit(reply["error"])
print(reply if isinstance(reply, str) else json.dumps(reply), end="")''',
        }.items():
            path = self.bin / name
            path.write_text(f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\nroot = Path(os.environ['FIXTURE'])\n" + body + "\n")
            path.chmod(0o755)

    def run_helper(self, name, *args, data=None, check=True):
        return subprocess.run([str(ROOT / "bin" / name), *args], env=self.env,
                              input=data, capture_output=True, check=check, timeout=10)

    def plan(self, replies):
        (self.home / "plan").write_text(json.dumps(replies))
        (self.home / "calls").unlink(missing_ok=True)

    def calls(self):
        path = self.home / "calls"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_popup_alias_and_dispatcher_preserve_prompt_environment(self):
        layouts = self.home / ".config/zellij/layouts"
        layouts.mkdir(parents=True)
        (layouts / "tmux.kdl").write_text("layout { pane; }\n")
        (self.bin / "zellij").write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
from pathlib import Path
assert sys.argv[1] == "--layout-string", sys.argv
Path(os.environ["FIXTURE"]).joinpath("popup-env").write_text(json.dumps(dict(os.environ)))
''')
        self.env.update(PS1="inherited-prompt> ", ZELLIJ="1", SSH_CONNECTION="")
        for command in (("zellij-popup",), ("zellij-helper", "popup")):
            self.run_helper(*command)
            forwarded = json.loads((self.home / "popup-env").read_text())
            self.assertEqual(forwarded.get("PS1"), "inherited-prompt> ")
            self.assertTrue(all(key not in forwarded for key in
                                ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID")))

    def test_clipboard_preserves_literal_sessions_and_rejects_unsafe_paste(self):
        selected = "--name / 'literal'"
        data = "hello\n界\tthere\n".encode()
        self.run_helper("zellij-clipboard", "copy", "--session", selected, data=data)
        self.assertEqual(self.run_helper("zellij-clipboard", "read", "--session", selected).stdout, data)
        path = self.home / f"zellij-clipboard-{os.getuid()}" / hashlib.sha256(selected.encode()).hexdigest()
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        for data in (b"\x1b[201~malicious", b"hello\x07"):
            self.run_helper("zellij-clipboard", "copy", "--session", selected, data=data)
            result = self.run_helper("zellij-clipboard", "read", "--session", selected, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"")
        result = self.run_helper("zellij-clipboard", "copy", "--session", selected,
                                 data=b"x" * (1024 * 1024 + 1), check=False)
        self.assertNotEqual(result.returncode, 0)
        path.unlink()
        target = self.home / "unrelated"
        target.write_text("preserve")
        path.symlink_to(target)
        self.assertNotEqual(self.run_helper("zellij-clipboard", "read", "--session", selected, check=False).returncode, 0)
        self.run_helper("zellij-clipboard", "clear", "--session", selected)
        self.assertEqual(target.read_text(), "preserve")

    def test_context_resolves_a_native_socket_without_process_inspection(self):
        with tempfile.TemporaryDirectory(prefix="zj-context-", dir="/tmp") as directory:
            work = Path(directory)
            namespace = work / "run/contract_version_1"
            namespace.mkdir(parents=True)
            cache = (self.home / "Library/Caches/org.Zellij-Contributors.Zellij" if sys.platform == "darwin"
                     else self.home / "cache/zellij")
            index = cache / "contract_version_1/session_index.sqlite"
            index.parent.mkdir(parents=True)
            with sqlite3.connect(index) as connection:
                connection.execute("CREATE TABLE sessions (name TEXT, id TEXT)")
                connection.execute("INSERT INTO sessions VALUES (?, ?)",
                                   (self.env["ZELLIJ_SESSION_NAME"], "native-id"))
            self.env["ZELLIJ_SOCKET_DIR"] = str(work / "run")
            (self.bin / "ps").write_text("#!/bin/sh\nexit 99\n")
            self.plan([])
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(str(namespace / "native-id"))
                identity = json.loads(self.run_helper("zellij-context", "socket").stdout)
                self.assertEqual(Path(identity[0]).resolve(), (namespace / "native-id").resolve())
                self.assertEqual(identity[2], (namespace / "native-id").stat().st_ino)
            self.assertEqual(self.calls(), [])

    def test_navigation_rechecks_client_and_refuses_ambiguous_focus(self):
        client = "CLIENT_ID ZELLIJ_PANE_ID RUNNING_COMMAND\n1 terminal_7 shell\n"
        tabs = [{"other_focused_clients": [1]}]
        current = {"tab_id": 4, "is_fullscreen_active": False}
        self.plan([client, tabs, [pane(7)], current, client, tabs, ""])
        self.run_helper("zellij-navigate", "left")
        self.assertEqual(self.calls()[-1], ["--session=--session's literal name", "action", "move-focus", "left"])
        for source in (pane(7, is_fullscreen=True), pane(7, tab_id=9)):
            self.plan([client, tabs, [source], current])
            self.run_helper("zellij-navigate", "left")
            self.assertFalse(any("move-focus" in call for call in self.calls()))
        self.plan([client, tabs, [pane(7)], current, client.replace("terminal_7", "terminal_8"), tabs])
        self.run_helper("zellij-navigate", "left")
        self.assertFalse(any("move-focus" in call for call in self.calls()))
        self.plan([client, [{"other_focused_clients": [1, 2]}]])
        result = self.run_helper("zellij-navigate", "left", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("move-focus" in call for call in self.calls()))

    def test_scrollback_navigation_requires_visible_single_client_ownership(self):
        client = "CLIENT_ID ZELLIJ_PANE_ID RUNNING_COMMAND\n"
        tabs = [{"tab_id": 4, "other_focused_clients": [1]}]
        current = {"tab_id": 4, "is_fullscreen_active": False}
        self.plan([client, tabs, [pane(7)], [pane(7)], current,
                   client, tabs, [pane(7)], ""])
        self.run_helper("zellij-navigate", "right")
        self.assertEqual(self.calls()[-1][-2:], ["move-focus", "right"])
        for changes in ({"is_suppressed": True}, {"is_focused": False}, {"tab_id": 9}):
            self.plan([client, tabs, [pane(7, **changes)]])
            self.run_helper("zellij-navigate", "right")
            self.assertFalse(any("move-focus" in call for call in self.calls()))
        self.plan([client, [{"tab_id": 4, "other_focused_clients": [1, 2]}]])
        result = self.run_helper("zellij-navigate", "right", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("move-focus" in call for call in self.calls()))
        # The editor can lose ownership after its first snapshot.
        self.plan([client, tabs, [pane(7)], [pane(7)], current,
                   client, tabs, [pane(7, is_suppressed=True)]])
        self.run_helper("zellij-navigate", "right")
        self.assertFalse(any("move-focus" in call for call in self.calls()))

    def test_balancing_verifies_each_boundary_and_stops_after_lost_reply(self):
        sockets = tempfile.TemporaryDirectory(prefix="zj-balance-", dir="/tmp")
        self.addCleanup(sockets.cleanup)
        namespace = Path(sockets.name) / "contract_version_1"
        namespace.mkdir(parents=True)
        self.env["ZELLIJ_SOCKET_DIR"] = str(namespace.parent)
        cache = (self.home / "Library/Caches/org.Zellij-Contributors.Zellij" if sys.platform == "darwin"
                 else self.home / "cache/zellij")
        index = cache / "contract_version_1/session_index.sqlite"
        index.parent.mkdir(parents=True)
        with sqlite3.connect(index) as connection:
            connection.execute("CREATE TABLE sessions (name TEXT, id TEXT)")
            connection.execute("INSERT INTO sessions VALUES (?, ?)",
                               (self.env["ZELLIJ_SESSION_NAME"], "balance"))
        before = [pane(1), pane(2, x=60, width=40)]
        after = [pane(1, width=50), pane(2, x=50, width=50)]
        (self.bin / "zellij").write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
from pathlib import Path
assert sys.argv[2:4] == ["prompt", "notify"], sys.argv
with Path(os.environ["FIXTURE"]).joinpath("calls").open("a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
''')
        actions, plan = [], []

        def reply(request):
            self.assertEqual(request[2], 1)
            self.assertEqual(request[4], 1)
            action = fields(request[1])
            actions.append(action)
            response = plan.pop(0)
            if response is None:
                return None
            if 98 in action:
                self.assertEqual(fields(action[98])[6], 1)
                return message(5, message(1, json.dumps(response).encode()))
            self.assertEqual(set(action), {118})
            resize = fields(action[118])
            self.assertEqual(fields(resize[1]), {1: 1})
            self.assertEqual(fields(resize[2]), {1: 2, 2: 2})
            return message(2, b"")

        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(namespace / "balance"))
            with action_server(listener, reply):
                plan[:] = [before, before, before, "", after]
                self.run_helper("zellij-balance", "equalize")
                self.assertFalse(plan)
                self.assertEqual(sum(118 in a for a in actions), 1)
                actions.clear()
                # The mutation's reply is lost; it must never be replayed.
                plan[:] = [before, before, before, None]
                result = self.run_helper("zellij-balance", "equalize", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(sum(118 in a for a in actions), 1)
                actions.clear()
                for unsupported in ([pane(1, is_fullscreen=True)],
                                    [pane(1, pane_rows=1), pane(2, pane_y=2, pane_rows=19)]):
                    plan[:] = [unsupported]
                    self.assertNotEqual(self.run_helper("zellij-balance", "equalize", check=False).returncode, 0)
                    self.assertFalse(any(118 in a for a in actions))
        self.assertFalse(any("action" in c or "setup" in c for c in self.calls()))

    def test_tab_picker_rejects_closed_target_and_keeps_names_as_data(self):
        sockets = tempfile.TemporaryDirectory(prefix="zj-picker-", dir="/tmp")
        self.addCleanup(sockets.cleanup)
        namespace = Path(sockets.name) / "contract_version_1"
        namespace.mkdir(parents=True)
        self.env["ZELLIJ_SOCKET_DIR"] = str(namespace.parent)
        cache = (self.home / "Library/Caches/org.Zellij-Contributors.Zellij" if sys.platform == "darwin"
                 else self.home / "cache/zellij")
        index = cache / "contract_version_1/session_index.sqlite"
        index.parent.mkdir(parents=True)
        with sqlite3.connect(index) as connection:
            connection.execute("CREATE TABLE sessions (name TEXT, id TEXT)")
            connection.execute("INSERT INTO sessions VALUES (?, ?)",
                               (self.env["ZELLIJ_SESSION_NAME"], "picker"))
        theme = self.home / "theme"
        theme.mkdir()
        (theme / "fzf.txt").write_text("--color=dark,header:#123456\n")
        self.env["DOTFILES_THEME_DIR"] = str(theme)
        title = "manual; $(touch should-not-exist)\nname"
        tabs = [{"tab_id": 4, "position": 1, "name": title}, {"tab_id": 8, "position": 2, "name": "other"}]
        (self.home / "selection").write_text("8")
        self.plan([])
        actions, plan = [], []

        def reply(request):
            self.assertEqual(request[2], 7)
            self.assertEqual(request[4], 1)
            action = fields(request[1])
            actions.append(action)
            response = plan.pop(0)
            if 104 in action or 98 in action:
                self.assertEqual(fields(next(iter(action.values())))[6], 1)
                return message(5, message(1, json.dumps(response).encode()))
            if 92 in action:
                self.assertEqual(fields(action[92])[1].decode(), target)
                return response
            self.assertEqual(set(action), {101})
            self.assertEqual(fields(action[101]), {1: 8})
            return message(2, b"")

        with socket.socket(socket.AF_UNIX) as listener:
            listener.bind(str(namespace / "picker"))
            with action_server(listener, reply):
                plan[:] = [tabs, [pane(7)], [tabs[0]]]
                result = self.run_helper("zellij-picker", "tabs", check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any(101 in action for action in actions))
                self.assertIn("manual; $(touch should-not-exist) name", (self.home / "choices").read_text())
                self.assertIn("--color=dark,header:#123456", json.loads((self.home / "fzf-args").read_text()))
                plan[:] = [tabs, [pane(7)], tabs, ""]
                self.run_helper("zellij-picker", "tabs")
                self.assertEqual(sum(101 in action for action in actions), 1)
                self.assertFalse((self.home / "should-not-exist").exists())
                preview = next(arg.removeprefix("--preview=") for arg in
                               json.loads((self.home / "fzf-args").read_text()) if arg.startswith("--preview="))
                plan[:] = [[]]
                rendered = subprocess.run(["/bin/sh", "-c", preview.replace("{1}", "8")],
                                          env=self.env, capture_output=True, text=True, check=True, timeout=5)
                self.assertIn("No other terminal pane", rendered.stdout)
                self.assertFalse(plan)
                self.assertFalse(self.calls())
                target = "literal; $(touch should-not-exist)"
                import base64
                (self.home / "selection").write_text(base64.urlsafe_b64encode(target.encode()).decode())
                listing = target + " [Created 1s ago] \n"
                for completion, succeeds in ((message(3, bytes([8, 5])), True),
                                             (message(6, message(1, b"rejected")), False)):
                    self.plan([listing, listing])
                    plan[:] = [completion]
                    result = self.run_helper("zellij-picker", "sessions", check=False)
                    self.assertEqual(result.returncode == 0, succeeds, result.stderr)
                    self.assertFalse(plan)
                    self.assertTrue(all(call == ["list-sessions", "--no-formatting"] for call in self.calls()))
                self.assertFalse((self.home / "should-not-exist").exists())

    def test_claude_title_preserves_manual_name_and_rejects_delayed_events(self):
        identity = "019a1234-abcd-7000-aaaa-bbbbbbbbbbbb"
        event = {"session_id": identity, "hook_event_name": "SessionStart", "cwd": "/work/project"}
        self.plan([[pane(7, title="manual")], "", [pane(7, title="native")], ""])
        self.run_helper("claude-zellij-title-hook", "--timestamp", "100", data=json.dumps(event).encode())
        renames = [call[-1] for call in self.calls() if "rename-pane" in call]
        self.assertEqual(renames, ["", "manual"])
        self.plan([])
        event["hook_event_name"] = "Stop"
        self.run_helper("claude-zellij-title-hook", "--timestamp", "90", data=json.dumps(event).encode())
        self.assertEqual(self.calls(), [])

    def test_codex_title_uses_native_identity_instead_of_inherited_pane(self):
        identity = "019a1234-abcd-7000-aaaa-bbbbbbbbbbbb"
        event = {"session_id": identity, "hook_event_name": "SessionStart", "cwd": "/work/project"}
        self.plan(["actual-session\n", [pane(42, title=f"codex | {identity} | project")], ""])
        self.run_helper("codex-zellij-title-hook", "--timestamp", "100", data=json.dumps(event).encode())
        rename = self.calls()[-1]
        self.assertEqual(rename[:6], ["--session", "actual-session", "action", "rename-pane", "--pane-id", "terminal_42"])
        self.assertEqual(rename[-1], "󰚩 project")
        event.update(hook_event_name="PreToolUse", cwd="/tmp/tool-worktree")
        self.plan([[pane(42, title=rename[-1])]])
        self.run_helper("codex-zellij-title-hook", "--timestamp", "110", data=json.dumps(event).encode())
        self.assertFalse(any("rename-pane" in call for call in self.calls()))
        outside = {**event, "session_id": "019a1234-abcd-7000-aaaa-cccccccccccc"}
        self.plan(["actual-session\n", [pane(42, title=rename[-1])]])
        self.run_helper("codex-zellij-title-hook", "--timestamp", "120", data=json.dumps(outside).encode())
        self.assertFalse(any("rename-pane" in call for call in self.calls()))
        self.plan([])
        self.run_helper("codex-zellij-title-hook", "--timestamp", "90", data=json.dumps(event).encode())
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
