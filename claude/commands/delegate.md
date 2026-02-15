---
description: "Delegate work to specialized agents to protect context window: use Task tool for searches, exploration, planning, and multi-step tasks instead of doing work directly"
tags:
  - context-management
  - efficiency
  - agents
  - delegation
---

# Delegate - Protect Context by Using Sub-Agents

**CRITICAL**: Your context window is precious. Delegate work to specialized agents using the Task tool instead of consuming your own context with searches, exploration, and multi-step tasks.

## Core Principle

**If work CAN be delegated, it SHOULD be delegated.**

Every grep, glob, file read, and search you perform consumes YOUR context. Every agent you spawn uses THEIR context, keeping yours clean for the user's primary conversation.

## When to Delegate (Use Task Tool)

### ALWAYS Delegate These

**Codebase exploration** (use `subagent_type: "Explore"`):
- Searching for files by pattern across multiple directories
- Finding where features are implemented
- Understanding codebase structure
- Locating API endpoints, components, or modules
- Open-ended queries like "how does authentication work?"
- ANY search that might require multiple rounds of grepping/globbing

```bash
# DON'T do this yourself:
grep -r "authenticate" .
grep -r "login" .
grep -r "session" .
# This consumes YOUR context with potentially thousands of results

# DO delegate:
Task(subagent_type="Explore", prompt="Find where user authentication is implemented")
```

**Multi-step research** (use `subagent_type: "general-purpose"`):
- Investigating unfamiliar libraries or frameworks
- Researching how to solve a problem
- Finding examples of similar implementations
- Gathering information from multiple sources
- Any task requiring 3+ tool calls to complete

**Planning** (use `subagent_type: "Plan"`):
- Designing implementation approaches
- Creating step-by-step plans
- Identifying critical files
- Considering architectural trade-offs

**Summarization** (use `subagent_type: "document-summarizer"`):
- Reading lengthy documentation files
- Extracting key points from long markdown files
- Analyzing multiple related documents
- Creating executive summaries

### Sometimes Delegate

**File operations** - delegate if:
- Reading 5+ files to understand something
- Searching for specific patterns across many files
- Need to explore multiple locations

**Code review** - delegate if:
- Reviewing entire pull requests
- Analyzing large diffs
- Checking multiple files for consistency

### DON'T Delegate These

**Direct user requests for specific actions:**
- User asks you to edit a specific file
- User provides exact file path to read
- User wants YOU to implement something

**Simple, known operations:**
- Reading 1-2 specific files
- Single grep for exact class/function name
- Quick glob for known pattern

**Already in context:**
- Information from previous messages
- Files you've already read
- Work you've already done

## Delegation Patterns

### Pattern 1: Codebase Exploration

**BAD** (consumes your context):
```
User: "How does error handling work in this codebase?"
You: [runs multiple greps and globs, reads 10+ files, fills context]
```

**GOOD** (delegates):
```
User: "How does error handling work in this codebase?"
You: Task(
  subagent_type="Explore",
  prompt="Investigate error handling patterns in this codebase. Find error types, handlers, and common patterns.",
  thoroughness="medium"
)
```

### Pattern 2: Multi-File Search

**BAD**:
```
# Searching yourself
Grep(pattern="handleSubmit")
Grep(pattern="onSubmit")
Grep(pattern="submitForm")
# ... more searches, filling your context
```

**GOOD**:
```
Task(
  subagent_type="Explore",
  prompt="Find all form submission handlers. Look for handleSubmit, onSubmit, submitForm patterns.",
  thoroughness="quick"
)
```

### Pattern 3: Research Tasks

**BAD**:
```
# You doing research
WebSearch("how to use library X")
Read(file from search results)
WebSearch("library X examples")
Read(more files)
# Your context fills with research
```

**GOOD**:
```
Task(
  subagent_type="general-purpose",
  prompt="Research how to use library X for our use case. Find examples and best practices."
)
```

### Pattern 4: Large File Analysis

**BAD**:
```
Read("docs/long-specification.md")  # 2000+ lines
Read("docs/architecture.md")        # 1500+ lines
Read("docs/api-reference.md")       # 3000+ lines
# Your context is now full of documentation
```

**GOOD**:
```
Task(
  subagent_type="document-summarizer",
  prompt="Summarize the key points from the specification, architecture, and API docs in docs/. Focus on authentication requirements."
)
```

## Context Management Rules

### Rule 1: One Search, Maybe. Two Searches, Delegate.

If you find yourself doing a second grep/glob for the same goal, stop and delegate.

```bash
# First search - OK
Grep(pattern="AuthService")

# About to do second search? STOP. Delegate instead.
# DON'T: Grep(pattern="auth")
# DO: Task(subagent_type="Explore", prompt="Find authentication service implementation")
```

### Rule 2: Unknown Territory = Delegate

If you don't know where something is or how it works, delegate the discovery.

```bash
# You don't know the codebase structure
# DON'T search yourself
# DO delegate:
Task(subagent_type="Explore", prompt="Find the payment processing implementation")
```

### Rule 3: Multiple Possibilities = Delegate

If there are multiple ways something could be named/located, delegate.

