---
description: "Assess task complexity and recommend the optimal Claude model before starting work"
argument-hint: [task description]
allowed-tools: []
---

# /pick-model — Pre-flight Model Assessment

Evaluate the task described in `$ARGUMENTS` (or the most recent user request if no arguments) against the model selection heuristics below, then output a single recommendation block.

## Heuristics

**Haiku 4.5** (`claude-haiku-4-5`, $1/$5 per MTok):
- Single-turn Q&A with factual answers
- Simple classification or extraction
- Keyword lookup, regex generation, trivial transforms

**Sonnet 4.6** (`claude-sonnet-4-6`, $3/$15 per MTok) — default:
- Boilerplate generation, scaffolding, well-known API usage
- Simple refactors with clear mechanical steps
- Documentation, commit messages, PR descriptions
- Search/grep/explore tasks, file reading, format conversions
- Single-file bug fixes with obvious root causes

**Opus 4.8** (`claude-opus-4-8`, $5/$25 per MTok):
- Multi-stage coherence required (later steps must stay consistent with earlier decisions across 5+ files or phases)
- Novel architecture decisions requiring design tradeoff evaluation
- Subtle bugs: race conditions, cross-system state, or concurrent execution paths
- High correction cost: architectural decisions, security design, migration plans
- Complex data modeling: non-trivial joins, window functions, schema-wide query optimization
- Any task where one wrong assumption cascades into rework that exceeds the Opus premium

**The economic break-even**: Opus costs 1.7× Sonnet per token. If you estimate Sonnet would need 2+ revision rounds to get it right, Opus is likely cheaper in total tokens.

## Output Format

Output exactly this block, nothing else:

```
Model:   [Haiku 4.5 | Sonnet 4.6 | Opus 4.8]
Command: claude --model [claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-8]
Reason:  [One sentence: the specific signal that drove this recommendation]
```

If no task is described, output:
```
No task described. Usage: /pick-model <task description>
```
