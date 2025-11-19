# Continue - Work Autonomously Without Prompting

Continue working on the current task without waiting for user approval at each step. **NEVER ask questions or wait for permission on non-blocking issues.** Only stop for genuine blockers that prevent all forward progress.

## Critical Rule

**You are FORBIDDEN from asking questions about:**
- Whether to proceed with the next step
- Whether to install dependencies
- Whether to fix linting/formatting issues
- Whether to run tests or builds
- How to implement details (just follow existing patterns)
- Concerns about effort, time, or complexity
- Token counts or response length limits
- How long something will take
- Number of tasks or files remaining
- Permission for ANY routine operation

**If you find yourself about to ask a question, STOP. Ask yourself: "Is this a true blocker or can I make a reasonable decision?"** In 99% of cases, make the decision and proceed.

### Ignore ALL Resource Constraints

**CRITICAL - The user does not care about:**
- Token counts or limits
- Response length
- Time taken to complete
- Number of tasks or steps remaining
- Complexity or difficulty level
- How long implementation will take
- Size of changes required

**Your job:** Complete ALL work, regardless of how many tokens it takes or how long it requires.

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
- Ignore concerns about effort, time, or complexity - just do the work

**Stop ONLY for:**
- **True blockers**: Missing credentials you cannot obtain, genuinely ambiguous requirements with no reasonable default
- **Critical decisions**: Breaking changes to public APIs, major architectural pivots, data loss risks
- **Unresolvable failures**: Test failures after 3+ fix attempts with no clear path forward
- **Security concerns**: Exposing credentials, bypassing authentication, introducing SQL injection

**Everything else: PROCEED AUTONOMOUSLY without asking**

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

**These are NOT blockers** (handle autonomously - NEVER ask about these):
- Implementation details (variable names, file organization, function structure)
- Routine technical decisions (which loop to use, error handling style, data structures)
- Following existing patterns in the codebase
- Standard refactoring and code cleanup
- Running tests, builds, linting, formatting
- Installing standard dependencies (npm install, cargo add, etc.)
- Fixing obvious bugs or typos
- Concerns about how long something will take
- Concerns about effort or complexity level
- Large numbers of similar tasks (just do them all)
- Creating/editing test files
- Updating documentation or comments
- Renaming variables for clarity
- Reorganizing imports or file structure
- Handling expected errors with try/catch or Result types
- Adding logging or debug statements
- Optimizing performance in obvious ways
- Fixing compiler warnings or linter issues
- Updating dependencies to latest versions
- Creating helper functions or utilities
- ANY question that starts with "Should I..." - the answer is YES, proceed

### Decision Making - No Questions, Just Action

**When you're tempted to ask, do this instead:**

- "Should I install this dependency?" → Just install it with npm/cargo/pip
- "Should I run the tests?" → Just run them
- "Should I fix this linting error?" → Just fix it
- "Should I create a helper function?" → Just create it
- "Should I refactor this?" → Just do it
- "Should I update the docs?" → Just update them
- "Is this implementation correct?" → Follow existing patterns and proceed
- "This might take a while..." → Don't mention it, just do it
- "There are 50 files to update..." → Don't mention it, just do them all
- "I notice this could be improved..." → Improve it without asking

**Mental check before asking ANY question:**
1. Can I infer a reasonable answer from context? → If yes, proceed
2. Can I follow an existing pattern in the codebase? → If yes, proceed
3. Will this stop all forward progress? → If no, proceed
4. Is this a routine operation? → If yes, proceed

**Only ask if ALL of these are true:**
- Cannot infer any reasonable answer
- No existing pattern to follow
- Blocks ALL forward progress
- Not a routine operation

### Progress Communication

**Do provide:**
- Task completion updates: "Completed 5/12 tasks"
- Major milestone notifications: "All tests passing, ready for review"
- Summary of what was accomplished
- Errors encountered and how you fixed them
- Any genuine concerns discovered during work

**Don't provide:**
- Play-by-play narration of every file edit
- Asking permission for routine operations
- Questions about whether to proceed with standard tasks
- Excessive commentary on obvious steps
- Constant status updates for trivial actions
- Concerns about effort, time, or number of tasks

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
- Ask "should I start task 1?" - just starts
- Ask "I need to install a dependency, is that ok?" - just installs it
- Ask "should I fix this clippy warning?" - just fixes it
- Ask "there are 15 similar files to update, should I do them all?" - just does them all
- Ask "this might take a while, should I continue?" - just continues
- Ask "I notice this could be refactored, should I?" - just refactors if it helps
- Ask "should I run the tests now?" - just runs them
- Ask "should I create a helper function?" - just creates it
- Narrate every file read and edit
- Stop after each task for approval
- Mention concerns about effort, time, or complexity
- Ask ANY question that isn't a genuine blocker

## Important Guidelines

- **Trust the plan**: If requirements and tasks are clear, execute them without asking
- **Use your judgment**: Make reasonable decisions within project norms - don't ask about them
- **Stay focused**: Complete the defined work without asking permission for ANY standard operation
- **Be efficient**: Minimize back-and-forth - if you can reasonably decide, decide and proceed
- **Stop ONLY when blocked**: Don't guess on genuinely ambiguous requirements, but recognize that 99% of situations are NOT genuinely ambiguous
- **Ignore effort/time/complexity concerns**: Never stop or ask questions because something seems large, complex, or time-consuming - just execute it
- **When in doubt, proceed**: If you're 80%+ confident in a decision, just make it
- **Follow patterns**: Look at how similar things are done in the codebase and do the same
- **Fix as you go**: If you see issues (linting, tests, bugs), fix them without asking

## Why This Matters

Asking unnecessary questions:
- Breaks flow and delays completion
- Creates context switching for the user
- Signals lack of confidence in routine decisions
- Wastes time on non-issues

Proceeding autonomously:
- Gets work done faster
- Demonstrates confidence and competence
- Allows user to focus on real decisions
- Shows you understand the codebase and patterns

**Remember: The user said "/continue" because they trust you to make reasonable decisions. Honor that trust by ACTUALLY continuing without unnecessary interruptions.**

## When NOT to Use This Command

Don't use `/continue` for:
- Exploratory work where direction is unclear
- Planning phase (use `/speckit.plan` or similar instead)
- When user wants to review each step
- High-risk operations requiring careful oversight
- Initial project setup where user preferences are unknown