```bash
# Could be "login", "signin", "authenticate", "auth", etc.
# DON'T try them all yourself
# DO delegate:
Task(subagent_type="Explore", prompt="Find login/authentication flow")
```

### Rule 4: Protect Context for User Interaction

Your context is for:
- User conversation history
- Files you're actively editing
- Code you're currently writing
- Context needed for implementation

Your context is NOT for:
- Search results
- Exploration work
- Research material
- Documentation reading

## Agent Types Quick Reference

```bash
# Codebase exploration and searches
Task(subagent_type="Explore", ...)

# General research and multi-step tasks
Task(subagent_type="general-purpose", ...)

# Implementation planning
Task(subagent_type="Plan", ...)

# Document summarization
Task(subagent_type="document-summarizer", ...)

# Pull request review
Task(subagent_type="pull-request-commentor", ...)

# Commit messages
Task(subagent_type="git-commit-message-writer", ...)
```

## Benefits of Delegation

**Context Protection:**
- Your context stays clean for primary conversation
- User's conversation history preserved
- More room for implementation work

**Efficiency:**
- Agents can explore freely without cluttering main thread
- Failed searches don't pollute your context
- Multiple agents can run in parallel

**Better Results:**
- Specialized agents are optimized for their tasks
- Explore agent knows how to search thoroughly
- Plan agent knows how to structure plans

## Mental Model

Think of yourself as a **manager** not a **worker**:

- **Manager**: Delegates exploration to team, receives summary, acts on results
- **Worker**: Does all searches personally, context fills with minutiae

When user asks a question:
1. Can an agent answer this better? → Delegate
2. Do I need to search/explore? → Delegate
3. Is this implementation work I should do? → Do it yourself
4. Am I about to do multiple searches? → Delegate

## Anti-Patterns to Avoid

**Anti-Pattern 1: Doing Your Own Research**
```
User: "How do we handle database migrations?"
You: [searches, reads 10 files, fills context]
```
Fix: Delegate to Explore agent

**Anti-Pattern 2: Repeated Searches**
```
Grep(pattern="migration")
Grep(pattern="migrate")
Grep(pattern="schema")
```
Fix: One Task call, let agent do multiple searches

**Anti-Pattern 3: Reading Long Docs Yourself**
```
Read("README.md")  # 500 lines
Read("CONTRIBUTING.md")  # 300 lines
Read("ARCHITECTURE.md")  # 800 lines
```
Fix: Delegate to document-summarizer

**Anti-Pattern 4: Exploring Without Clear Target**
```
Glob(pattern="**/*.ts")  # 500 files
# Now what? Your context is huge
```
Fix: Delegate exploration with clear goal

## The Delegation Checklist

Before performing ANY search or exploration, ask:

1. **Is this a needle query?** (Exact class/function name)
   - YES → Maybe do it yourself
   - NO → Delegate

2. **Will this require multiple searches?**
   - YES → Delegate
   - MAYBE → Delegate

3. **Do I know exactly where to look?**
   - YES → Maybe do it yourself
   - NO → Delegate

4. **Will results consume significant context?**
   - YES → Delegate
   - NO → Maybe do it yourself

5. **Is this exploratory/research work?**
   - YES → Delegate
   - NO → Maybe do it yourself

**When in doubt, DELEGATE.**

## Example Scenarios

### Scenario 1: User Asks About Feature

**User**: "How do we handle file uploads?"

**Bad Response**:
```
[Runs 5 greps, reads 8 files, context fills with search results]
"Based on my search, file uploads are handled in..."
```

**Good Response**:
```
Task(
  subagent_type="Explore",
  prompt="Find how file uploads are implemented. Look for upload handlers, storage logic, and validation.",
  thoroughness="medium"
)

[Agent returns summary]
"Based on the codebase exploration, file uploads are handled in..."
```

### Scenario 2: User Wants Implementation

**User**: "Add validation to the login form"

**Bad Response**:
```
[Searches for login forms, reads multiple files, fills context]
[Then implements validation]
```

**Good Response**:
```
Task(
  subagent_type="Explore",
  prompt="Find the login form component",
  thoroughness="quick"
)

[Agent returns location]
[Read specific file]
[Implement validation]
```

### Scenario 3: User Asks Architectural Question

**User**: "What's the overall architecture of the authentication system?"

**Bad Response**:
```
[Searches across entire codebase, reads dozens of files]
```

**Good Response**:
```
Task(
  subagent_type="Explore",
  prompt="Analyze the authentication system architecture. Identify main components, data flow, and integration points.",
  thoroughness="very thorough"
)
```

## Summary

**Core Rules**:
1. **Exploration = Delegation**: Always delegate codebase exploration
2. **Multi-search = Delegation**: 2+ searches for same goal → delegate
3. **Research = Delegation**: Unknown libraries/concepts → delegate
4. **Long docs = Delegation**: 500+ line files → delegate to summarizer
5. **Protect context**: Your context is for user conversation and active work

**Default Mindset**:
- "Can I delegate this?" → Usually YES
- "Should I search this myself?" → Usually NO
- "Will this consume my context?" → Then DELEGATE

**Remember**: You're a manager with a team of specialized agents. Use them. Your job is to coordinate and synthesize, not to do all the searches yourself.
