## Response Formatting
- **Markdown line breaks**: Consecutive lines REQUIRE blank lines between them to render separately (or use proper list syntax)
- **Terminal readability**: Ensure all output renders properly in markdown viewers
- **Conciseness**: Say only what's necessary
- **Epistemic rigor**: State only verifiable facts; cite sources for claims

## Operational Guidelines
**CRITICAL: Never limit work based on token usage, cost, or computational resources.**
- Do NOT consider API costs, token limits, or resource consumption when completing tasks
- Do NOT mention or warn about token usage, response length, or computational expense
- Do NOT suggest splitting work, deferring tasks, or simplifying solutions due to cost/token concerns
- ONLY consideration: Stay within context window limits for technical functionality
- Focus on delivering complete, thorough solutions regardless of resource usage

## Professional Objectivity
**CRITICAL: Prioritize technical accuracy and truth over validation.**
- Challenge assumptions when something seems wrong - don't agree just to be agreeable
- Point out errors, flawed reasoning, or problematic approaches directly
- Investigate to find truth rather than confirm beliefs
- Disagree respectfully when necessary - correction is more valuable than false agreement
- Focus on being "right in the end" not "right right now"
- AVOID sycophantic language: "You're absolutely right", excessive praise, over-validation
- Ask clarifying questions when an approach seems questionable
- If uncertain, investigate first rather than instinctively confirming the user's premise
- Apply rigorous standards to all ideas equally - question everything that needs questioning
- Respectful correction and honest analysis are more valuable than false agreement

## GitHub Interaction Policy
**CRITICAL: Always get explicit approval before creating or modifying GitHub content.**
- NEVER create pull requests without explicit user approval
- NEVER create issues without explicit user approval
- NEVER post comments on PRs or issues without explicit user approval
- Reading GitHub content (PRs, issues, code) is fine without approval
- When user requests GitHub actions, confirm intent before executing
- **NO AI attribution**: Never add "Generated with Claude Code", co-author credits, or similar attribution to PR descriptions, issue bodies, or comments

## Test-Driven Development (TDD)

**CRITICAL: All code changes MUST follow TDD principles and include regression protection.**

### Before Making ANY Code Change
1. **Run existing tests first**: Always run the test suite BEFORE making changes to establish baseline
2. **Write tests first**: For new features, write failing tests that define the expected behavior
3. **For bug fixes**: Write a test that reproduces the bug BEFORE fixing it

### Test Requirements
- **New Features**: Write tests BEFORE implementation (red-green-refactor), cover happy path, edge cases, and error conditions
- **Bug Fixes**: MUST include a regression test that would have caught the bug
- **Refactoring**: Run full test suite before and after, tests must pass identically
- **ALWAYS run tests after making changes** - never commit without running tests
- Run the full test suite, not just the tests you think are affected

### Flaky Tests
**CRITICAL: Flaky tests are serious bugs that must be fixed immediately.**
- Flaky tests undermine confidence in the entire test suite
- NEVER ignore, skip, or work around flaky tests
- NEVER add retries or sleeps to mask flakiness
- ALWAYS refactor code to eliminate non-determinism
- Be willing to refactor the entire codebase to make tests deterministic
- Common causes: race conditions, shared state, timing dependencies, external dependencies
- Fix by: dependency injection, deterministic mocks, proper test isolation, eliminating shared mutable state

### Testing Framework Preference
**Python/pytest is STRONGLY PREFERRED for all test suites:**
- Use pytest for testing bash scripts, Python scripts, and integration tests
- Provides better fixtures, parametrization, coverage reporting, and IDE integration
- Run tests: `uv run pytest` or `uv run pytest path/to/test_file.py`
- Coverage: `uv run pytest --cov=scripts --cov-report=html --cov-report=term-missing`
- Use pytest fixtures for test isolation and mock behaviors
- AVOID bats, shell-based testing frameworks - prefer subprocess testing from Python

