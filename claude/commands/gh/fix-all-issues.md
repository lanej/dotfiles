# Fix All Open Issues

Find all open GitHub issues without associated PRs, create git worktrees for each, work on them in parallel, and auto-merge passing PRs.

## Workflow

1. **Discovery Phase**
   - Use `gh issue list --state open --json number,title,url` to get all open issues
   - For each issue, check if a PR exists using `gh pr list --search "fixes #<issue-number>" --json number`
   - Filter to issues without PRs (max 10)

2. **Setup Phase**
   - Get repository name: Extract from remote URL or current directory name
   - For each issue (up to 10):
     - Create worktree from main: `git worktree add -b fix/issue-{number} ../{repo_name}-fix-issue-{number} origin/main`
     - Use lowercase repo name with dashes (e.g., `gspace-fix-issue-123`)
     - Record worktree path and issue details

3. **Parallel Execution Phase**
   - Launch Task agents in parallel (one per issue) with:
     - Agent type: `general-purpose`
     - Working directory set to the worktree path
     - Instructions to:
       - Read the issue details from GitHub
       - Implement the fix
       - Run tests to verify the fix works
       - Commit changes using git-commit-message-writer agent
       - Push branch to origin
       - Create PR with `gh pr create --title "Fix #{number}: {title}" --body "Fixes #{number}"`
       - Wait for CI checks to pass using `gh pr checks`
       - **If checks pass: immediately auto-merge** with `gh pr merge --auto --squash`
       - **If merged: close issue and clean up worktree**
       - Report back: success/failure status

4. **Monitoring Phase**
   - Wait for all parallel tasks to complete
   - Collect results from each agent
   - Report summary of all tasks (merged vs. needs attention)

5. **Cleanup**
   - Report which issues/PRs need manual attention (tests failed, implementation incomplete, etc.)
   - Keep worktrees for failed tasks to allow manual review

## Implementation

### Step 0: Get Repository Name

```bash
# Get repository name from git toplevel directory
# Convert to lowercase and replace spaces with dashes
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
```

### Step 1: Discover Issues

```bash
# Get all open issues
ISSUES=$(gh issue list --state open --json number,title,url --limit 100)

# For each issue, check if PR exists
# Filter to those without PRs
```

### Step 2: Create Worktrees

```bash
# Get repository name from remote URL or directory
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

# Create worktree for each issue (max 10), branching from main
for issue_number in "${ISSUE_NUMBERS[@]}"; do
  git worktree add -b "fix/issue-${issue_number}" "../${REPO_NAME}-fix-issue-${issue_number}" "origin/main"
done
```

### Step 3: Launch Parallel Tasks

Use TodoWrite to create a task list tracking each issue.

For each issue, launch a Task agent with:
- `subagent_type: "general-purpose"`
- Working directory: the worktree path
- Detailed instructions including issue number, title, and acceptance criteria

### Step 4: Process Results

After all agents complete:
- Parse each agent's response for success/failure
- Auto-merge passing PRs
- Report status summary

### Step 5: Report Summary

```bash
# Report results from all agents
# List successfully merged issues
# List issues that need manual attention
# Remind about preserved worktrees for failed tasks
```

Note: Worktree cleanup happens immediately after each successful merge within each agent's execution, not in a batch at the end.

## Safety Considerations

- **Max 10 issues**: Prevents overwhelming the system
- **Separate worktrees**: Isolates work to prevent conflicts
- **Immediate auto-merge on pass**: Each task merges independently when ready
- **Preserve failing worktrees**: Allows manual investigation
- **Atomic operations**: Each issue is completely independent

## Error Handling

- If worktree creation fails: skip that issue, continue with others
- If agent fails: mark as failed, preserve worktree
- If PR creation fails: preserve worktree for manual PR creation
- If tests fail: do not merge, report for manual review

## Expected Output

```
Found 8 open issues without PRs:
- #123: Fix login validation bug
- #124: Add dark mode support
- #125: Update dependencies
- #126: Fix memory leak in dashboard
- #127: Improve error messages
- #128: Add API rate limiting
- #129: Fix mobile responsiveness
- #130: Update documentation

Creating worktrees...
✓ Created gspace-fix-issue-123
✓ Created gspace-fix-issue-124
...

Launching parallel fixes (8 agents)...
[Agents work independently and merge when ready]

✓ #123: PR #145 created, checks passed, merged and cleaned up
✓ #127: PR #148 created, checks passed, merged and cleaned up
✓ #124: PR #146 created, checks passed, merged and cleaned up
✗ #125: PR #147 created, tests failing - preserved for manual review
✓ #126: PR #149 created, checks passed, merged and cleaned up
✓ #129: PR #150 created, checks passed, merged and cleaned up
✗ #128: Implementation incomplete - preserved for manual review
✓ #130: PR #151 created, checks passed, merged and cleaned up

Summary: 6 issues fixed and merged, 2 need manual review
Preserved worktrees: gspace-fix-issue-125, gspace-fix-issue-128
```

## BEGIN COMMAND

You are tasked with fixing all open GitHub issues that don't have associated PRs.

Follow this process:

1. **Get repository name** from git remote or directory (convert to lowercase, preserve dashes)
2. **Discover issues without PRs** (max 10)
3. **Create git worktrees** for each issue:
   - Branch name: `fix/issue-{number}`
   - Directory name: `{repo_name}-fix-issue-{number}` (e.g., `gspace-fix-issue-123`)
   - Branch from: `origin/main`
4. **Launch Task agents in parallel** to work on each issue independently
5. **Each agent auto-merges and cleans up** as soon as its PR passes checks (no waiting)
6. **Report** final summary of merged vs. failed tasks

Use TodoWrite to track progress through these phases.

Each parallel Task agent should:
- Work in its assigned worktree directory
- Analyze the GitHub issue
- Implement the fix
- Run tests to verify
- Commit with proper message (using git-commit-message-writer agent)
- Push and create PR
- Monitor CI checks
- **If passing: immediately auto-merge, close issue, and remove worktree**
- **If failing: preserve worktree for manual review**
- Report status back

**Important:** Each agent merges and cleans up independently as soon as its PR passes. Don't wait for other tasks to complete.

Start by checking what open issues exist without PRs.
