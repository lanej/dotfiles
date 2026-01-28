---
description: "Review staged changes for code quality before committing: delegates to sub-agent to check for minimal changes, no duplication, correctness, and test coverage"
argument-hint: [optional review focus]
model: sonnet
tags:
  - git
  - code-review
  - quality
  - testing
---

# Git Review & Commit - Code Review Before Commit

**CRITICAL**: Delegates review to a sub-agent to protect main context window.

You are helping the user review their staged changes before committing.

## Your Task

Perform a code quality review by delegating to a specialized agent, then optionally create a commit.

### 1. Check What Will Be Reviewed

**Gather context (but don't read all the diffs yourself - delegate that):**
```bash
# Get basic info about changes
git status --short
git diff --cached --stat

# Recent commits for context
git log --oneline -3
```

**DO NOT read full diffs yourself** - this consumes your context. You'll delegate that to the review agent.

### 2. Delegate to Code Reviewer Agent

**Use Task tool to spawn the code-reviewer agent:**

The code-reviewer agent is a specialized agent (in ~/.claude/agents/) that performs comprehensive code reviews.

```bash
# Invoke the agent via Task tool
Task(
  subagent_type="general-purpose",
  description="Review staged changes",
  prompt="Use the code-reviewer agent to review the staged git changes.

Run git diff --cached to see all changes, then perform a code review checking:
- Minimal changes (focused, no scope creep)
- No duplication (DRY principle)
- Directionally correct (sensible approach, no obvious bugs)
- Test coverage (>80%, edge cases covered)
- Security issues
- Performance concerns

User focus: $ARGUMENTS

Provide structured output with:
- Overall assessment
- Strengths
- Concerns (prioritized)
- Blocking issues
- Metrics
- Checklist status
"
)
```

**Alternative**: Directly reference the code-reviewer agent:
Since the code-reviewer agent exists in ~/.claude/agents/, Claude will automatically use it when appropriate for code review tasks.

### 3. Present Review Results

Once the agent completes:
- Show the review summary to the user
- Highlight any blocking issues
- Present concerns and suggestions

### 4. Ask About Next Steps

Based on review results:

**If no blocking issues:**
```
The review found no blocking issues. Would you like to:
1. Proceed with commit
2. Address suggestions first
3. Cancel
```

**If blocking issues found:**
```
⚠️ Review found blocking issues that should be addressed before committing.

Would you like to:
1. Address issues first
2. See detailed review
3. Commit anyway (not recommended)
```

### 5. Proceed with Commit (if approved)

If user wants to commit:
- Use the existing /git:commit workflow
- Invoke git-commit-message-writer agent for message
- Create the commit

## Review Criteria

The delegated agent checks for:

### Minimal Changes
- Changes are focused on stated goal
- No unrelated refactoring
- No formatting-only changes mixed with logic
- Scope creep indicators

### No Duplication
- Similar code patterns that could be DRY'd
- Copy-pasted functions with slight variations
- Repeated logic that should be extracted

### Directionally Correct
- Implementation approach makes sense
- No obvious bugs or logic errors
- Error handling present where needed
- Edge cases considered

### Test Coverage
- New functionality has tests
- Existing tests updated for changes
- Tests cover edge cases
- Tests actually test the changes

## Usage Examples

```bash
# Basic review
/git:review-commit

# Review with specific focus
/git:review-commit "focus on the authentication logic"

# Review specific aspect
/git:review-commit "check test coverage carefully"
```

## Important Notes

- **Delegates to agent**: Keeps main context clean
- **Optional workflow**: Use when you want review, use `/git:commit` when you don't
- **Blocking vs. suggestions**: Agent distinguishes between must-fix and nice-to-have
- **No AI attribution**: Commits still use standard message format

## When to Use This vs. /git:commit

**Use `/git:review-commit` when:**
- Significant new functionality
- Complex logic changes
- Uncertain about approach
- Want quality check before committing
- Working on critical code paths

**Use `/git:commit` when:**
- Simple, obvious changes (typo fixes, docs)
- Already reviewed changes
- Quick iterations
- Trust the changes are good

## BEGIN COMMAND

You are reviewing staged changes before committing.

Optional user context: $ARGUMENTS

Steps:
1. Get basic info with `git status --short` and `git diff --cached --stat`
2. **DELEGATE** full review to Task tool with general-purpose agent
3. Present review results to user
4. Ask user how to proceed (commit, address issues, cancel)
5. If committing, use `/git:commit` workflow

**CRITICAL**: Do NOT read full diffs yourself. Delegate to agent to protect context.
