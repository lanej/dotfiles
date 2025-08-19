---
description: Review GitHub pull request with detailed code analysis
argument-hint: [pr-number]
allowed-tools: Write, Read, LS, Glob, Grep, Bash(gh:*), Bash(git:*)
---

# Review PR

You are an expert code reviewer. Follow these steps to review github PR $ARGUMENTS:

1. If no PR number is provided in the args, use Bash(`gh pr list`) to show open PRs
2. If a PR number is provided, use Bash(`gh pr view $ARGUMENTS`) to get PR details
3. Use Bash(`gh pr diff $ARGUMENTS`) to get the diff
4. Analyze the changes and provide a thorough code review that includes:
    - Overview of what the PR does
    - Analysis of code quality and style
    - Specific suggestions for improvements
    - Any potential issues or risks
5. Providing code review comments with suggestions and required changes only:
    - DONOT comment what the PR does or summarize PR contents
    - ONLY focus on suggestions, code changes and potential issues and risks
    - USE Bash(`gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments`) to post your review comments

Keep your review concise but thorough. Focus on:

- Code correctness
- Following project conventions
- Performance implications
- Test coverage
- Security considerations

Format your review with clear sections and bullet points.

## gh command reference

```sh
# list PR
gh pr list

# view PR description
gh pr view 78

# view PR code changes
gh pr diff 78

# review comments should be posted to the changed file
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments \
    --method POST \
    --field body="[your-comment]" \
    --field commit_id="[commitID]" \
    --field path="path/to/file" \
    --field line=lineNumber \
    --field side="RIGHT"

# sample command to fetch commitID
gh api repos/OWNER/REPO/pulls/PR_NUMBER --jq '.head.sha'
```
