"""Behavioral tests for automatic termination and lifecycle boundaries."""
import contextlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("claude-tmux-later")
loader = SourceFileLoader("claude_tmux_later", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
app = importlib.util.module_from_spec(spec)
loader.exec_module(app)


NOW = 200000


def pane(pid="%7", session="main", window="@4"):
    return dict(session_id="$1", session_name=session, window_id=window,
                pane_id=pid, pane_current_command="claude", pane_dead="0",
                pane_in_mode="0", window_linked="0", pane_tty="/dev/pts/7",
                **{"@claude_later_pin": ""})


def state(age=3600):
    return dict(session_id="conversation-1", phase="idle", agents=[],
                background=False, last_activity=NOW-age, cwd="/project",
                owner={"pid": 42, "started": "Fri Sep 11 05:00:00 2026"},
                transcript_path="/tmp/conversation-1.jsonl")


class PolicyTests(unittest.TestCase):
    def decide(self, row=None, value=None, visible=None):
        row = row or pane()
        return app.decision([row], {row["pane_id"]: value or state()},
                            visible or set(), NOW, app.DEFAULTS)[0]

    def test_exact_one_hour_boundary(self):
        self.assertIsNone(self.decide(value=state(3599)))
        self.assertEqual(self.decide(value=state(3600)), "move")

    def test_24_hours_is_total_idle_not_time_in_later(self):
        self.assertIsNone(self.decide(pane(session="later"), state(86399)))
        self.assertEqual(self.decide(pane(session="later"), state(86400)), "close")

    def test_unparked_old_window_moves_before_any_close(self):
        self.assertEqual(self.decide(value=state(100000)), "move")

    def test_viewing_prevents_both_actions(self):
        for session in ("main", "later"):
            self.assertIsNone(self.decide(pane(session=session), state(100000), {"@4"}))

    def test_busy_forever_does_not_age_into_termination(self):
        for phase in ("busy", "unknown"):
            self.assertIsNone(self.decide(pane(session="later"), state(100000) | {"phase": phase}))

    def test_background_work_or_agents_prevents_cleanup(self):
        for extra in ({"background": True}, {"agents": ["agent-a"]}):
            self.assertIsNone(self.decide(pane(session="later"), state(100000) | extra))

    def test_mixed_window_is_preserved(self):
        rows = [pane(), pane("%8")]
        self.assertIsNone(app.decision(rows, {"%7": state()}, set(), NOW, app.DEFAULTS)[0])

    def test_youngest_pane_controls_clock(self):
        rows = [pane(), pane("%8")]
        states = {"%7": state(100000), "%8": state(20)}
        self.assertIsNone(app.decision(rows, states, set(), NOW, app.DEFAULTS)[0])

    def test_all_managed_panes_may_archive_together(self):
        rows = [pane(), pane("%8")]
        states = {"%7": state(4000), "%8": state(3600)}
        self.assertEqual(app.decision(rows, states, set(), NOW, app.DEFAULTS)[0], "move")

    def test_pin_link_copy_mode_and_dead_pane_prevent_close(self):
        for field in ("@claude_later_pin", "window_linked", "pane_in_mode", "pane_dead"):
            self.assertIsNone(self.decide(pane(session="later") | {field: "1"}, state(100000)))

    def test_clock_going_backwards_delays_cleanup(self):
        self.assertIsNone(self.decide(value=state(-10)))


class HookTests(unittest.TestCase):
    def event(self, kind, **fields):
        return dict(hook_event_name=kind, session_id="conversation-1", **fields)

    def test_new_prompt_cancels_old_idle_eligibility(self):
        s = app.transition(state(100000), self.event("UserPromptSubmit"), NOW)
        self.assertEqual(s["phase"], "busy")
        self.assertEqual(s["last_activity"], NOW)
        s = app.transition(s, self.event("Stop", background_tasks=[], session_crons=[]), NOW+10)
        self.assertNotEqual(app.decision([pane(session="later")], {"%7": s}, set(),
                                        NOW+86409, app.DEFAULTS)[0], "close")
        self.assertEqual(app.decision([pane(session="later")], {"%7": s}, set(),
                                     NOW+86410, app.DEFAULTS)[0], "close")
        self.assertEqual(s["last_activity"], NOW+10)

    def test_unknown_background_state_blocks_termination(self):
        s = app.transition(state(), self.event("Stop"), NOW)
        self.assertTrue(s["background"])

    def test_background_tasks_and_scheduled_prompts_protect_session(self):
        for field in ("background_tasks", "session_crons"):
            fields = {"background_tasks": [], "session_crons": []}
            fields[field] = [{"id": "scheduled-work"}]
            self.assertTrue(app.transition(state(), self.event("Stop", **fields), NOW)["background"])

    def test_subagent_tool_hooks_cannot_change_parent_phase(self):
        s = state() | {"phase": "busy"}
        for kind in ("Stop", "SessionEnd", "SessionStart"):
            self.assertEqual(app.transition(s, self.event(kind, agent_id="child"), NOW), s)

    def test_subagent_start_and_stop_keep_parent_state(self):
        s = app.transition(state(), self.event("SubagentStart", agent_id="child"), NOW)
        self.assertEqual(s["agents"], ["child"])
        s = app.transition(s, self.event("SubagentStop", agent_id="child"), NOW+10)
        self.assertEqual(s["agents"], [])
        self.assertEqual(s["last_activity"], NOW+10)

    def test_late_event_from_previous_conversation_does_not_delete_new_one(self):
        e = self.event("SessionEnd") | {"session_id": "old-session"}
        self.assertEqual(app.transition(state(), e, NOW), state())

    def test_session_end_removes_registration(self):
        self.assertIsNone(app.transition(state(), self.event("SessionEnd"), NOW))

    def test_cannot_enroll_without_verified_claude_process(self):
        self.assertIsNone(app.transition(None, self.event("SessionStart", source="startup"), NOW))

    def test_compaction_start_does_not_mark_busy_session_idle(self):
        s = state() | {"phase": "busy"}
        result = app.transition(s, self.event("SessionStart", source="compact"), NOW, s["owner"])
        self.assertEqual(result["phase"], "busy")

    def test_api_failure_is_unknown_until_later_successful_stop(self):
        self.assertEqual(app.transition(state(), self.event("StopFailure"), NOW)["phase"], "unknown")


class FakeTmux:
    def __init__(self, row, folder):
        self.row, self.folder, self.calls = row, folder, []
        self.visibility_calls = 0
        self.become_visible = False

    def panes(self):
        return [self.row.copy()]

    def visible_windows(self):
        self.visibility_calls += 1
        return {"@4"} if self.become_visible and self.visibility_calls > 1 else set()

    def move(self, row, name):
        self.calls.append(("move", row["window_id"], name))
        self.row["session_name"] = name

    def call(self, *args):
        # The resume record must exist before sending kill-window.
        history = (self.folder / "history.jsonl").read_text()
        assert '"session_id": "conversation-1"' in history
        assert '"action": "close-requested"' in history
        self.calls.append(args)


class SweepTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        app.write_json(self.folder / "state.json", {"%7": state(86400)})
        self.tmux = FakeTmux(pane(session="later"), self.folder)

    def tearDown(self):
        self.temp.cleanup()

    def run_sweep(self, cfg=None, inspect=False, owner=True):
        with patch.object(app.time, "time", return_value=NOW), \
             patch.object(app, "foreground_owner", return_value=owner), \
             contextlib.redirect_stdout(io.StringIO()):
            app.sweep(self.tmux, self.folder, cfg or app.DEFAULTS, inspect=inspect)

    def test_close_logs_resume_identity_before_kill_and_unregisters_pane(self):
        self.run_sweep()
        self.assertEqual(self.tmux.calls, [("kill-window", "-t", "@4")])
        self.assertEqual(app.read_json(self.folder / "state.json", {}), {})
        events = [json.loads(x)["action"] for x in (self.folder / "history.jsonl").read_text().splitlines()]
        self.assertEqual(events, ["close-requested", "close-completed"])

    def test_move_keeps_process_state_and_idle_clock(self):
        self.tmux.row["session_name"] = "main"
        self.run_sweep()
        self.assertEqual(self.tmux.calls, [("move", "@4", "later")])
        self.assertEqual(app.read_json(self.folder / "state.json", {})["%7"]["last_activity"], NOW-86400)

    def test_dry_run_and_status_never_mutate_tmux(self):
        for cfg, inspect in ((app.DEFAULTS | {"dry_run": True}, False), (app.DEFAULTS, True)):
            self.run_sweep(cfg, inspect)
            self.assertEqual(self.tmux.calls, [])
            self.assertIn("%7", app.read_json(self.folder / "state.json", {}))

    def test_client_switching_to_window_before_kill_cancels_it(self):
        self.tmux.become_visible = True
        self.run_sweep()
        self.assertEqual(self.tmux.calls, [])

    def test_pid_reuse_or_unverifiable_foreground_prevents_kill(self):
        self.run_sweep(owner=False)
        self.assertEqual(self.tmux.calls, [])


class ConfigurationTests(unittest.TestCase):
    def test_all_lifecycle_hooks_are_wired_once(self):
        doc = app.read_json(SCRIPT.parent.parent / ".claude/settings.json", {})
        for event in app.EVENTS:
            hooks = [h for entry in doc["hooks"][event] for h in entry["hooks"]
                     if "claude-tmux-later" in h.get("command", "")]
            self.assertEqual(len(hooks), 1, event)
            self.assertEqual(hooks[0]["command"], '"$HOME/.files/bin/claude-tmux-later" hook')
            self.assertFalse(hooks[0].get("async", False))

    def test_checked_in_defaults_match_runtime_defaults(self):
        self.assertEqual(app.read_json(SCRIPT.parent.parent / "claude/tmux-later.json", {}),
                         app.DEFAULTS)

    def test_observer_session_start_does_not_replace_foreground_session(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            app.write_json(root / "state.json", {"%7": state()})
            tmux = FakeTmux(pane(), root)
            event = dict(hook_event_name="SessionStart", session_id="observer", source="startup")
            with patch.dict(app.os.environ, {"TMUX": "/tmp/tmux,1,0", "TMUX_PANE": "%7"}), \
                 patch.object(app.sys, "stdin", io.StringIO(json.dumps(event))), \
                 patch.object(app, "settings", return_value=app.DEFAULTS), \
                 patch.object(app, "connection", return_value=(tmux, "1:1", root)), \
                 patch.object(app, "claude_ancestor", return_value={"pid": 99, "started": "now"}), \
                 patch.object(app, "foreground_owner", return_value=False), \
                 patch.object(app, "ensure_daemon") as daemon:
                app.hook()
                daemon.assert_not_called()
            self.assertEqual(app.read_json(root / "state.json", {}), {"%7": state()})


class ProcessTests(unittest.TestCase):
    def test_native_process_foreground_is_verified_without_controlling_tty(self):
        for tty, command in (("pts/7", "claude"), ("ttys007", "/Users/josh/.local/bin/claude")):
            line = f"1 42 42 {tty} Fri Sep 11 05:00:00 2026 {command}\n"
            result = SimpleNamespace(returncode=0, stdout=line)
            with patch.object(app.subprocess, "run", return_value=result):
                self.assertTrue(app.foreground_owner(pane() | {"pane_tty": "/dev/"+tty}, state()))

    def test_background_process_with_matching_name_cannot_be_closed(self):
        result = SimpleNamespace(returncode=0,
                                 stdout="1 42 99 pts/7 Fri Sep 11 05:00:00 2026 claude\n")
        with patch.object(app.subprocess, "run", return_value=result):
            self.assertFalse(app.foreground_owner(pane(), state()))

    def test_reused_pid_with_different_start_time_cannot_be_closed(self):
        result = SimpleNamespace(returncode=0,
                                 stdout="1 42 42 pts/7 Fri Sep 11 06:00:00 2026 claude\n")
        with patch.object(app.subprocess, "run", return_value=result):
            self.assertFalse(app.foreground_owner(pane(), state()))

    def test_observer_sharing_foreground_process_group_is_not_owner(self):
        result = SimpleNamespace(returncode=0,
                                 stdout="42 42 42 pts/7 Fri Sep 11 05:00:00 2026 claude\n")
        with patch.object(app.subprocess, "run", return_value=result):
            self.assertFalse(app.foreground_owner(pane(), state() | {
                "owner": {"pid": 99, "started": "Fri Sep 11 05:00:00 2026"}}))

    def test_versioned_native_executable_uses_wrapper_argv_zero(self):
        result = SimpleNamespace(returncode=0,
                                 stdout="1 42 42 pts/7 Fri Sep 11 05:00:00 2026 claude --resume id\n")
        with patch.object(app.subprocess, "run", return_value=result):
            self.assertTrue(app.foreground_owner(pane() | {"pane_current_command": "2.1.242"}, state()))


class TmuxAvailabilityTests(unittest.TestCase):
    def test_ci_requires_live_tmux_tests(self):
        if os.environ.get("REQUIRE_TMUX_TESTS") == "1":
            self.assertIsNotNone(shutil.which("tmux"))


@unittest.skipUnless(shutil.which("tmux"), "tmux is not installed")
class LiveTmuxTests(unittest.TestCase):
    """Use only a private socket, an empty config, and disposable sleep panes."""

    def setUp(self):
        # Short socket path also fits Darwin's sockaddr_un limit.
        self.temp = tempfile.TemporaryDirectory(prefix="claude-later-", dir="/tmp")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.tmux = app.Tmux(str(self.folder / "server.sock"))
        self.client = None
        self.addCleanup(self.stop_server)
        env = {k: v for k, v in os.environ.items() if k not in ("TMUX", "TMUX_PANE")}
        subprocess.run(["tmux", "-S", self.tmux.socket, "-f", "/dev/null",
                        "new-session", "-d", "-s", "main", "-n", "keep", "sleep 300"],
                       check=True, capture_output=True, env=env, timeout=5)
        self.claude = self.folder / "claude"
        # Copy executable bytes, not macOS's protected system-file flags.
        shutil.copyfile(shutil.which("sleep"), self.claude)
        self.claude.chmod(0o755)

    def stop_server(self):
        # This cannot reach the user's default server or any unrelated socket.
        subprocess.run(["tmux", "-S", self.tmux.socket, "kill-server"],
                       capture_output=True, timeout=5)
        if self.client:
            self.client.communicate(timeout=5)

    def new_claude(self, age=3600):
        pane_id = self.tmux.call("new-window", "-d", "-t", "main:", "-P", "-F", "#{pane_id}",
                                 f"exec {shlex.quote(str(self.claude))} 300")
        pid = int(self.tmux.call("display-message", "-p", "-t", pane_id, "#{pane_pid}"))
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            p = app.process(pid)
            row = next(r for r in self.tmux.panes() if r["pane_id"] == pane_id)
            s = state(age) | {"owner": {"pid": pid, "started": p["started"] if p else ""}}
            if p and app.foreground_owner(row, s):
                app.write_json(self.folder / "state.json", {pane_id: s})
                return row
            time.sleep(0.02)
        self.fail("Disposable native Claude fixture never owned its tmux foreground")

    def sweep(self, now=NOW, **overrides):
        with patch.object(app.time, "time", return_value=now):
            app.sweep(self.tmux, self.folder, app.DEFAULTS | overrides)

    def test_window_moves_then_closes_at_total_idle_deadline(self):
        row = self.new_claude()
        self.sweep()
        moved = next(r for r in self.tmux.panes() if r["pane_id"] == row["pane_id"])
        self.assertEqual(moved["session_name"], "later")
        self.assertEqual(moved["window_id"], row["window_id"])
        self.assertTrue(app.foreground_owner(moved, app.read_json(self.folder / "state.json", {})[row["pane_id"]]))
        self.sweep(NOW + 86400 - 3600 - 1)
        self.assertIn(row["pane_id"], [r["pane_id"] for r in self.tmux.panes()])
        self.sweep(NOW + 86400 - 3600)
        self.assertNotIn(row["pane_id"], [r["pane_id"] for r in self.tmux.panes()])
        self.assertIn("main", [r["session_name"] for r in self.tmux.panes()])
        self.assertIn("conversation-1", (self.folder / "history.jsonl").read_text())

    def test_existing_later_window_is_not_overwritten(self):
        existing = self.tmux.call("new-session", "-d", "-s", "later", "-P", "-F", "#{pane_id}", "sleep 300")
        row = self.new_claude()
        self.sweep()
        later = [r for r in self.tmux.panes() if r["session_name"] == "later"]
        self.assertEqual({r["pane_id"] for r in later}, {existing, row["pane_id"]})

    def test_mixed_and_busy_windows_are_untouched(self):
        row = self.new_claude(age=100000)
        self.tmux.call("split-window", "-d", "-t", row["pane_id"], "sleep 300")
        self.sweep()
        self.assertEqual({r["session_name"] for r in self.tmux.panes()}, {"main"})
        states = app.read_json(self.folder / "state.json", {})
        states[row["pane_id"]]["phase"] = "busy"
        app.write_json(self.folder / "state.json", states)
        self.sweep()
        self.assertEqual({r["session_name"] for r in self.tmux.panes()}, {"main"})

    def test_viewed_parked_window_is_not_closed(self):
        row = self.new_claude(age=100000)
        self.sweep()
        self.tmux.call("select-window", "-t", row["window_id"])
        self.client = subprocess.Popen(["tmux", "-S", self.tmux.socket, "-C", "attach-session", "-t", "later"],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + 3
        while row["window_id"] not in self.tmux.visible_windows() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertIn(row["window_id"], self.tmux.visible_windows())
        self.sweep()
        self.assertIn(row["pane_id"], [r["pane_id"] for r in self.tmux.panes()])


if __name__ == "__main__":
    unittest.main()
