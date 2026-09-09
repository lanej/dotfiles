# Claude Agents

Sub-agents dispatched via the `Agent` tool. Each `.md` file carries YAML frontmatter with a `description` that determines when the agent is selected.

Every dispatch needs Context, Domain, Sub-problem, Success criteria, Constraints, and Output format — see `claude/CLAUDE.md` for the full briefing contract.

## Writing & Documentation

| Agent | Use case |
|-------|----------|
| **human-writer** | Any writing task — documents, emails, Slack messages, memos, READMEs |
| **document-summarizer** | Key points, main themes, or specific details from long documents |

## Code & Review

| Agent | Use case |
|-------|----------|
| **code-reviewer** | Code quality, security vulnerabilities, and best-practice review |
| **commit-message-generator** | Commitizen conventional-format commit messages |
| **pull-request-writer** | GitHub PR titles and descriptions |
| **pull-request-commentor** | GitHub PR comments and reviews |

## Issue Tracking

| Agent | Use case |
|-------|----------|
| **jira-ticket-writer** | Jira tasks, epics, bugs, and stories |
| **phabricator-ticket-writer** | Phabricator tickets, bug reports, feature requests |

## Coordination & Session Management

| Agent | Use case |
|-------|----------|
| **orchestrator** | Coordinate multi-phase projects by delegating to specialized subagents |
| **reflection** | Analyze a session transcript against CLAUDE.md and apply behavioral fixes |
| **tech-radar** | Maintain `docs/radar.md` — add, promote, demote, or retire entries |
| **todo** | Manage the todo list without triggering other hooks |

## Prompt Fragments (`prompts/`)

Shared system-prompt pieces composed into agent definitions rather than invoked directly:

| File | Purpose |
|------|---------|
| `continuous-phased.md` | Phased-execution loop for long-running agents |
| `orchestrator-system.md` | Base orchestrator system prompt |
| `plan-mode.md` | Plan-mode entry and exit discipline |

## Versioning

`claude/agents/` is selectively versioned, same pattern as commands — see the repo root `CLAUDE.md`. Experiment in `~/.claude/agents/` (symlinked here, gitignored), then force-add:

```bash
git add -f claude/agents/<name>.md
```

No AI attribution in anything the git and GitHub agents produce — commits, PR descriptions, or comments.
