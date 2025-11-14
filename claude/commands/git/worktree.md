---
description: Create a git worktree with automatic naming
argument-hint: <branch-name>
allowed-tools: Bash(git:*)
---

Create a git worktree with consistent naming based on the repository and branch.

## Workflow

1. **Get repository name**
   - Extract from git toplevel directory
   - Convert to lowercase, preserve dashes, replace spaces with dashes

2. **Parse branch name**
   - Use the provided branch name from $ARGUMENTS
   - Sanitize for filesystem (replace slashes with dashes)

3. **Create worktree**
   - Directory name: `../{repo_name}-{sanitized_branch_name}`
   - Branch name: `{branch_name}` (as provided)
   - Branch from: `origin/main` (or current branch if you prefer)
   - Command: `git worktree add -b {branch_name} ../{repo_name}-{sanitized_branch_name} origin/main`

4. **Confirm creation**
   - Show the worktree path
   - Provide instructions on how to navigate to it
   - Show how to remove it when done: `git worktree remove ../{repo_name}-{sanitized_branch_name}`

## Examples

```bash
# For branch "feature/dark-mode" in repository "gspace"
/git:worktree feature/dark-mode
# Creates:
#   - Directory: ../gspace-feature-dark-mode
#   - Branch: feature/dark-mode
#   - Based on: origin/main
```

```bash
# For branch "fix/login-bug" in repository "my-app"
/git:worktree fix/login-bug
# Creates:
#   - Directory: ../my-app-fix-login-bug
#   - Branch: fix/login-bug
#   - Based on: origin/main
```

## Usage

```bash
/git:worktree <branch-name>
```

## Cleanup

When done with the worktree:
```bash
git worktree remove ../repo-name-branch-name
```

Or list all worktrees:
```bash
git worktree list
```

## BEGIN COMMAND

You are creating a git worktree for branch: $ARGUMENTS

Steps:
1. Get repository name: `basename "$(git rev-parse --show-toplevel)" | tr '[:upper:]' '[:lower:]' | tr ' ' '-'`
2. Sanitize branch name for directory: replace slashes with dashes
3. Create worktree: `git worktree add -b "$ARGUMENTS" ../{repo_name}-{sanitized_branch_name} origin/main`
4. Report the worktree path and how to navigate to it
5. Provide cleanup command for when they're done

Be concise and just execute the commands.
