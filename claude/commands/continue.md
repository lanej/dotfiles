# Continue - Work Autonomously Without Prompting

Continue working on the current task without waiting for user approval at each step. Only stop and ask questions when you encounter a blocker or genuine ambiguity.

## Your Task

Execute all remaining work autonomously by following these principles:

### Execution Mode

**Assume all planning is complete:**
- Requirements are defined (spec.md, issue, or user request)
- Tasks are broken down (tasks.md or todo list)
- Implementation approach is clear
- No need for additional clarification unless truly blocked

**Work continuously:**
- Execute tasks sequentially without asking permission for each step
- Make reasonable technical decisions within established patterns
- Follow project conventions and best practices
- Fix errors and issues as they arise
- Run tests, builds, and validation automatically

**Stop only for:**
- **True blockers**: Missing credentials, ambiguous requirements, conflicting constraints
- **Critical decisions**: Breaking changes, major architectural choices, data loss risks
- **Failures you cannot resolve**: Repeated test failures, build errors, missing dependencies
- **Security concerns**: Potential vulnerabilities, credential handling, authentication issues

### Working Style

**Be efficient:**
- Don't narrate every single action
- Provide periodic progress updates (e.g., "Completed 3/10 tasks")
- Show results and outcomes, not play-by-play
- Use todo list to track progress visibly

**Be autonomous:**
- Read documentation and code as needed
- Search for patterns and examples in the codebase
- Install dependencies if needed
- Fix linting/formatting issues automatically
- Handle routine errors without asking

**Be thorough:**
- Complete each task fully before moving to the next
- Run tests after changes
- Verify your work compiles/runs
- Mark todos as completed only when truly done
- Clean up as you go

### What Counts as a Blocker

**These ARE blockers** (stop and ask):
- Requirement is genuinely ambiguous or contradictory
- Multiple valid approaches with significant trade-offs
- Missing information that cannot be inferred from context
- Repeated failures you cannot debug
- Destructive operations (data deletion, force push to main)

**These are NOT blockers** (handle autonomously):
- Implementation details (variable names, file organization)
- Routine technical decisions (which loop to use, error handling style)
- Following existing patterns in the codebase
- Standard refactoring and code cleanup
- Running tests, builds, linting
- Installing standard dependencies
- Fixing obvious bugs or typos

### Progress Communication

**Do provide:**
- Task completion updates: "Completed 5/12 tasks"
- Major milestone notifications: "All tests passing, ready for review"
- Summary of what was accomplished
- Any warnings or concerns discovered during work

**Don't provide:**
- Play-by-play narration of every file edit
- Asking permission for routine operations
- Excessive commentary on obvious steps
- Constant status updates for trivial actions

## Usage

After planning is complete and tasks are defined:

```
/continue
```

Or use inline during conversation:
```
User: Here are the 10 tasks to complete [lists tasks]
Assistant: [Creates todo list] /continue
```

## Example Behavior

**User**: "I have tasks.md with 15 implementation tasks. They're all straightforward following existing patterns. Get them done."

**Assistant**:
- Reads tasks.md
- Creates todo list with 15 items
- Starts executing task 1 without asking
- Completes tasks 1-5, provides brief update
- Hits a test failure on task 6, debugs and fixes it
- Continues through tasks 7-15
- Runs final validation (tests, build, clippy)
- Reports completion with summary

**What the assistant does NOT do:**
- Ask "should I start task 1?"
- Ask "I need to install a dependency, is that ok?"
- Ask "should I fix this clippy warning?"
- Narrate every file read and edit
- Stop after each task for approval

## Important Guidelines

- **Trust the plan**: If requirements and tasks are clear, execute them
- **Use your judgment**: Make reasonable decisions within project norms
- **Stay focused**: Complete the defined work without asking permission for standard operations
- **Be efficient**: Minimize back-and-forth when not needed
- **Stop when blocked**: Don't guess on genuinely ambiguous requirements

## When NOT to Use This Command

Don't use `/continue` for:
- Exploratory work where direction is unclear
- Planning phase (use `/speckit.plan` or similar instead)
- When user wants to review each step
- High-risk operations requiring careful oversight
- Initial project setup where user preferences are unknown
