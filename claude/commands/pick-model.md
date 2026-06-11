---
description: "Pre-flight model recommendation for a described task"
argument-hint: [task description]
allowed-tools: []
---

Evaluate the task against the model selection heuristics and output exactly:

```
Model:   [Haiku 4.5 | Sonnet 4.6 | Opus 4.8]
Command: claude --model [claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-8]
Reason:  [one sentence — the specific signal that drove this]
```

If no argument: `No task described. Usage: /pick-model <task>`
