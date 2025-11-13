# Claude Code Skills

This directory contains specialized skill files that enhance Claude Code's capabilities for specific tools, workflows, and domains.

## What are Skills?

Skills are detailed instruction sets that provide Claude Code with domain-specific expertise. When invoked, a skill expands its specialized knowledge and best practices, enabling Claude to work more effectively with particular tools, languages, or workflows.

Skills can be invoked using the Skill tool in Claude Code conversations, allowing for context-aware, expert-level assistance with complex tasks.

## Documentation

For more information about skills and how to use them, see the official Anthropic documentation:
- [Claude Code Skills Documentation](https://docs.claude.com/en/docs/claude-code/skills)
- [Claude Code Overview](https://docs.claude.com/en/docs/claude-code/overview)

## Skill Manifest

This directory contains the following skills:

### Development Tools

- **git.md** - Git and GitHub workflow expertise
  - Commit message formatting (Commitizen-style, no AI attribution)
  - Branch management and merge strategies
  - GitHub CLI (gh) operations for PRs, issues, and releases
  - Code review workflows

- **rust.md** - Rust and Cargo development
  - Build order: `cargo test --quiet` → `cargo build --quiet` → `cargo clippy`
  - Auto-fix clippy warnings with `--allow-dirty`
  - Timeout and background process management
  - Dependency management and build optimization

- **python.md** - Python development with uv
  - Use `uv run` for executing Python scripts
  - Project and dependency management
  - Virtual environment handling
  - Tool installation patterns

### Cloud and DevOps

- **az.md** - Azure CLI operations
  - Azure cloud resource management
  - Azure DevOps repos, pipelines, and work items
  - Output formats: `--output table/json/tsv`
  - Authentication workflows
  - VMs, storage, networking, AKS, Key Vault, monitoring

- **gspace.md** - Google Workspace operations
  - Google Drive, Gmail, Docs, Sheets, Calendar
  - Use `gspace` CLI for all operations
  - Output formats: `--json` for scripting, `--quiet` for minimal output
  - File operations, email management, document editing

### Project Management

- **acli.md** - Atlassian CLI (Jira)
  - Jira work item, project, sprint, and board management
  - JQL search patterns and bulk operations
  - Output formats: `--json`, `--csv`, `--web`
  - Work item CRUD, transitions, comments

- **phab.md** - Phabricator operations
  - Use `phab` CLI for tasks, revisions, diffs
  - Task management and code review workflows
  - Project operations and search patterns

### Data Processing

- **jq.md** - JSON processing and manipulation
  - **STRONGLY PREFERRED** for all JSON operations
  - Filtering, transformations, aggregations
  - Output modes: `-r` (raw), `-c` (compact), `-s` (slurp)
  - API response processing and log analysis

- **xsv.md** - CSV data processing
  - Fast CSV processing with `xsv`
  - Selection, filtering, statistics
  - Joining, sorting, performance optimization

- **xlsx.md** - Excel/spreadsheet operations
  - Use `xlsx` binary for reading/writing xlsx files
  - SQL-like filtering and cell editing
  - Export to CSV workflows

### Specialized Tools

- **lancer.md** - LanceDB vector database
  - Vector database operations and queries
  - Embedding management
  - Search and retrieval patterns

- **pkm.md** - Personal Knowledge Management
  - Note-taking and knowledge organization
  - Linking and cross-referencing
  - Search and retrieval workflows

## Usage in CLAUDE.md

Skills referenced in this directory are automatically available to Claude Code when working in this project. The global `~/.claude/CLAUDE.md` file references these skills in the "Tool-Specific Skills" section, making them available across all projects.

For comprehensive tool-specific workflows and best practices, always refer to these skill files rather than duplicating instructions in project-specific documentation.
