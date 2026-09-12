"""One regression detector for resolving the current tmux Claude session."""
import os


def test_resolves_the_panes_session_in_a_project_with_dots(
        load_script, private_tmux, tmp_path, monkeypatch, capsys):
    app = load_script("claude-session-resolve")
    monkeypatch.setattr(app.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("PWD", "/workspace/project.with.dots")
    project = tmp_path / ".claude/projects/-workspace-project-with-dots"
    project.mkdir(parents=True)
    transcript = project / "current-session.jsonl"
    transcript.write_text("{}\n")
    newer = project / "another-session.jsonl"
    newer.write_text("{}\n")
    os.utime(transcript, (1, 1))
    os.utime(newer, (2, 2))
    private_tmux.call("set-option", "-p", "-t", private_tmux.pane,
                      "@claude-session-id", "current-session")

    app.main()

    assert capsys.readouterr().out.splitlines() == [
        "SESSION_ID=current-session", f"TRANSCRIPT_PATH={transcript}",
    ]
