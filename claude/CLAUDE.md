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

For comprehensive tool-specific workflows and best practices, see the skills in `~/.claude/skills/`. Each skill is in its own directory with a `SKILL.md` file.

### Git and GitHub - `~/.claude/skills/git/`
- Use git commit message writer agent for all commits
- **Commit message format**: Professional, human-written style with NO AI attribution (no "Generated with Claude Code" or "Co-Authored-By: Claude")
- Use `gh` CLI to access GitHub repositories
- See skill for: branch workflows, PR management, GitHub API usage, commit strategies

### Rust/Cargo - `~/.claude/skills/rust/`
- **Command execution order**: `cargo test --quiet` → `cargo check --quiet` → `cargo clippy`
- **AVOID release builds**: Use `cargo check` to verify compilation, `cargo run` for iterative development
- **Auto-fix clippy warnings**: Use `cargo clippy --fix --allow-dirty`
- **Handle timeouts**: Use `timeout: 120000` (2 min) for check/test/debug builds
- **Clean up background processes**: Use `pkill -f cargo` to prevent lock contention
- See skill for: check-first workflow, clippy strategies, dependency management, complete workflows

### Python/uv - `~/.claude/skills/python/`
- **Primary command**: Use `uv run` for executing Python scripts and commands
- See skill for: project management, dependency handling, virtual environments, tool installation

### Excel/Spreadsheets - `~/.claude/skills/xlsx/`
- Use `xlsx` binary to read/write/edit xlsx files and export to csv
- See skill for: viewing data, SQL-like filtering, cell editing, conversion workflows

### CSV Processing - `~/.claude/skills/xsv/`
- Use `xsv` for fast CSV data processing and analysis
- See skill for: selection, filtering, statistics, joining, sorting, performance optimization

### Phabricator - `~/.claude/skills/phab/`
- Use `phab` CLI for Phabricator operations (tasks, revisions, diffs)
- See skill for: task management, code review workflow, project operations, search patterns

### Google Workspace - `~/.claude/skills/gspace/`
- Use `gspace` CLI for Google Workspace operations (Drive, Gmail, Docs, Sheets, Calendar)
- **Output formats**: Use `--json` for scripting, `--quiet` for minimal output
- See skill for: file operations, email management, document editing, calendar events, search queries

### Azure CLI - `~/.claude/skills/az/`
- Use `az` CLI for Azure cloud and Azure DevOps operations
- **Output formats**: Use `--output table` for human review, `--output json` for scripting, `--output tsv` for parsing
- **Authentication**: Always run `az login` and `az account set` before operations
- See skill for: resource management, Azure DevOps repos/pipelines, VMs, storage, networking, AKS, Key Vault, monitoring

### JSON Processing - `~/.claude/skills/jq/`
- **STRONGLY PREFERRED** for ALL JSON formatting, parsing, manipulation, and analysis
- Use `jq` instead of Python/Node.js scripts, grep, awk, or other text processing for JSON data
- **Common patterns**: Pretty-print (`jq '.'`), filter (`jq '.[] | select(.key == "value")'`), map (`jq 'map(.field)'`)
- **Output modes**: `-r` for raw strings, `-c` for compact, `-s` for slurp (merge files)
- See skill for: filtering, transformations, aggregations, API response processing, log analysis, advanced patterns

### Atlassian CLI (Jira) - `~/.claude/skills/acli/`
- Use `acli jira` for Jira work item, project, sprint, and board management
- **Output formats**: Use `--json` for scripting, `--csv` for export, `--web` to open in browser
- **Authentication**: Always run `acli jira auth login` before first use
- **Bulk operations**: Test JQL queries with `--count` first, use `--yes` to skip confirmations
- See skill for: JQL search patterns, work item CRUD operations, transitions, comments, project management, complete workflows

### BigQuery - `~/.claude/skills/bigquery/`
- Use `bigquery` CLI for Google BigQuery data warehouse operations
- **Query execution**: Run SQL queries with `bigquery query`, use `--dry-run` to estimate costs
- **Data management**: Create datasets/tables, load data, export results
- **MCP server**: Semantic search and natural language query interface via `bigquery mcp stdio`
- **LSP integration**: SQL language server for editor support via `bigquery lsp stdio`
- See skill for: query operations, dataset/table management, schema operations, job control, cost optimization, partitioning/clustering

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
