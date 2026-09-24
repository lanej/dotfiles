"""One live regression detector for the Claude window-status feature.

Drives a window through the states a real session produces -- needs you, busy,
finished, forgotten -- through the actual hooks, and asserts the tab tmux draws
from rc/tmux.conf tells them apart.
"""
import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"


def capture(fn):
    """Run a script's main() and return what it wrote to the status bar."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        fn()
    return buffer.getvalue()


def tab_format():
    """The real window-status-format from rc/tmux.conf, as one tmux command."""
    text = (ROOT / "rc/tmux.conf").read_text()
    match = re.search(r"^set-window-option -g window-status-format \"(?:.*\\\n)*.*\"$",
                      text, re.MULTILINE)
    assert match, "rc/tmux.conf no longer defines window-status-format"
    return match.group(0)


def test_window_tab_separates_needs_from_activity_from_dormancy(
        load_script, private_tmux, monkeypatch):
    state = load_script("tmux-claude-state")
    sweep = load_script("tmux-claude-sweep")
    hooks = json.loads((ROOT / ".claude/settings.json").read_text())["hooks"]
    window = private_tmux.call("new-window", "-d", "-t", "main:", "-n", "project",
                               "-P", "-F", "#{window_id}", "sleep 300")
    pane = private_tmux.call("display-message", "-p", "-t", window, "#{pane_id}")
    monkeypatch.setenv("TMUX_PANE", pane)
    # Every assertion below compares whole rendered tabs, so the only thing that
    # may differ between them is the state. tmux's own automatic-rename would
    # otherwise retitle the window from its running command mid-test -- which it
    # does differently per platform -- and the comparisons would turn on the name
    # instead of on the styling they exist to check.
    private_tmux.call("set-option", "-w", "-t", window, "automatic-rename", "off")

    # Teach the throwaway server the tab the user actually sees.
    conf = private_tmux.folder / "tab.conf"
    conf.write_text(tab_format() + "\n")
    private_tmux.call("source-file", str(conf))

    def emit(event_name, hook_name, **fields):
        """Deliver an event through whichever hook settings.json wires to it."""
        event = dict(hook_event_name=event_name, session_id="conversation-1", **fields)
        commands = [h["command"] for entry in hooks.get(event_name, [])
                    for h in entry["hooks"]]
        script = next(c for c in commands if Path(c.strip('"')).name == hook_name)
        subprocess.run([str(BIN / hook_name)], input=json.dumps(event), text=True,
                       capture_output=True, timeout=10, check=True)
        return script

    def tab():
        return private_tmux.call("display-message", "-p", "-t", window,
                                 "#{E:window-status-format}")

    def option(name):
        return private_tmux.call("display-message", "-p", "-t", window, "#{%s}" % name)

    plain = tab()
    assert option("@claude-state") == "", "a fresh window starts un-Claude-ed"

    # A plan waiting on approval is a need, and must not look like a busy window.
    emit("PreToolUse", "claude-tmux-state-hook", tool_name="ExitPlanMode")
    assert option("@claude-class") == "need"
    plan = tab()

    # A tool running is activity: worth knowing, but not worth interrupting for.
    emit("PreToolUse", "claude-tmux-state-hook", tool_name="Bash")
    assert option("@claude-class") == "activity"
    busy = tab()

    # A permission prompt is a need again, and a distinguishable one.
    emit("Notification", "claude-notification-hook",
         message="Claude needs your permission to use Bash")
    assert option("@claude-state") == "approval"
    approval = tab()

    # An open question is also a need, told apart by its glyph.
    emit("Notification", "claude-notification-hook",
         message="Claude is waiting for your input")
    assert option("@claude-state") == "question"
    question = tab()

    # Finished is its own state: a window Claude just worked in is not a window
    # Claude was never in.
    emit("Stop", "claude-stop-hook")
    assert option("@claude-state") == "idle"
    idle = tab()
    assert idle != plain, "a finished Claude window must not read as an empty one"

    # Left alone long enough, a finished window is called out as dormant. The
    # sweep skips the focused window, so aim the client elsewhere first.
    private_tmux.call("select-window", "-t", "main:")
    private_tmux.call("set-option", "-w", "-t", window, "@claude-since",
                      str(int(time.time()) - sweep.DORMANT_AFTER - 1))
    sweep.main()
    assert option("@claude-state") == "dormant"
    dormant = tab()

    # Each class must render differently, or none of the above reaches the eye.
    rendered = {"plain": plain, "plan": plan, "busy": busy, "approval": approval,
                "question": question, "idle": idle, "dormant": dormant}
    assert len(set(rendered.values())) == len(rendered), rendered

    # Needs are the emphasised ones: bold, and sharing the hottest colour.
    for name in ("plan", "approval", "question"):
        assert "bold" in rendered[name] and "nobold" not in rendered[name], name
    for name in ("busy", "idle", "dormant"):
        assert "nobold" in rendered[name], name

    # Every part of the tab -- segment, text, and both powerline caps -- has to
    # come from the same state, or a half-wired format shows the wrong colours.
    for name, tab_state in (("plan", "plan"), ("busy", "tool"), ("approval", "approval"),
                            ("question", "question"), ("idle", "idle"),
                            ("dormant", "dormant")):
        _, bg, fg, _, glyph = state.STATES[tab_state]
        drawn = rendered[name]
        assert drawn.count("bg=%s" % bg) == 1, (name, "segment and its opening cap")
        assert drawn.count("fg=%s" % fg) == 1, (name, "text foreground")
        assert drawn.count("fg=%s" % bg) == 1, (name, "closing cap matches the segment")
        assert glyph in drawn, (name, "state glyph survives a colourless terminal")

    # The status bar rolls the same states up across every session, so a need in
    # a window you are not looking at still reaches you.
    state.apply(window, "approval")
    roll_up = capture(sweep.main)
    assert state.STATES["approval"][1] in roll_up, roll_up

    # Claude's state outranks tmux's own bell, which cannot say why it rang: the
    # notification hook above left a bell pending on this very window.
    assert option("window_bell_flag") == "1"
    assert state.STATES["approval"][1] in tab()

    # SessionEnd hands the tab back to tmux's own signals -- here, that pending
    # bell -- and once it is acknowledged, to a plain window.
    emit("SessionEnd", "claude-tmux-state-hook")
    assert option("@claude-state") == ""
    private_tmux.call("select-window", "-t", window)
    private_tmux.call("select-window", "-t", "main:")
    assert option("window_bell_flag") == "0"
    assert tab() == plain