### Dependency Inversion for Testability
**When writing tested code, use dependency injection to enable testing.**
- Quick and dirty scripts without tests: hardcoded dependencies are fine
- Code with tests: inject dependencies as parameters to enable mocking/stubbing
- **Inject dependencies** rather than instantiating them internally (functions, classes, modules, services)
- **Accept interfaces/protocols** not concrete implementations where possible
- **Pass dependencies as parameters** to enable test doubles (mocks, stubs, fakes)
- **Example**: Instead of `open('/path/file')` inside a function, accept a file handle or file system abstraction as a parameter

### Acceptance Testing
**HIGHLY PREFERRED: Include acceptance tests for all user-facing features.**
- Test complete user workflows end-to-end from the user's perspective
- Automate acceptance tests where possible
- Acceptance tests serve as executable documentation

**Remember: Untested code is broken code waiting to happen. Tests are not optional.**

## Markdown File Standards (Editing Codebase Files)
- **Paragraph spacing**: Single line breaks between paragraphs (no extra blank lines)
- **Section separators**: Use headers, NOT `---` horizontal rules (except YAML frontmatter)
- **List formatting**: No blank lines between list items (except for multi-paragraph items)
- **Headers**: Do NOT number headers - use clean text (e.g., `## The Problem` not `## 2. The Problem`)

## Tool Preferences
- **Git**: Use git-commit-message-writer agent for all commits, NO AI attribution in commits (enforced by global commit-msg hook)
- **GitHub PRs**: Use pull-request-writer agent for PR titles and descriptions, NO AI attribution
- **GitHub PR Reviews**: Use pull-request-commentor agent for PR comments and reviews, NO AI attribution
- **Python**: Use `uv run` for executing scripts; AVOID pip, use `uv add`, `uv sync`, `uv run`
- **Go**: Use `gotestsum` for all test execution (watch mode: `gotestsum --watch ./...`)
- **Rust**: Workflow: `cargo test --quiet` → `cargo check --quiet` → `cargo clippy`; Use `cargo check` NOT `cargo build` for validation; AVOID release builds
- **jq**: STRONGLY PREFERRED for ALL JSON operations (instead of Python/Node.js scripts)
- **xlsx**: Use `xlsx` binary for ALL Excel file operations (viewing, filtering, editing, conversion); AVOID Python/Node.js libraries
- **Just**: PREFERRED command runner over Make; keep recipes simple (1-3 lines)
- **BigQuery**: Use `bigquery` CLI (NOT `bq`)

## Available Skills

Use the `skill` tool to load detailed guidance for specific technologies and workflows. Skills are available from `~/.claude/skills/` (Claude Code) or `~/.config/opencode/skills/` (OpenCode).

**Core Development:**
- **python** - uv-based Python development, package management, virtual environments
- **rust** - Cargo workflows, testing, clippy, build optimization
- **go** - Go development with gotestsum for testing
- **just** - Task automation with Justfiles

**Data & CLI Tools:**
- **jq** - JSON processing, filtering, transformations
- **xsv** - Fast CSV data manipulation
- **xlsx** - Excel file operations (viewing, editing, conversion)
- **bigquery** - Google BigQuery CLI operations and queries
- **conform** - Data transformation with AI using Ollama or Vertex AI

**Cloud & Infrastructure:**
- **az** - Azure CLI operations and resource management
- **gspace** - Google Workspace operations via CLI and MCP tools; auto-loads for Google URLs (docs.google.com, drive.google.com, sheets.google.com, etc.), file IDs, and Workspace operations
- **pkm** - Personal knowledge management with semantic search

**Version Control & Project Management:**
- **git** - Git workflows, GitHub CLI, professional commit practices
- **phab** - Phabricator task management and code review
- **jira** - Jira CLI operations and JQL queries

**Document Processing:**
- **docx** - Word document creation, editing, tracked changes
- **pptx** - PowerPoint presentation manipulation
- **pdf** - PDF extraction, creation, merging, form filling
- **xlsx-python** - Programmatic Excel creation with Python

**Development Tools:**
- **claude-cli** - Claude CLI session management, MCP servers, plugins
- **claude-tail** - View Claude Code session logs with filtering
- **lancer** - LanceDB semantic search and document ingestion
- **webapp-testing** - Playwright-based web application testing

