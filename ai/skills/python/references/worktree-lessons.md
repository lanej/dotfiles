# Worktree runtime verification

### Worktree + pytest
`cd` into the worktree before invoking `pytest` — never run it from the main repo root with paths pointing into the worktree. The main repo's `pyproject.toml` drives discovery/imports from there, not the worktree's edited files. Correct: `cd <worktree-path> && uv run pytest tests/...`. (detail: memory "feedback_worktree_pytest_verification")
