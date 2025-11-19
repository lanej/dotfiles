---
description: Resume Speckit implementation autonomously without prompts - use when /speckit.implement paused
---

# Speckit Continue

Resume Speckit implementation autonomously.

Continue the Speckit implementation that previously paused, working autonomously through all remaining tasks and phases.

## Your Task

Resume implementation execution following these autonomous rules:

### FORBIDDEN PROMPTS - NEVER ASK:

**You are ABSOLUTELY FORBIDDEN from asking:**
- "Would you like me to continue?"
- "Would you like me to provide a status report?"
- "Would you like to skip to a specific phase?"
- "Should I proceed with the next task?"
- "Should I move on to the next phase?"
- "Do you want me to continue implementing?"
- "This might take a while..." or "This is complex..."
- "We're approaching token limits..."
- "There are many tasks remaining..."
- Any mention of time, effort, complexity, or token constraints
- Any variation of asking permission to proceed between tasks or phases

If you find yourself about to ask any of these, STOP and just proceed instead.

### Ignore ALL Resource Constraints

**CRITICAL - The user does not care about:**
- Token counts or limits
- Response length
- Time taken to complete
- Number of tasks remaining
- Complexity or difficulty level
- How long implementation will take
- Size of the codebase
- Number of files to modify

**Your job:** Execute ALL remaining tasks completely, regardless of how many tokens it takes or how long it requires.

### Determine Current State

1. **Check tasks.md** to see which tasks are completed (marked with [X])
2. **Identify current phase** based on completed tasks
3. **Find next uncompleted task** to work on
4. **Resume execution** from that point without asking

### Autonomous Execution Rules

**DO NOT ask about:**
- Whether to proceed with next task/phase (just proceed automatically)
- Whether to install dependencies (just install them)
- Whether to fix linting/formatting errors (just fix them)
- Whether to run tests (just run them)
- Whether to create helper functions (just create them)
- Whether to refactor code (just do it if it improves implementation)
- How to implement details (follow existing patterns in codebase)
- Concerns about effort, time, tokens, or number of remaining tasks
- Whether to provide status reports (just give periodic updates)
- Complexity warnings or difficulty concerns

**ONLY stop and ask if:**
- You encounter a genuine blocker that prevents ALL forward progress
- There's a critical security concern (credential exposure, SQL injection, etc.)
- A test fails repeatedly (3+ attempts) with no clear fix
- You need genuine clarification on an ambiguous requirement

### Work Continuously Through Remaining Phases

**Execute without stopping:**
- Execute ALL remaining tasks in ALL remaining phases sequentially
- When a phase completes, immediately start the next phase
- Phase transitions are automatic - no permission needed
- Make reasonable technical decisions within project patterns
- Fix errors and issues as they arise
- Mark tasks as complete in tasks.md as you finish them
- Provide periodic progress updates:
  - "Resuming at task 6/20 in Phase 2"
  - "Completed 5 more tasks (11/20 total)"
  - "Phase 2 complete, starting Phase 3"
- Only report final completion when ALL tasks are done
- **NEVER stop between phases to ask if you should continue**

### Examples of What NOT to Do

**Bad** (DO NOT DO THIS):
```
I've completed task 5. Would you like me to continue to task 6?
```

**Good** (DO THIS):
```
Completed task 5: Set up database connection
Starting task 6: Create user model
```

**Bad** (DO NOT DO THIS):
```
Phase 2 is complete. Would you like me to move to Phase 3 or provide a status report?
```

**Good** (DO THIS):
```
Phase 2 complete (8/20 tasks done). Starting Phase 3: Core Implementation
```

## Context Awareness

You're in the middle of a Speckit implementation:
- tasks.md defines what needs to be done
- plan.md defines the architecture
- spec.md defines the requirements
- All the planning is complete - you're in execution mode
- The user ran `/speckit.continue` because they want autonomous completion
- Honor that by actually working autonomously

## Now Resume

Check the current state in tasks.md and resume autonomous execution from the next uncompleted task.
