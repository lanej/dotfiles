# Anthropic Skills Migration

This file documents the one-time migration of skills from https://github.com/anthropics/skills

## Migration Date
2026-01-17

## Skills Added

### Document Processing
- **pdf** - PDF manipulation: extract text/tables, create PDFs, merge/split, handle forms
- **docx** - Word document creation and editing
- **pptx** - PowerPoint presentation creation and editing
- **xlsx-python** - Spreadsheet creation with Python (openpyxl/xlsxwriter)
  - Note: Renamed from `xlsx` to avoid conflict with existing `xlsx` CLI skill
  - Use `xlsx` (CLI) for reading/analyzing existing spreadsheets
  - Use `xlsx-python` for creating/modifying spreadsheets programmatically

### Creative & Design
- **algorithmic-art** - Generative art and algorithmic design
- **canvas-design** - Canvas-based design work
- **frontend-design** - Frontend UI/UX design
- **theme-factory** - Theme creation and customization
- **slack-gif-creator** - Create GIFs for Slack

### Communication & Documentation
- **doc-coauthoring** - Collaborative document writing
- **internal-comms** - Internal communications writing
- **brand-guidelines** - Brand guideline adherence and creation

### Development Tools
- **mcp-builder** - MCP (Model Context Protocol) server building
- **skill-creator** - Create new Claude skills
- **web-artifacts-builder** - Build web artifacts
- **webapp-testing** - Web application testing

## Conflict Resolution

**xlsx conflict:**
- Your existing `xlsx` skill (CLI-based) preserved at: `claude/skills/xlsx/`
- Anthropic's xlsx skill (Python-based) renamed to: `claude/skills/xlsx-python/`
- Both are available and serve different purposes

## License Note

Some Anthropic skills include LICENSE.txt files with proprietary licenses. Review before distributing or modifying.

## Selective Versioning

Following the dotfiles selective versioning pattern:
- Skills are now in `~/.files/claude/skills/` (symlinked from `~/.claude/skills/`)
- Use `git add -f claude/skills/<skill-name>/` to version specific skills
- Experiment freely; only commit skills you want to keep long-term

## Next Steps

1. Review the new skills to see which ones are useful
2. Selectively add desired skills to version control
3. Remove unused skills if desired
4. Update skill descriptions as needed
