---
description: Create a git commit using the commit message writer agent
argument-hint: [optional context or focus]
tags:
  - git
  - commit
  - workflow
---

# Git Commit - Create Professional Commits

You are helping the user create a professional git commit using the git-commit-message-writer agent.

## Your Task

Guide the user through creating a well-crafted commit by following these steps:

### 1. Understand Current State

**Check what will be committed:**
- Run `git status` to see staged and unstaged changes
- Run `git diff --cached` to see staged changes (what will be committed)
- Run `git diff` to see unstaged changes (what won't be committed unless staged)
- If nothing is staged, ask if the user wants to stage all changes or specific files

**Review recent commits for context:**
- Run `git log --oneline -5` to see recent commit style
- This helps match the repository's commit message conventions

### 2. Determine Focus (if provided)

If the user provided an argument via $ARGUMENTS:
- Use it as context for the commit message (e.g., "focus on the authentication changes")
- Otherwise, include all staged changes

### 3. Stage Files (if needed)

If no files are staged:
- Ask the user what to stage, OR
- Stage all changes with `git add .` if that seems appropriate
- **DO NOT commit** files that likely contain secrets (.env, credentials.json, etc.)

### 4. Generate Commit Message

**Use the Task tool to invoke the git-commit-message-writer agent:**
- Provide it with the staged changes from `git diff --cached`
- Provide it with recent commit history for style matching
- Provide any user context from $ARGUMENTS
- The agent will generate a professional commit message

### 5. Create the Commit

**Execute the commit:**
```bash
git commit -m "$(cat <<'EOF'
[message from agent]
EOF
)"
```

**Verify success:**
- Run `git status` to confirm the commit was created
- Run `git log -1 --oneline` to show the new commit

## Important Notes

- **NO AI attribution**: Never include "Generated with Claude Code" or "Co-Authored-By: Claude"
- **Professional style**: Follow Commitizen format (type(scope): message)
- **Match project conventions**: Use recent commits as style guide
- **Clear and concise**: Focus on "why" not just "what"

## Examples

```bash
# Simple commit (all staged changes)
/git:commit

# Commit with specific focus
/git:commit "authentication changes"

# Commit specific files
/git:commit "update config files"
```

## BEGIN COMMAND

You are creating a git commit.

Optional user context: $ARGUMENTS

Steps:
1. Run `git status` and `git diff --cached` to understand what will be committed
2. If nothing staged, ask what to stage or stage appropriate files
3. Use the Task tool with subagent_type='git-commit-message-writer' to generate the commit message
4. Create the commit using the generated message
5. Verify with `git status` and `git log -1`

Be efficient and guide the user through any decisions needed.
