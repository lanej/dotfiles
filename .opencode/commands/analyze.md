---
description: Analyze document content and extract insights
agent: document-summarizer
subtask: true
model: anthropic/claude-haiku-4-20250514
---

Read and analyze: $ARGUMENTS

Provide:
1. **Key Points** (5-7 bullets max)
2. **Action Items** (if any - who does what by when)
3. **Open Questions** (what's unclear/missing/needs decision)
4. **Critical Details** (technical specs, deadlines, decisions, metrics)

Focus on: What matters most? What needs to happen next?

Format as scannable markdown with clear headers.
