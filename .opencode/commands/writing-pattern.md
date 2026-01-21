---
description: Document writing patterns and style decisions for reuse
---

Capture a writing pattern or style decision: $ARGUMENTS

Ask the user:
1. What writing challenge did this solve?
2. What's the pattern/technique?
3. Example before/after?
4. When should this be used?

Create file: `writing-patterns/YYYY-MM-DD-[pattern-name].md`

Template:
```markdown
# [Pattern Name]

**Date**: YYYY-MM-DD
**Context**: [When/where this applies]

## The Challenge
[What writing problem this solves]

## The Pattern
[The reusable writing approach]

## Example

**Before:**
[Weak version]

**After:**
[Strong version]

## When to Use
- [Scenario 1]
- [Scenario 2]
- [Scenario 3]
```

Also update: `writing-patterns/INDEX.md` with new entry:
```markdown
- **[Date]**: [Title] - [One-line summary] ([link])
```
