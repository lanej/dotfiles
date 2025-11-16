## Response Formatting (Claude's Output)
- **Markdown line breaks**: Consecutive lines REQUIRE blank lines between them to render separately (or use proper list syntax: `- `, `* `, numbered)
- **Terminal readability**: Ensure all output renders properly in markdown viewers

## Markdown File Standards (Editing Codebase Files)
- **Paragraph spacing**: Single line breaks between paragraphs (no extra blank lines)
- **Section separators**: Use headers, NOT `---` horizontal rules (except YAML frontmatter)
- **List formatting**: No blank lines between list items (except for multi-paragraph items)
- **Headers**: Do NOT number headers - use clean text (e.g., `## The Problem` not `## 2. The Problem`)

## Tool-Specific Skills

For comprehensive workflows and best practices, see `~/.claude/skills/`. Each skill has a `SKILL.md` file.

### Git - `~/.claude/skills/git/`
- Use git commit message writer agent for all commits
- NO AI attribution in commits (no "Generated with Claude Code" or "Co-Authored-By: Claude")

### Rust - `~/.claude/skills/rust/`
- Workflow: `cargo test --quiet` → `cargo check --quiet` → `cargo clippy`
- AVOID release builds; use `cargo check` to verify compilation, `cargo run` for iteration
- Auto-fix: `cargo clippy --fix --allow-dirty`

### Python - `~/.claude/skills/python/`
- Use `uv run` for executing scripts and commands
- AVOID pip; use `uv add`, `uv sync`, `uv run`

### Just - `~/.claude/skills/just/`
- PREFERRED command runner over Make
- Keep recipes simple (1-3 lines); delegate complex logic to scripts in `scripts/` directory

### jq - `~/.claude/skills/jq/`
- STRONGLY PREFERRED for ALL JSON operations
- Use instead of Python/Node.js scripts, grep, awk for JSON data

### Azure - `~/.claude/skills/az/`
- Authentication: Always `az login` and `az account set` before operations
- Output formats: `--output table` (review), `--output json` (scripting), `--output tsv` (parsing)

### Atlassian/Jira - `~/.claude/skills/acli/`
- Use `acli jira` for Jira operations
- Authentication: `acli jira auth login` before first use

### Other Skills
- `bigquery` - Use `bigquery` CLI (not `bq`)
- `gspace` - Google Workspace operations (Drive, Gmail, Docs, Sheets, Calendar)
- `phab` - Phabricator operations (tasks, revisions, diffs)
- `pkm` - Personal knowledge management
- `xlsx` - Excel file manipulation
- `xsv` - Fast CSV processing

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
- **TOML files** (Cargo.toml, pyproject.toml): Place comments on separate lines above config (NOT inline after values)

## Additional Tool Notes
- **Speckit**: Quote the short-name argument value when using `speckit.specify`
