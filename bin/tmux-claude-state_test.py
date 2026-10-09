"""One live regression detector for the shared Claude/Codex window-status feature.

Drives a window through the states a real session produces -- needs you, busy,
finished, forgotten -- through the actual hooks, and asserts the tab tmux draws
from rc/tmux.conf tells them apart.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import time
import pytest

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
    home = private_tmux.folder / "home"
    home.mkdir()
    (home / ".files").symlink_to(ROOT)
    # Broker source/installation now belongs to its independent project.
    source = Path(os.environ.get("AGENT_STATUS_SOURCE", str(Path.home() / "src/agent-status-broker")))
    binary = Path(os.environ.get("AGENT_STATUS_BIN", str(
        Path.home() / ".local/lib/agent-status/agent-status-broker")))
    if (source / "go.mod").is_file():
        monkeypatch.delenv("AGENT_STATUS_BIN", raising=False)
        go = shutil.which("go")
        assert go, "Go is required to build the standalone broker checkout"
        monkeypatch.setenv("GOCACHE", subprocess.check_output(
            [go, "env", "GOCACHE"], text=True).strip())
        monkeypatch.setenv("AGENT_STATUS_SOURCE", str(source))
    elif binary.is_file():
        monkeypatch.setenv("AGENT_STATUS_BIN", str(binary))
    elif os.environ.get("REQUIRE_BROKER_TESTS") == "1":
        pytest.fail("Install the standalone agent-status-broker before running its tmux integration")
    else:
        pytest.skip("Standalone broker unavailable; its own repository checks installation and tmux")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("AGENT_STATUS_INSTALL_FLAGS", "--no-start")
    fake_bin = home / "bin"
    fake_bin.mkdir()
    clients = fake_bin / "clients"
    clients.mkdir()

    def client_command(provider):
        # A passive copy supplies a live named process, without making a model
        # request or treating a retained title as evidence of liveness.
        shutil.copy2(broker_binary, clients / provider)
        return "exec " + shlex.join([
            str(clients / provider), "serve", "--socket",
            str(clients / provider) + "-socket/broker.sock", "--renderer", "/bin/cat"])

    # Keep desktop delivery observable without notifying the developer's OS.
    notification = fake_bin / "osascript"
    notification.write_text(f"#!{sys.executable}\n"
                            "import os\nfrom pathlib import Path\n"
                            "with Path(os.environ['HOME'], 'desktop-notification').open('a') as f:\n"
                            "    f.write('delivered\\n')\n")
    notification.chmod(0o755)
    (fake_bin / "notify-send").symlink_to(notification)
    tmux_adapter = fake_bin / "tmux"
    tmux_adapter.write_text(
        '#!/bin/sh\nif [ -z "${TMUX:-}" ]; then\n'
        '  if [ -e "$HOME/tmux-offline" ]; then\n'
        '    printf "attempt\\n" >> "$HOME/tmux-attempts"\n'
        '    printf "transient tmux failure\\n" >&2\n'
        '  else\n    printf "no server running\\n" >&2\n  fi\n  exit 1\nfi\n'
        f'exec {shlex.quote(shutil.which("tmux"))} "$@"\n')
    tmux_adapter.chmod(0o755)
    subprocess.run(["make", "agent-status-broker"], cwd=ROOT, check=True,
                   capture_output=True, text=True, timeout=60)
    broker_socket = private_tmux.folder / "broker/broker.sock"
    monkeypatch.setenv("AGENT_STATUS_SOCKET", str(broker_socket))
    broker_binary = home / ".local/lib/agent-status/agent-status-broker"
    broker = subprocess.Popen(
        [str(broker_binary), "serve", "--socket", str(broker_socket)],
        env=dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}"),
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    def stop_broker():
        broker.terminate()
        broker.wait(timeout=5)
        broker.stderr.close()
    private_tmux.cleanup.append(stop_broker)
    deadline = time.monotonic() + 5
    while not broker_socket.exists():
        assert broker.poll() is None, broker.stderr.read() if broker.poll() is not None else ""
        assert time.monotonic() < deadline
        time.sleep(0.02)

    def wait_for_broker():
        deadline = time.monotonic() + 5
        while True:
            stats = json.loads(subprocess.check_output(
                [str(broker_binary), "status"], text=True))
            if not stats["pending"]:
                return
            assert time.monotonic() < deadline, json.dumps(stats)
            time.sleep(0.02)

    hooks = json.loads((ROOT / ".claude/settings.json").read_text())["hooks"]
    window = private_tmux.call("new-window", "-d", "-t", "main:", "-n", "project",
                               "-P", "-F", "#{window_id}", client_command("claude"))
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
    border_settings = "\n".join(
        line for line in (ROOT / "rc/tmux.conf").read_text().splitlines()
        if re.match(r"set\s+-g (?:@codex-pane-label|pane-border-format) ", line))
    conf.write_text(tab_format() + "\n" + border_settings + "\n")
    private_tmux.call("source-file", str(conf))

    def emit(event_name, hook_name, **fields):
        """Deliver an event through whichever hook settings.json wires to it."""
        event = dict(hook_event_name=event_name, session_id=private_tmux.folder.name, **fields)
        commands = [h["command"] for entry in hooks.get(event_name, [])
                    for h in entry["hooks"]]
        script = next(c for c in commands if hook_name in c)
        subprocess.run([str(BIN / hook_name)], input=json.dumps(event), text=True,
                       capture_output=True, timeout=10, check=True)
        wait_for_broker()
        return script

    def tab():
        return private_tmux.call("display-message", "-p", "-t", window,
                                 "#{E:window-status-format}")

    def option(name, target=window):
        return private_tmux.call("display-message", "-p", "-t", target, "#{%s}" % name)

    plain = tab()
    assert option("@claude-state") == "", "a fresh window starts un-Claude-ed"
    emit("SessionStart", "claude-session-start-hook", cwd="/workspace/project", source="startup")

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

    # Install Codex's hooks beside another integration, then drive a real
    # approval/question/finished workflow through the installed commands.
    codex_home = home / ".codex"
    codex_home.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    config_file = codex_home / "config.toml"
    config_file.write_text('model = "kept"\n[tui]\nterminal_title = [\n'
                           '  "project", # prior preference\n]\n'
                           'status_line = ["model-name"]\n')
    hook_file = codex_home / "hooks.json"
    hook_file.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{
        "type": "command", "command": 'printf kept >> "$CODEX_HOME/custom-hook"',
    }]}]}}))
    subprocess.run(["make", "codex-tmux"], cwd=ROOT, check=True,
                   capture_output=True, text=True, timeout=60)
    installed = hook_file.read_text()
    installed_config = config_file.read_text()
    subprocess.run(["make", "codex-tmux"], cwd=ROOT, check=True,
                   capture_output=True, text=True, timeout=60)
    assert hook_file.read_text() == installed
    assert config_file.read_text() == installed_config
    assert 'model = "kept"' in installed_config
    assert 'status_line = ["model-name"]' in installed_config
    codex_hooks = json.loads(installed)["hooks"]
    codex_window = private_tmux.call("new-window", "-d", "-t", "main:", "-n", "codex",
                                     "-P", "-F", "#{window_id}", client_command("codex"))
    codex_pane = private_tmux.call("display-message", "-p", "-t", codex_window, "#{pane_id}")
    private_tmux.call("set-option", "-w", "-t", codex_window, "automatic-rename", "off")
    codex_session = "01a11437-3d7c-7053-b6d2-da78e9281cd6"
    fake_codex = fake_bin / "codex"
    fake_codex.write_text(f"""#!{sys.executable}
