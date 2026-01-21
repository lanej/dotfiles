---
description: Commit document changes with auto-generated message
---

Stage and commit changes to: $ARGUMENTS

First, check what changed:
!`git diff $ARGUMENTS`

Then create a commit message following this format:

```
docs: [brief summary of change]

- [Key change 1]
- [Key change 2]
- [Key change 3 if needed]
```

Examples:
- `docs: add microservices overview to architecture guide`
- `docs: revise API documentation for clarity`
- `docs: create executive brief on Q1 strategy`

Then execute:
1. `git add $ARGUMENTS`
2. `git commit -m "[your generated message]"`
3. Report the commit hash and message to user