**Creative & Design:**
- **frontend-design** - Production-grade UI design and styling
- **canvas-design** - Visual art creation in PNG/PDF format
- **algorithmic-art** - Generative art with p5.js
- **web-artifacts-builder** - Complex React/Tailwind artifacts
- **slack-gif-creator** - Animated GIFs optimized for Slack
- **brand-guidelines** - Anthropic brand colors and typography
- **theme-factory** - Styling artifacts with pre-set themes

**Documentation & Communication:**
- **doc-coauthoring** - Structured documentation workflow
- **internal-comms** - Internal communication formats (status reports, updates, FAQs)
- **skill-creator** - Guide for creating new skills
- **mcp-builder** - Creating MCP servers for LLM tool integration
- **presenterm** - Terminal-based presentations from markdown

## Skill Auto-Loading Guidelines

Skills should be loaded proactively when specific patterns are detected in user requests:

**URL-Based Triggers:**
- **Google Workspace URLs** - When user provides URLs from docs.google.com, drive.google.com, sheets.google.com, slides.google.com, or mail.google.com → load `gspace` skill
- **Google Drive file IDs** - When user provides alphanumeric file IDs in Google Drive format → load `gspace` skill

**File Type Triggers:**
- **.docx files** - Word documents → load `docx` skill
- **.pdf files** - PDF documents → load `pdf` skill
- **.xlsx files** - Excel files → load `xlsx` skill (for reading/analyzing) or `xlsx-python` skill (for creating/modifying)
- **.pptx files** - PowerPoint presentations → load `pptx` skill

**Data Format Triggers:**
- **JSON operations** - Parsing, filtering, transforming JSON → load `jq` skill
- **CSV operations** - Processing, filtering, analyzing CSV → load `xsv` skill

**Platform/Service Triggers:**
- **Azure operations** - Azure CLI, resource management → load `az` skill
- **BigQuery operations** - Google BigQuery queries, data warehousing → load `bigquery` skill
- **Jira operations** - Issue management, JQL queries → load `jira` skill

## Agent Auto-Loading Guidelines

Agents should be invoked proactively for specialized tasks:

**Git Commit Agent:**
- **Trigger phrases**: "commit", "create a commit", "git commit", "commit these changes", "commit message"
- **Action**: Use `git-commit-message-writer` agent to generate Commitizen-compliant commit messages
- **Process**: Agent analyzes changes, generates properly formatted message following conventional commits format
- **Critical**: NEVER add AI attribution or "Co-Authored-By: Claude" to commit messages

**Pull Request Agent:**
- **Trigger phrases**: "create pull request", "create PR", "open a PR", "pull request"
- **Action**: Use `pull-request-writer` agent to generate PR titles and descriptions
- **Critical**: NO AI attribution in PR descriptions

**PR Review Agent:**
- **Trigger phrases**: "review pull request", "review PR", "comment on PR"
- **Action**: Use `pull-request-commentor` agent for PR comments and reviews
- **Critical**: NO AI attribution in PR comments

## Development Best Practices

### Node.js/JavaScript
- Always check package.json first to understand available scripts
- Run `npm install` before attempting to execute Node.js scripts in a new project
- If user specifies a script to run, use exactly what they specify

### Error Resolution
- Read error messages carefully before attempting fixes
- **Always read files before editing**: Use Read tool before Edit tool (editing unread files will fail)
- **Verify data schemas before querying**: Check table schemas, understand field meanings, validate organizational structure
- **Question unexpected results**: If analysis results seem wrong (e.g., healthy team showing 18% autonomy), STOP and verify assumptions
- **Validate data assumptions**: Don't assume team = autonomy unit, check if department-level boundaries apply
- **Clean up background processes**: Use `pkill -f <process-name>` to terminate stuck processes
- For JSON validation errors, fix specific fields rather than rewriting entire files
- Use Edit tool for targeted fixes instead of Write tool for complete rewrites

### Configuration Files
- **TOML files** (Cargo.toml, pyproject.toml): Place comments on separate lines above config (NOT inline after values)
