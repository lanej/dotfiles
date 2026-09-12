"""One regression detector for Claude's tmux window naming."""
import io
import json


def test_stop_names_the_window_from_the_session_directory(
        load_script, private_tmux, tmp_path, monkeypatch):
    app = load_script("claude-autoname-hook")
    monkeypatch.setattr(app.Path, "home", lambda: tmp_path)
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(json.dumps({"cwd": "/workspace/shipping-api"}) + "\n")
    monkeypatch.setattr(app.sys, "stdin", io.StringIO(json.dumps({
        "session_id": "session-1", "transcript_path": str(transcript),
    })))

    app.main()

    assert private_tmux.call("display-message", "-p", "-t", private_tmux.pane,
                             "#{window_name}") == "✻ shipping-api"
    assert (tmp_path / ".claude/session-names/session-1").read_text() == "shipping-api"
