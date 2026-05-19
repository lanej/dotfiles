# Agents

Sub-agents invoked via the `Agent` tool or `@agent-name` syntax. Each has a focused role, constrained tool set, and no AI attribution in output.

## Code & Git

| Agent | Key Tools | Description |
|-------|-----------|-------------|
| `code-reviewer` | Read, Glob, Grep | Expert code quality, security, and best-practice review. Outputs APPROVE / REQUEST CHANGES / BLOCK with categorized findings. |
| `commit-message-generator` | Read, Bash(git:*) | Commitizen conventional format (`<type>(<scope>): <subject>`). No AI attribution. |
| `pull-request-writer` | Read, Bash(git:*) | PR title and description. Scannable, concise, no AI footers. |
| `pull-request-commentor` | Read, Glob, Grep | Inline and general PR review comments. Categorizes: critical / important / nice-to-have. |

## Writing & Documents

| Agent | Key Tools | Description |
|-------|-----------|-------------|
| `human-writer` | Read, Edit | Any document, email, or proposal. One document only — edit, never create duplicates. Radical brevity, executive voice. |
| `document-summarizer` | Read, Glob | Long document analysis: key points, themes, action items, open questions. |

## Orchestration

| Agent | Key Tools | Description |
|-------|-----------|-------------|
| `team-leader` | Agent, Read, Glob, Grep | Decomposes problem into 2–6 parallel sub-problems, spawns agents, synthesizes unified output. |
| `follower` | Read, Edit, Bash, Write | Executes delegated pipeline phases for team-leader. Applies layered reasoning: observe → hypothesize → analyze → conclude. |
| `orchestrator` | Agent, TodoWrite, Read | Coordinates multi-workstream projects: breaks work into parallel workstreams, tracks via master todo, handles blockers. |

## Tickets & Issues

| Agent | Key Tools | Description |
|-------|-----------|-------------|
| `jira-ticket-writer` | Read | JIRA tickets in Wiki Markup syntax. Types: bug, feature, task, epic. |
| `phabricator-ticket-writer` | Read | Phabricator tickets in Remarkup syntax. Preserves exact specs, config values, rollback plans. |

## Knowledge & Utilities

| Agent | Key Tools | Description |
|-------|-----------|-------------|
| `tech-radar` | Read, Edit | Maintain `docs/radar.md` — add, promote, demote, or retire tools across four rings (Adopt/Trial/Assess/Hold). |
| `todo` | TodoRead, TodoWrite | Manages the todo list: add, update, complete, clear. No side effects. |

## Shared Prompts

Reusable prompt fragments in `prompts/`:

- `prompts/continuous-phased.md` — Shared by `document-summarizer` and `human-writer`
- `prompts/orchestrator-system.md` — System prompt for the `orchestrator` agent
- `prompts/plan-mode.md` — Plan mode restriction injection for sub-agents
