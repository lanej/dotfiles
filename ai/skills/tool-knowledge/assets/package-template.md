# Tool knowledge package template

Replace placeholders with tool-specific knowledge and delete unused sections. Keep the entrypoint's shared rules short and its topic reads conditional. The sample paths below must exist in the resulting package; the topic names are examples, not a required taxonomy.

## Entrypoint outline

```markdown
---
name: <tool-name>
description: Use when <specific user tasks involving this tool and distinguishing triggers>.
---

# <Tool>

<Scope, relevant environment selection, essential constraints and authority limits.>

Read the matching references before performing these tasks:

| Task | Read |
| --- | --- |
| <Common task needing detail> | [<Task topic>](references/task-topic.md) |
| <Specific failure or advanced operation> | [<Other topic>](references/other-topic.md) |

<Shared observable outcome check and how to report an unknown result.>
```

## Topic note outline

```markdown
# <User task>

<When this note applies; version/environment limitations if material.>

## Procedure

<Required inputs and account, environment, or resource selection.>

<Smallest working command/API example with portable input placeholders.>

<Expected artifact/state and the check that confirms it; cleanup if needed.>

## Troubleshooting

| Symptom | Check | Recovery and confirmation |
| --- | --- | --- |
| <Observed failure> | <Distinguishes a likely cause> | <Action and observable recovery> |

## Sources

<Official documentation or source supporting non-obvious claims. Give version/date scope for transient behavior and a way to recheck it. Label local observations and unverified advice accurately.>
```
