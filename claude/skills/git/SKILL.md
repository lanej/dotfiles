---
name: git
description: Git version control and GitHub CLI workflows for commits, branches, pull requests, and code reviews with professional commit message practices.
---

# Git and GitHub

Standard git and `gh` usage works as documented. This file covers the conventions to hold to and
the failure modes on this machine that have actually cost time.

## Commits

- **All commits go through the `git-commit-message-writer` agent** (or `/git:commit [context]`).
  Do not hand-write commit messages. `/git:worktree <branch>` creates a worktree with
  automatic naming.
- Format: Commitizen conventional, `<type>(<scope>): <subject>`, subject ≤ 50 chars.
- **No AI attribution.** Never emit `Generated with Claude Code` or `Co-Authored-By: Claude`.
- Atomic commits; the message explains *why*.
- **`Detected-By:` trailer** on any commit fixing a fault found after the code was written — the tier that caught it (`V0`–`V4`, see the `methodology` skill's Verification Rigor Tiers) or `user`. This is measurement, not attribution, and is unaffected by the no-AI-attribution rule above.
- `--amend` only when the user asked for it, or to fold in a pre-commit hook's own edits.

## Branch naming

`feature/`, `fix/`, `hotfix/`, `refactor/`, `docs/`, `test/` + a descriptive slug.

## Safety rules

1. Never force-push to `main`/`master` — warn instead.
2. Never `--no-verify` unless explicitly requested.
3. `--force-with-lease`, never bare `--force`.
4. Confirm authorship and push status before amending.
5. Destructive commands need user confirmation.

## Worktree gotchas

### `gh pr checkout` is not worktree-safe

It operates against the main git directory regardless of the shell's cwd. Run from inside a
worktree, it switches the **main** working directory's branch and overwrites files there.

Instead, from inside the worktree:

```bash
git fetch origin <branch>
git checkout -b fix/<name> origin/<branch>
```

### `core.hooksPath` is shared across all worktrees

It lives in the repo's shared `.git/config` as a single value. A sibling worktree running
`husky init` silently overwrites it repo-wide with a path relative to *its own* worktree. Every
other worktree's pre-commit hook then fires and does nothing — no error, the commit just lands as
if lint-staged never existed.

Per worktree needing isolated hooks:

```bash
git config extensions.worktreeConfig true
git config --worktree core.hooksPath <relative-path-to-hooks-dir>
```

Applies to any hooks manager that writes `core.hooksPath`.

## Diff and patch gotchas

### `git apply` "does not exist in index" → check `diff.noprefix`

This machine sets `diff.noprefix = true` globally in `~/.gitconfig` (confirm:
`git config --get diff.noprefix`). It applies to **every repo** and strips the `a/`/`b/` prefixes,
so headers read `--- projects/foo/bar.qmd` rather than `--- a/projects/foo/bar.qmd`. `git apply`
defaults to `-p1`, which then eats a real path segment and reports the file as missing even though
it is tracked at exactly that path.

**Fix**: pass `-p0` for any hand-crafted or sub-agent-generated diff on this machine —
`git apply --cached -p0 <patch>`. Check `diff.noprefix` first; this recurred across unrelated repos
because it wasn't written down the first time.

### `git commit -m "..." -- <pathspec>` stages the full working tree for those paths

It is not "commit what's staged, scoped to these paths" — it implicitly `git add`s the *current
working-tree content* of every listed path, regardless of what was staged. In a shared working tree
with unrelated uncommitted changes in the same files, that silently folds someone else's WIP into
your commit.

**Before any `git commit -- <pathspec>`**: stage explicitly (`git add -p`, or `git apply --cached
-p0` against an extracted patch), commit with a bare `git commit` against the index, and verify with
`git show --stat` before pushing. Recovery if it already landed: `git reset --soft HEAD^` (working
tree untouched), then hand-stage the intended hunks.
