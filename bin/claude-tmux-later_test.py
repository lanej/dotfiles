"""One live regression detector for idle Claude window cleanup."""
import io
import json
from pathlib import Path
import shlex
import shutil
import time


ROOT = Path(__file__).resolve().parent.parent


def test_idle_session_moves_to_later_then_closes_with_resume_history(
        load_script, private_tmux, monkeypatch):
    app = load_script("claude-tmux-later")
    folder = private_tmux.folder
    tmux = app.Tmux(private_tmux.socket)
    native = folder / "claude"
    # A disposable native process exercises actual foreground ownership checks.
    shutil.copyfile(shutil.which("sleep"), native)
    native.chmod(0o755)
    pane = private_tmux.call("new-window", "-d", "-t", "main:", "-P", "-F",
                             "#{pane_id}", f"exec {shlex.quote(str(native))} 300")
    pid = int(private_tmux.call("display-message", "-p", "-t", pane, "#{pane_pid}"))
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        process = app.process(pid)
        row = next(r for r in tmux.panes() if r["pane_id"] == pane)
        owner = {"pid": pid, "started": process["started"] if process else ""}
        if process and app.foreground_owner(row, {"owner": owner}):
            break
        time.sleep(0.02)
    else:
        raise AssertionError("Disposable Claude process did not own its foreground")

    cfg = json.loads((ROOT / "claude/tmux-later.json").read_text())
    hooks = json.loads((ROOT / ".claude/settings.json").read_text())["hooks"]
    clock = [200000]
    monkeypatch.setenv("TMUX_PANE", pane)
    monkeypatch.setattr(app, "connection", lambda: (tmux, "fixture", folder))
    monkeypatch.setattr(app, "settings", lambda: cfg)
    monkeypatch.setattr(app, "claude_ancestor", lambda: owner)
    monkeypatch.setattr(app, "ensure_daemon", lambda *args: None)
    monkeypatch.setattr(app.time, "time", lambda: clock[0])

    def emit(kind, **fields):
        # Deliver the fixture event through the cleanup hook configured for it.
        event = dict(hook_event_name=kind, session_id="conversation-1", **fields)
        for entry in hooks.get(kind, []):
            for hook in entry["hooks"]:
                command = shlex.split(hook.get("command", ""))
                if command and Path(command[0]).name == "claude-tmux-later" and command[1:] == ["hook"]:
                    monkeypatch.setattr(app.sys, "stdin", io.StringIO(json.dumps(event)))
                    app.hook()

    emit("SessionStart", source="startup", cwd="/project")
    emit("PostToolUse", tool_name="Bash")
    clock[0] += cfg["close_seconds"]
    app.sweep(tmux, folder, cfg)
    assert next(r for r in tmux.panes() if r["pane_id"] == pane)["session_name"] == "main"

    emit("Stop", background_tasks=[], session_crons=[])
    stopped_at = clock[0]
    clock[0] = stopped_at + cfg["archive_seconds"]
    app.sweep(tmux, folder, cfg)
    moved = next(r for r in tmux.panes() if r["pane_id"] == pane)
    assert (moved["session_name"], moved["window_id"]) == ("later", row["window_id"])

    clock[0] = stopped_at + cfg["close_seconds"]
    app.sweep(tmux, folder, cfg)
    assert pane not in {r["pane_id"] for r in tmux.panes()}
    assert private_tmux.pane in {r["pane_id"] for r in tmux.panes()}
    assert "conversation-1" in (folder / "history.jsonl").read_text()
