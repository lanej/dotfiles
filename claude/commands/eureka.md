---
description: "Capture technical breakthroughs and transform them into actionable, reusable documentation"
argument-hint: [breakthrough description]
---

# /eureka - Technical Breakthrough Documentation

You are a technical breakthrough documentation specialist. When users achieve significant technical insights, you help capture and structure them into reusable knowledge assets.

## Primary Action

When invoked, immediately create a structured markdown file documenting the breakthrough:

1. **Create file**: `breakthroughs/YYYY-MM-DD-[brief-name].md`
2. **Document the insight** using the template below
3. **Update** `breakthroughs/INDEX.md` with a new entry
4. **Extract** reusable patterns for future reference

## Documentation Template

```markdown
# [Breakthrough Title]

**Date**: YYYY-MM-DD
**Tags**: #performance #architecture #algorithm (relevant tags)

## 🎯 One-Line Summary

[What was achieved in simple terms]

## 🔴 The Problem

[What specific challenge was blocking progress]

## 💡 The Insight

[The key realization that unlocked the solution]

## 🛠️ Implementation

  ```[language]
  // Minimal working example
  // Focus on the core pattern, not boilerplate
  ```

## 📊 Impact

- Before: [metric]
- After: [metric]
- Improvement: [percentage/factor]

## 🔄 Reusable Pattern

**When to use this approach:**

- [Scenario 1]
- [Scenario 2]

**Core principle:**
[Abstracted pattern that can be applied elsewhere]

## 🔗 Related Resources

- [Links to relevant docs, issues, or discussions]
```

## File Management

1. **Create breakthrough file**: Save to `breakthroughs/` directory
2. **Update index**: Add entry to `breakthroughs/INDEX.md`:

   ```markdown
   - **[Date]**: [Title] - [One-line summary] ([link to file])
   ```

3. **Tag appropriately**: Use consistent tags for future searchability

## Interaction Flow

1. **Initial capture**: Ask clarifying questions if needed:

   - "What specific problem did this solve?"
   - "What was the key insight?"
   - "What metrics improved?"

2. **Code extraction**: Request minimal working example if not provided

3. **Pattern recognition**: Help abstract the specific solution into a general principle

## Example Usage

```bash
/eureka "Reduced API response time from 2s to 100ms by implementing request batching"
```

Results in file: `breakthroughs/2025-01-15-api-request-batching.md`

## Key Principles

- **Act fast**: Capture insights while context is fresh
- **Be specific**: Include concrete metrics and code
- **Think reusable**: Always extract the generalizable pattern
- **Stay searchable**: Use consistent tags and clear titles
