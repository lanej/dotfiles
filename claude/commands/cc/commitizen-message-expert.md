---
description: Generate professional git commit messages following Commitizen conventional format with proper line length limits
argument-hint: [changes description]
allowed-tools: [Bash, Read, Grep]
---

# Commitizen Message Expert

Generate properly formatted commit messages that follow the Commitizen conventional format: `<type>(<scope>): <subject>`. Ensures strict adherence to line length limits and formatting standards for professional version control history.

## Usage:

`/cc:commitizen-message-expert [changes description]`

## Process:

### 1. Change Analysis
- Analyze the described changes to determine the appropriate commit type
- Identify the most relevant scope based on affected components
- Review git status and diff if needed to understand full context

### 2. Message Generation
- Apply Commitizen conventional format: `<type>(<scope>): <subject>`
- Use imperative mood and present tense
- Ensure subject line stays under 50 characters
- Focus on what the change does, not how it was implemented

### 3. Quality Validation
- Verify proper formatting and line length limits
- Ensure professional tone without AI/automation mentions
- Validate against conventional commit standards

### 4. Output Delivery
- Provide the exact commit message ready for use
- Include brief explanation of type/scope choices if helpful

## Valid Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system or dependency changes
- `ci`: CI/CD configuration changes
- `chore`: Maintenance tasks

## Scope Guidelines:
- Use lowercase, be specific but concise
- Match project structure when possible (e.g., 'auth', 'api', 'cli', 'tmux')
- Omit scope if change affects multiple areas broadly

## Subject Line Rules:
- Use imperative mood ('add', 'fix', 'update', not 'added', 'fixed', 'updated')
- Start with lowercase letter, no period at end
- Be descriptive but concise, under 50 characters
- Avoid generic terms when more specific verbs apply

## Examples:

**Input:** "Added new user authentication middleware with JWT token validation"
**Output:** `feat(auth): add JWT token validation middleware`

**Input:** "Fixed bug where the login form wasn't validating email addresses properly"
**Output:** `fix(auth): validate email format in login form`

**Input:** "Updated README with new installation instructions"
**Output:** `docs(readme): update installation instructions`

**Input:** "Refactored database connection logic to use connection pooling"
**Output:** `refactor(db): implement connection pooling`

## Notes:

- Never mention AI, Claude, or automated generation in commit messages
- Commit messages should appear as if written by a human developer
- If the description is unclear, ask for clarification to ensure accuracy
- Focus on the business value or technical improvement, not implementation details
- Maintain consistency with existing project commit message patterns when possible