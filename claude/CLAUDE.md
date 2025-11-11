## Response Formatting (Claude's Output)
- **Markdown line breaks**: Consecutive lines that aren't part of a markdown list REQUIRE blank lines between them to render separately
  - Use proper markdown list syntax (`- `, `* `, or numbered) for lists
  - OR use double newlines (blank lines) between non-list lines
  - Correct (proper list syntax):
    ```markdown
    - ✅ First feature - Description here
    - ✅ Second feature - Description here
    - ✅ Third feature - Description here
    ```
  - Correct (double newlines):
    ```markdown
    ✅ First feature - Description here

    ✅ Second feature - Description here

    ✅ Third feature - Description here
    ```
  - Incorrect (concatenates into one line):
    ```markdown
    ✅ First feature - Description here
    ✅ Second feature - Description here
    ✅ Third feature - Description here
    ```
- **Terminal readability**: Ensure all output renders properly in markdown viewers

## Markdown File Standards (Editing Codebase Files)
- **Paragraph spacing**: Use single line breaks between paragraphs - do NOT add extra blank lines
- **Section separators**: Do NOT use `---` horizontal rules as section separators - use headers instead
  - Exception: YAML frontmatter delimiters at top of file (required)
- **List formatting**: Do NOT add blank lines between list items
  - Exception: Items containing multiple paragraphs or sub-lists
  - Correct:
    ```markdown
    1. First item
    2. Second item
    3. Third item
    ```
  - Incorrect:
    ```markdown
    1. First item

    2. Second item
    ```
- **Headers**: Do NOT number markdown headers - use clean header text
  - Correct: `## The Problem`
  - Incorrect: `## 2. The Problem`

## Tool-Specific Skills

For comprehensive tool-specific workflows and best practices, see the skills in `~/.claude/skills/`:

### Git and GitHub - `~/.claude/skills/git.md`
- Use git commit message writer agent for all commits
- **Commit message format**: Professional, human-written style with NO AI attribution (no "Generated with Claude Code" or "Co-Authored-By: Claude")
- Use `gh` CLI to access GitHub repositories
- See skill for: branch workflows, PR management, GitHub API usage, commit strategies

### Rust/Cargo - `~/.claude/skills/rust.md`
- **Command execution order**: `cargo test --quiet` → `cargo build --quiet` → `cargo clippy`
- **Auto-fix clippy warnings**: Use `cargo clippy --fix --allow-dirty`
- **Handle timeouts**: Use `timeout: 120000` (2 min) or `timeout: 600000` (10 min)
- **Clean up background processes**: Use `pkill -f cargo` to prevent lock contention
- See skill for: clippy strategies, dependency management, build optimization, complete workflows

### Python/uv - `~/.claude/skills/python.md`
- **Primary command**: Use `uv run` for executing Python scripts and commands
- See skill for: project management, dependency handling, virtual environments, tool installation

### Excel/Spreadsheets - `~/.claude/skills/xlsx.md`
- Use `xlsx` binary to read/write/edit xlsx files and export to csv
- See skill for: viewing data, SQL-like filtering, cell editing, conversion workflows

## Node.js/JavaScript Development
- When working in a project, always check package.json first to understand available scripts
- If user specifies a script to run (e.g., "node validate.js"), use exactly what they specify
- Always run `npm install` before attempting to execute Node.js scripts in a new project
- Check for README files or documentation that might explain the project structure

## Error Resolution
- Read error messages carefully before attempting fixes
- **Always read files before editing**: Use Read tool before Edit tool (editing unread files will fail)
- **Clean up background processes**: Use `pkill -f <process-name>` to terminate stuck processes causing "resource busy" or lock errors
- For JSON validation errors, fix specific fields rather than rewriting entire files
- Use Edit tool for targeted fixes instead of Write tool for complete rewrites
- Preserve working parts of the solution while addressing specific issues

## Configuration File Best Practices
- **TOML files** (Cargo.toml, pyproject.toml): Avoid inline comments after values; place comments on separate lines above the configuration
  - Correct:
    ```toml
    # This is a comment
    key = "value"
    ```
  - Incorrect:
    ```toml
    key = "value"  # This may cause parsing errors
    ```

## Additional Tool Notes
- **Google Drive**: Use gdrive MCP to access docs.google.com and drive.google.com links
- **Speckit**: Quote the short-name argument value when using `speckit.specify`
