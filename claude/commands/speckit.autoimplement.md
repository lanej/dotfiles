---
description: Execute /speckit.implement with full autonomous execution - no prompts between phases or tasks
---

# Speckit Auto-Implementation

Execute `/speckit.implement` with full autonomous mode.

You are about to execute `/speckit.implement` with **full autonomous mode** enabled.

## Critical Instructions

Execute `/speckit.implement` immediately, then follow these rules during the ENTIRE implementation:

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

**Your job:** Execute ALL tasks completely, regardless of how many tokens it takes or how long it requires.

### Autonomous Execution Rules

**DO NOT ask about:**
- Whether to proceed with next task/phase (just proceed automatically)
- Whether to install dependencies (just install them)
- Whether to fix linting/formatting errors (just fix them)
- Whether to run tests (just run them)
- Whether to create helper functions (just create them)
- Whether to refactor code (just do it if it improves implementation)
- How to implement details (follow existing patterns in codebase)
- Concerns about effort, time, tokens, or number of tasks
- Whether to provide status reports (just give periodic updates)
- Complexity warnings or difficulty concerns

**ONLY stop and ask if:**
- A checklist quality gate fails (the initial validation in speckit.implement)
- You encounter a genuine blocker that prevents ALL forward progress
- There's a critical security concern (credential exposure, SQL injection, etc.)
- A test fails repeatedly (3+ attempts) with no clear fix

### Work Continuously Through ALL Phases

**Execute without stopping:**
- Execute ALL tasks in ALL phases sequentially without stopping
- When a phase completes, immediately start the next phase
- Phase transitions (Setup → Tests → Core → Integration → Polish) are automatic
- Make reasonable technical decisions within project patterns
- Fix errors and issues as they arise
- Mark tasks as complete in tasks.md as you finish them
- Provide periodic progress updates:
  - "Completed 5/20 tasks"
  - "Phase 2 complete, starting Phase 3"
  - "Setup phase done (5 tasks), moving to Tests phase"
- Only report final completion when ALL phases and ALL tasks are done
- **NEVER stop between phases to ask if you should continue**

### Mental Model

Think of this as `/continue` mode but specifically for Speckit implementation:
- You have a clear task list (tasks.md)
- You know the phases to execute
- The path forward is defined
- Just execute everything without asking permission

The user ran `/speckit.autoimplement` because they want the ENTIRE implementation done autonomously. Honor that by actually working autonomously through all phases and tasks.

## Now Execute

Run `/speckit.implement` and follow the autonomous execution rules above throughout the entire process.
