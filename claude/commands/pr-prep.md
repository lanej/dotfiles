---
description: "Prepare branch for pull request: review implementation, verify requirements, restructure commits into logical narrative, run tests, generate PR description"
argument-hint: [optional issue number]
tags:
  - git
  - github
  - pr
  - workflow
  - quality
---

# PR Prep - Prepare Branch for Pull Request

You are helping the user prepare their current git branch for a pull request by reviewing the implementation, verifying it meets requirements, and creating a clean, narrative commit history.

## Your Task

Prepare the current branch for PR by following these steps:

### 1. Understand the Context

**Identify the Issue/Requirement:**
- Check the branch name for issue references (e.g., `issue-1240-multipart-related`)
- Look for GitHub issue numbers in the branch name or recent commits
- If an issue number is found, use `gh issue view <number>` to read the requirements
- Ask the user what this branch is intended to accomplish if unclear

**Analyze Current State:**
- Run `git status` to see what's changed
- Run `git log --oneline origin/main..HEAD` to see existing commits (or appropriate base branch)
- Run `git diff origin/main...HEAD --stat` to understand scope of changes
- Identify all modified, added, and deleted files

### 2. Critical Review of Implementation

**Create a comprehensive review document** (`/tmp/implementation_review.md`) analyzing:

**What Was Built:**
- List all major components/features added
- Describe the technical approach taken
- Identify key files and their roles

**Verification Against Requirements:**
- Does the implementation meet all stated requirements?
- Are there any missing features or incomplete work?
- Does the API match what was requested (if applicable)?
- Are there any gaps or deviations from the issue?

**Code Quality Assessment:**
- Separation of concerns
- Test coverage
- Documentation quality
- Edge case handling
- Error handling approach

**Critical Analysis:**
- Identify strengths of the implementation
- Note any concerns (performance, correctness, maintainability)
- Highlight potential issues or trade-offs made
- Document any intentional design decisions (e.g., "accepting clone for API simplicity")

**Side Effects:**
- Identify any unintended changes to existing code
- Assess whether side effects are beneficial or problematic
- Determine if side effects should be in separate commits

**Missing Features:**
- List anything that's deliberately out of scope
- Note any features that should be in follow-up work

### 3. Test Verification

**Run the test suite:**
- Execute tests: `cargo test --quiet` (or appropriate test command for the project)
- Verify all tests pass
- Check for any warnings
- If tests fail, fix issues before proceeding

### 4. Design Commit Structure

**Create a logical commit narrative** that tells the story of the implementation:

**Principles:**
- Keep commit count low (typically 3-5 commits) but high enough to be followable
- Each commit should represent a logical, atomic change
- Commits should build on each other in a clear progression
- Each commit should compile and pass tests independently
- Group related changes together (don't split artificially)

**Common Patterns:**
1. **Foundation → Implementation → Tests**
   - Commit 1: Add core infrastructure/types/traits
   - Commit 2: Implement main functionality/code generation
   - Commit 3: Add comprehensive tests

2. **Layer by Layer**
   - Commit 1: Runtime/library support
   - Commit 2: Code generation
   - Commit 3: CLI/tooling integration
   - Commit 4: Tests and documentation

3. **Feature Decomposition**
   - Commit 1: Add feature A
   - Commit 2: Add feature B (depends on A)
   - Commit 3: Integration and tests

**Avoid:**
- "Fix typo" commits (squash into main commit)
- "WIP" or incremental development commits
- Mixing unrelated changes
- Commits that don't compile
- Commits with test failures

### 5. Clean Up Commit History

**Stage and commit changes** following the designed structure:

For each logical commit:
1. Stage only the files relevant to that commit: `git add <files>`
2. Use the git-commit-message-writer agent to generate a professional commit message
3. Ensure the message:
   - Uses conventional commit format (feat/fix/refactor/test/docs)
   - Has a clear, concise subject line (<50 chars)
   - Includes detailed body explaining what and why
   - References the issue number
   - Is written in professional, human style
4. Create the commit: `git commit -m "message"`
5. Verify the commit compiles: run build/test commands
6. Repeat for each commit

**If there are existing commits on the branch:**
- You may need to use `git reset --soft origin/main` (or base branch) to unstage all commits
- Then re-commit following the clean structure
- Be careful not to lose any work

### 6. Final Verification

**Verify the commit history:**
- Run `git log --oneline -<N>` to show the new commits
- Run `git log -<N> --format=fuller` to show full details
- Verify each commit message is clear and professional
- Run `cargo test --quiet` (or appropriate) to ensure everything still works
- Check `git status` to ensure working directory is clean

**Review with user:**
- Show the commit structure
- Explain the narrative and reasoning
- Get approval before pushing

### 7. Generate PR Description

Dispatch the **pull-request-writer agent**; it owns the PR description spec (review-oriented structure, links a teammate can open, no local paths, screenshots for visual changes). Brief it with:
- The base branch and the issue/ticket URL (from `$ARGUMENTS` or step 1)
- The verification you ran in the steps above and its results, plus the CI run URL once pushed
- For any user-visible change: the before/after screenshots you captured, or where they are hosted
- The output path `/tmp/pr_description.md` (a local handoff file only; never mention it in the PR)

Read the result before showing it. Send it back if it references anything the reviewer can't open, omits the why or the verification, or has an unresolved screenshot TODO you didn't surface to the user.

### 8. Push to Remote

**Only after user approval:**
```bash
git push origin <branch-name>
```

Show the user the description, then open the PR only on their approval with `gh-pr-create-from /tmp/pr_description.md` (add `--draft` while a screenshot TODO is open). Raw `gh pr create` is blocked by a hook.

## Usage

```
/pr-prep
```

Or with an issue number:
```
/pr-prep 1240
```

## Important Guidelines

- **Always read files before editing** - use Read tool before Edit tool
- **Use the git-commit-message-writer agent** for ALL commit messages
- **Use the pull-request-writer agent** for PR titles and descriptions
- **Verify each commit independently** - each should compile and pass tests
- **Keep the user informed** - explain your reasoning for the commit structure
- **Don't push without approval** - always get user confirmation first
- **Clean working directory** - ensure no uncommitted changes at the end

## Example Output Structure

For a feature implementation, you might create:

1. **feat(core): add Widget infrastructure**
   - Core types, traits, and interfaces
   - Foundation for the feature

2. **feat(codegen): generate Widget API**
   - Code generation logic
   - Builder patterns and method generation

3. **test(widget): add comprehensive Widget tests**
   - Test suite with multiple scenarios
   - Generated output validation

Each commit should tell part of the story, building toward the complete feature.

## Error Handling

- If tests fail, fix them before creating commits
- If there are merge conflicts, inform user and ask for guidance
- If unsure about commit structure, discuss options with user
- If issue requirements are unclear, ask user for clarification

## Notes

- This command works best for feature branches ready for review
- For bug fixes, you may need only 1-2 commits
- For large refactorings, you may need 5-7 commits
- Trust your judgment on what makes a clear narrative
- The goal is reviewability and understanding, not arbitrary commit counts
