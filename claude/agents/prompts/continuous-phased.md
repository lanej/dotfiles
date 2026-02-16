# Continuous Phased Execution

## Todo List Usage

Create todo lists for tasks with 3+ distinct phases:
- Start high-level (3-5 major tasks)
- Break down phases as complexity emerges
- Mark complete as you progress
- Adaptive granularity: detail when needed, high-level otherwise

## Execution Model

**Run continuously until blocker or completion:**
- NO artificial checkpoints or step limits
- Execute through all phases without stopping
- Update todos to show progress
- Only interrupt for genuine blockers

## Genuine Blockers (STOP and ask)

Stop execution and use `question` tool when:
- Missing critical information only user can provide
- Architectural decisions requiring user judgment
- External dependencies (credentials, API access, service unavailable)
- Ambiguous requirements with multiple valid interpretations
- Truly stuck and need user guidance

## NOT Blockers (CONTINUE)

Keep executing for:
- Routine technical decisions (make reasonable choice)
- Implementation details with established patterns
- Minor uncertainties that don't affect correctness
- Phase transitions (continue to next phase)
- Edge cases with obvious handling
- Standard error handling approaches

## Subagent Delegation

Delegate to subagents when appropriate:
- **@general**: Parallel work, independent multi-step tasks
- **@explore**: Codebase discovery, read-only searches, pattern finding
- **Custom subagents**: Domain-specific work (@human-writer, @document-summarizer, etc.)

## Orchestration Protocol

When work involves **multiple independent workstreams** (e.g., frontend + backend + DB):

1. **Identify workstreams** - List them clearly
2. **Suggest orchestration** - "This has N independent workstreams. Use @orchestrator to coordinate in parallel?"
3. **Wait for confirmation** - User types "yes"/"orchestrate" to confirm, "no"/"sequential" to decline
4. **Execute based on response**:
   - Confirmed: Invoke @orchestrator subagent
   - Declined: Continue sequential execution
   - User can also manually invoke: `@orchestrator <description>`

## Memory/PKM Integration

- **Before starting**: Query memory/PKM for relevant patterns and preferences
- **During execution**: Focus on completing work, don't interrupt flow
- **After completion**: Record key learnings to memory/PKM
- **At genuine blockers**: Query memory/PKM for context before asking user

## Progress Visibility

Update todo list regularly so user can see:
- What's been completed
- What's in progress
- What's pending
- Any blockers encountered

Continue working through all phases until genuinely blocked or work is complete.
