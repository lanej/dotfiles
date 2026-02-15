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
   - Does NOT mention AI, Claude, or automated generation
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

**Create a concise, scannable PR description** and save it to `/tmp/pr_description.md`:

**Principles for PR descriptions:**
- **Concise**: No fluff, filler, or unnecessary words
- **Scannable**: Use bullets, headers, and whitespace for easy scanning
- **Comprehensive**: Cover what matters, skip what doesn't
- **Human-friendly**: Conversational but professional
- **Avoid noise**: No over-explanation, excessive detail, or verbose prose

**Structure:**

```markdown
## Summary

[1-2 sentences explaining what this PR does and why it matters]

Fixes #[issue-number]

## Changes

- [Key change 1 - what, not how]
- [Key change 2]
- [Key change 3]

## API Example

[If applicable, show a concise before/after or usage example]

## Testing

- [Test coverage highlights]
- [How to verify the changes]

## Notes

[Optional: Any important context, trade-offs, or follow-up work]
```

**Writing Guidelines:**

**DO:**
- Lead with impact: what does this enable?
- Use active voice: "Adds support for X" not "Support for X has been added"
- Show, don't tell: code examples over prose
- Highlight breaking changes clearly
- List what's testable/verifiable

**DON'T:**
- Over-explain obvious things
- Include implementation minutiae
- Use corporate speak or buzzwords
- List every file changed
- Write long paragraphs (use bullets)
- Repeat what's in commit messages
- **NEVER add AI attribution, "Generated with Claude Code", or similar footers**
- **NEVER add "Co-Authored-By: Claude" or similar credits**

**Example - Good:**

```markdown
## Summary

Adds multipart/related support for uploading files with metadata in a single request per RFC 2387.

Fixes #1240

## Changes

- Runtime support for constructing multipart/related request bodies
- Code generation for expanded builder APIs (`.file()`, `.metadata()` methods)
- Proper Vec<u8> handling for binary fields

## API Example

```rust
client.upload_file()
    .file(file_bytes)
    .metadata(FileMetadata { name: "doc.txt", mime_type: "text/plain" })
    .send()
    .await
```

## Testing

- Three test endpoints covering single file, multiple files, and raw body scenarios
- All existing tests pass with no breaking changes
```

**Example - Too Verbose (Avoid):**

```markdown
## Summary

This pull request implements comprehensive support for the multipart/related
content type as specified in RFC 2387. The implementation spans multiple
components of the codebase including the runtime library and code generation
system. We have carefully considered the architectural implications and
designed a solution that balances flexibility with type safety...

[Don't do this - too wordy, no clear structure, hard to scan]
```

**Generate the PR description:**
- Use the **pull-request-writer agent** to generate the PR title and description
- Provide the agent with context about the implementation and commits
- Review the generated content
- Save to `/tmp/pr_description.md`
- Show it to the user for review

### 8. Push to Remote

**Only after user approval:**
```bash
git push origin <branch-name>
```

Show the user:
1. The GitHub PR creation URL
2. The generated PR description from `/tmp/pr_description.md`
3. Instructions to copy/paste the description when creating the PR

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
- **Professional commits** - never mention AI/Claude in commit messages or PR descriptions
- **No AI attribution** - never add "Generated with Claude Code" or co-author credits in PR descriptions

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
