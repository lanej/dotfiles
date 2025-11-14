---
description: Fix GitHub issue (lists issues if no number provided)
argument-hint: [optional-issue-number]
allowed-tools: Write, Read, LS, Glob, Grep, Bash(gh:*), Bash(git:*)
---

If no issue number is provided, first list open GitHub issues using 'gh issue list --limit 20 --json number,title,labels,updatedAt' and ask the user which issue they want to fix.

Once an issue number is available (either from $ARGUMENTS or user selection), analyze and fix the GitHub issue by following these steps:

# PLAN

1. Use 'gh issue view <issue-number>' to get the issue details
2. Understand the problem described in the issue
3. Ask clarifying questions if necessary
4. Understand the prior art for this issue
   - Search the scratchpads for previous thoughts related to the issue
   - Search PRs to see if you can find history on this issue
   - Search the codebase for relevant files
5. Think harder about how to break the issue down into a series of small, manageable tasks.
6. Document your plan in a new scratchpad
   - include the issue name in the filename
   - include a link to the issue in the scratchpad.

# REPRODUCE

- **Reproduce the issue first** before making any fixes
- Create a test case or reproduction script that demonstrates the bug
- Verify you can reliably reproduce the problem
- Document the reproduction steps in comments or the scratchpad
- This ensures you understand the issue and can verify your fix works

# CREATE

- Create a new branch for the issue
- Solve the issue in small, manageable steps, according to your plan.
- Commit your changes after each step.

# TEST

- **Ensure regression protection**: Write tests that would have caught this issue
- Use your reproduction case from the REPRODUCE step as the basis for regression tests
- Use puppeteer via MCP to test the changes if you have made changes to the UI and puppeteer is in your tools list.
- Write unit tests to describe the expected behavior of your code.
- Run the full test suite to ensure you haven't broken anything
- If the tests are failing, fix them
- Ensure that all tests are passing before moving on to the next step
- Verify your fix by running the reproduction steps - they should now pass

# OPEN PULL REQUEST

- Open a PR and request a review.

Remember to use the GitHub CLI ('gh') for all Github-related tasks.