import json, os, sys, tomllib
from pathlib import Path
args = sys.argv[1:]
Path(os.environ["CODEX_TEST_ARGS"]).write_text(json.dumps(args))
config = tomllib.loads((Path(os.environ["CODEX_HOME"]) / "config.toml").read_text())
items = config["tui"]["terminal_title"]
if "app-name" in items and "thread-id" in items:
    title = "codex | " + os.environ["CODEX_TEST_SESSION"][:29] + "... | Ready | project"
    with open(os.environ["CODEX_TEST_TTY"], "wb", buffering=0) as tty:
        tty.write(("\\033]0;" + title + "\\007").encode())
""")
    fake_codex.chmod(0o755)
    cli_args = home / "codex-args.json"
    launch_env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}",
                      TMUX_PANE=codex_pane, CODEX_TEST_ARGS=str(cli_args),
                      CODEX_TEST_SESSION=codex_session,
                      CODEX_TEST_TTY=option("pane_tty", codex_pane))
    # Exercise the installed shell entrypoint. The fake CLI models only native
    # title publication; it makes no model request and starts no daemon.
    subprocess.run(["bash", "-c", '. "$HOME/.files/sh/alias"; codex resume --last'],
                   env=launch_env, check=True, capture_output=True, text=True)
    assert "--no-daemon" not in json.loads(cli_args.read_text())
    assert "-c" not in json.loads(cli_args.read_text())
    deadline = time.monotonic() + 5
    while codex_session[:29] not in option("pane_title", codex_pane):
        assert time.monotonic() < deadline, "the client did not publish its thread title"
        time.sleep(0.02)
    border = private_tmux.call("display-message", "-p", "-t", codex_pane,
                              "#{E:pane-border-format}")
    assert " ○ · project" in border
    assert "codex" not in border and codex_session[:29] not in border
    # Every hook now receives the shared daemon's stale originating pane.
    monkeypatch.setenv("TMUX_PANE", pane)

    def codex_tab():
        return private_tmux.call("display-message", "-p", "-t", codex_window,
                                 "#{E:window-status-format}")

    def emit_codex(event_name, **fields):
        event = dict(hook_event_name=event_name, session_id=codex_session, **fields)
        for group in codex_hooks.get(event_name, []):
            for handler in group["hooks"]:
                subprocess.run(["sh", "-c", handler["command"]], input=json.dumps(event),
                               text=True, capture_output=True, check=True, timeout=10)
        wait_for_broker()

    codex_plain = codex_tab()
    emit_codex("SessionStart", source="startup")
    emit_codex("UserPromptSubmit")
    assert option("@claude-state", codex_window) == "thinking"
    assert f" {state.STATES['thinking'][4]} · project" in private_tmux.call(
        "display-message", "-p", "-t", codex_pane, "#{E:pane-border-format}")
    assert option("@claude-state", window) != "thinking"
    emit_codex("PreToolUse", tool_name="Bash", tool_use_id="command-1")
    assert option("@claude-class", codex_window) == "activity"
    assert state.STATES["tool"][1] in codex_tab()
    assert (codex_home / "custom-hook").read_text() == "kept"

    emit_codex("PermissionRequest", tool_name="Bash")
    assert option("@claude-state", codex_window) == "approval"
    assert state.STATES["approval"][1] in codex_tab() and "▲" in codex_tab()
    # A Codex need outranks a busy Claude window, both in the summary and when
    # jumping from the user's shell. The hook must target its background pane.
    monkeypatch.setenv("TMUX_PANE", pane)
    emit("SessionStart", "claude-session-start-hook", cwd="/workspace/project", source="resume")
    emit("UserPromptSubmit", "claude-tmux-state-hook")
    emit("PreToolUse", "claude-tmux-state-hook", tool_name="Bash")
    roll_up = capture(sweep.main)
    assert "▲1" in roll_up and "●1" in roll_up
    private_tmux.call("select-window", "-t", "main:keep")
    monkeypatch.setenv("TMUX_PANE", private_tmux.pane)
    subprocess.run([str(BIN / "tmux-quickswitch-alert")], capture_output=True,
                   check=True, timeout=10)
    assert private_tmux.call("display-message", "-p", "#{window_id}") == codex_window
    private_tmux.call("select-window", "-t", "main:keep")
    monkeypatch.setenv("TMUX_PANE", codex_pane)

    emit_codex("PostToolUse", tool_name="Bash", tool_use_id="command-1")
    assert option("@claude-class", codex_window) == "activity"
    emit_codex("PreToolUse", tool_name="request_user_input", tool_use_id="question-1")
    assert option("@claude-state", codex_window) == "question"
    assert "?" in codex_tab()
    emit_codex("PostToolUse", tool_name="request_user_input", tool_use_id="question-1")
    assert option("@claude-state", codex_window) == "thinking"
    emit_codex("Stop", permission_mode="plan")
    assert option("@claude-state", codex_window) == "plan"
    assert "▣" in codex_tab()
    emit_codex("UserPromptSubmit")
    emit_codex("Stop", permission_mode="default")
    assert option("@claude-state", codex_window) == "idle"
    private_tmux.call("set-option", "-w", "-t", codex_window, "@claude-since",
                      str(int(time.time()) - sweep.DORMANT_AFTER - 1))
    sweep.main()
    assert option("@claude-state", codex_window) == "dormant"
    assert "·" in codex_tab()
    emit_codex("SessionEnd")
    assert option("@claude-state", codex_window) == ""

    # Reusing the pane for a different thread must reject delayed old events,
    # even when the last recorded owner still belongs to the previous thread.
    codex_session = "01a1143c-c598-79f2-ae9e-717ed97a274b"
    launch_env["CODEX_TEST_SESSION"] = codex_session
    subprocess.run(["bash", "-c", '. "$HOME/.files/sh/alias"; codex'],
                   env=launch_env, check=True, capture_output=True, text=True)
    deadline = time.monotonic() + 5
    while codex_session[:29] not in option("pane_title", codex_pane):
        assert time.monotonic() < deadline
        time.sleep(0.02)
    emit_codex("UserPromptSubmit")
    assert option("@claude-state", codex_window) == "thinking"
    emit_codex("Stop", agent_id="subagent", agent_type="worker")
    assert option("@claude-state", codex_window) == "thinking"
    old_session = codex_session
    codex_session = "01a11437-3d7c-7053-b6d2-da78e9281cd6"
    emit_codex("SessionEnd")
    assert option("@claude-state", codex_window) == "thinking"
    codex_session = old_session

    # A same-thread title refresh must preserve a valid approval event.
    # Snapshot interleavings exercise the actual renderer installed from the
    # standalone binary, including its embedded palette.
    from importlib.machinery import SourceFileLoader
    hook = SourceFileLoader("agent_status_renderer", str(
        home / ".local/lib/agent-status/tmux-render.py")).load_module()
    real_tmux = hook.state.tmux
    refreshing = True

    def refresh_after_snapshot(*args):
        nonlocal refreshing
        result = real_tmux(*args)
        if refreshing and args[:2] == ("list-panes", "-a"):
            refreshing = False
            private_tmux.call("select-pane", "-t", codex_pane, "-T",
                              f"! codex | {codex_session[:29]}... | Waiting | project")
        return result

    monkeypatch.setattr(hook.state, "tmux", refresh_after_snapshot)
    assert hook.render_event(
        dict(hook_event_name="PermissionRequest", session_id=codex_session,
             tool_name="exec_command", tool_use_id="approval-title-refresh")) == 0
    assert option("@claude-state", codex_window) == "approval"
    assert f" {state.STATES['approval'][4]} · project" in private_tmux.call(
        "display-message", "-p", "-t", codex_pane, "#{E:pane-border-format}")
    emit_codex("UserPromptSubmit")
    assert option("@claude-state", codex_window) == "thinking"

    # The same thread can start a new turn without changing its visible state.
    # An old Stop must not mistake that new thinking state for its own snapshot.
    submitting = True

    def submit_after_snapshot(*args):
        nonlocal submitting
        result = real_tmux(*args)
        if submitting and args[:2] == ("list-panes", "-a"):
            submitting = False
            hook.render_event(dict(hook_event_name="UserPromptSubmit", session_id=codex_session))
        return result

    monkeypatch.setattr(hook.state, "tmux", submit_after_snapshot)
    assert hook.render_event(dict(hook_event_name="Stop", session_id=codex_session)) == 0
    assert option("@claude-state", codex_window) == "thinking"

    # Interleave a client thread switch after an old hook reads pane identity.
    # The real tmux server must reject that old hook's state/ownership mutation.
    switching = True
    ending_session = codex_session

    def switch_after_snapshot(*args):
        nonlocal switching, codex_session
        result = real_tmux(*args)
        if switching and args[:2] == ("list-panes", "-a"):
            switching = False
            codex_session = "01a1143f-eae6-7d10-9267-c87553d379e1"
            private_tmux.call("select-pane", "-t", codex_pane, "-T",
                              f"codex | {codex_session[:29]}... | Ready | project")
            hook.render_event(dict(hook_event_name="UserPromptSubmit", session_id=codex_session))
        return result

    monkeypatch.setattr(hook.state, "tmux", switch_after_snapshot)
    assert hook.render_event(dict(hook_event_name="SessionEnd", session_id=ending_session)) == 0
    assert option("@claude-state", codex_window) == "thinking"
    assert option("@codex-session-id", codex_pane) == codex_session

    # A replacement application must not inherit native ownership as a
    # supposedly legacy binding for another delayed event.
    private_tmux.call("select-pane", "-t", codex_pane, "-T", "claude")
    hook.render_event(dict(hook_event_name="SessionEnd", session_id=codex_session))
    assert option("@claude-state", codex_window) == "thinking"
    private_tmux.call("select-pane", "-t", codex_pane, "-T",
                      f"codex | {codex_session[:29]}... | Ready | project")
    hook.render_event(dict(hook_event_name="SessionEnd", session_id=codex_session))
    assert option("@claude-state", codex_window) == ""
    private_tmux.call("select-window", "-t", codex_window)
    private_tmux.call("select-window", "-t", "main:keep")
    assert codex_tab() == codex_plain
    assert option("@claude-state") == "tool", "Codex must leave Claude's window alone"

    # The same active pane can move to a different window between tools.
    private_tmux.call("join-pane", "-d", "-s", pane, "-t", codex_pane)
    monkeypatch.setenv("TMUX_PANE", pane)
    emit("PreToolUse", "claude-tmux-state-hook", tool_name="Bash")
    assert option("@claude-state", codex_window) == "tool"

    # Their two panes now share a palette. An older Claude Stop delivered after
    # a newer Codex prompt must not win, whether in one batch or on a retry.
    timestamp = time.time_ns()
    subprocess.run([str(broker_binary), "send", "--timestamp", str(timestamp + 2)],
                   input=json.dumps(dict(hook_event_name="UserPromptSubmit", session_id=codex_session)),
                   text=True, check=True)
    subprocess.run([str(broker_binary), "send", "--provider", "claude",
                    "--timestamp", str(timestamp + 1)],
                   input=json.dumps(dict(hook_event_name="Stop", session_id=private_tmux.folder.name)),
                   text=True, check=True)
    wait_for_broker()
    assert option("@claude-state", codex_window) == "thinking"
    assert option("@claude-session-id", pane) == private_tmux.folder.name
    assert option("@codex-session-id", codex_pane) == codex_session

    # Stop's desktop delivery also works from an ordinary terminal, while
    # subprocess delivery to the desktop is represented by the marker above.
    desktop_env = {k: v for k, v in os.environ.items() if k not in ("TMUX", "TMUX_PANE")}
    offline = home / "tmux-offline"
    offline.touch()
    # A failed plain-terminal Codex route must not make the successful desktop
    # sink retry a notification already delivered.
    subprocess.run([str(BIN / "codex-tmux-state-hook")],
                   input=json.dumps(dict(hook_event_name="UserPromptSubmit", session_id="outside-codex")),
                   text=True, env=desktop_env, check=True)
    stop = json.dumps(dict(hook_event_name="Stop", session_id="desktop-session"))
    subprocess.run([str(broker_binary), "send", "--provider", "claude",
                    "--timestamp", str(time.time_ns() - 20_000_000_000)],
                   input=stop, text=True, env=desktop_env, check=True)
    subprocess.run([str(BIN / "claude-stop-hook")], input=stop, text=True,
                   env=desktop_env, check=True)
    deadline = time.monotonic() + 5
    while not (home / "desktop-notification").exists():
        assert time.monotonic() < deadline
        time.sleep(0.02)
    attempts = home / "tmux-attempts"
    while not attempts.exists() or len(attempts.read_text().splitlines()) < 2:
        assert time.monotonic() < deadline
        time.sleep(0.02)
    offline.unlink()
    wait_for_broker()
    assert (home / "desktop-notification").read_text().splitlines() == ["delivered"]
