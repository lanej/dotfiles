# Phased Execution Testing Checklist

Test the newly implemented continuous blocker-driven phased processing in OpenCode.

## Basic Phased Execution

- [ ] **Complex multi-phase task**
  - Give task: "Add authentication system with tests and documentation"
  - Verify Build agent creates adaptive todo list
  - Confirm continuous execution without artificial stops
  - Check todos update as phases complete
  - Verify agent runs until completion or genuine blocker

- [ ] **Adaptive granularity**
  - Give complex task
  - Verify starts with high-level phases (3-5 items)
  - Check if agent breaks down phases as complexity emerges
  - Confirm detailed breakdown only when needed

## Blocker Handling

- [ ] **Genuine blocker - missing info**
  - Give task with ambiguous requirement (e.g., "add auth but don't specify which method")
  - Verify agent stops and uses `question` tool
  - Provide clarification
  - Verify agent continues execution

- [ ] **Genuine blocker - architectural decision**
  - Give task requiring design choice
  - Verify agent identifies decision point and asks user
  - Make decision
  - Verify agent continues with chosen approach

- [ ] **NOT a blocker - routine decision**
  - Give task with implementation details left open
  - Verify agent makes reasonable choice and continues
  - Check agent doesn't stop for minor uncertainties

## Orchestration - Hybrid Model

- [ ] **Orchestration suggestion**
  - Give multi-workstream task: "Build user auth with React frontend, Express backend, and PostgreSQL migration"
  - Verify Build agent identifies independent workstreams
  - Verify agent suggests orchestration
  - Confirm suggestion format: "Use @orchestrator to coordinate in parallel?"

- [ ] **Accept orchestration**
  - When suggested, type "yes" or "orchestrate"
  - Verify @orchestrator subagent is invoked
  - Check orchestrator creates master todo list
  - Verify delegates to appropriate subagents
  - Check parallel execution tracking

- [ ] **Decline orchestration**
  - When suggested, type "no" or "sequential"
  - Verify Build agent continues sequential execution
  - Check agent doesn't invoke orchestrator

- [ ] **Manual orchestration**
  - Type `@orchestrator <task description>` directly
  - Verify orchestrator activates without needing suggestion
  - Check orchestrator handles task appropriately

## Plan Mode

- [ ] **Tab to Plan mode**
  - Press Tab key to switch to Plan mode
  - Give complex task
  - Verify creates adaptive todo list as implementation plan
  - Check plan identifies potential blockers
  - Verify suggests subagents/orchestration if applicable

- [ ] **Execute plan**
  - In Plan mode, review generated plan
  - Press Tab to switch back to Build mode
  - Type "execute the plan" or similar
  - Verify Build agent follows the plan from Plan mode

## Subagent Delegation

- [ ] **Delegate to @general**
  - Give task with parallel work opportunities
  - Verify Build agent delegates workstream to @general
  - Check @general executes with todos enabled
  - Verify progress tracked

- [ ] **Delegate to @explore**
  - Give task requiring codebase discovery
  - Verify Build agent delegates exploration to @explore
  - Check @explore uses todos for multi-step searches
  - Verify results returned to Build agent

- [ ] **Navigate sessions**
  - When orchestrator creates child sessions
  - Press `<Leader>+Right` to cycle forward through sessions
  - Verify cycles: parent → child1 → child2 → ... → parent
  - Press `<Leader>+Left` to cycle backward
  - Verify reverse navigation works

## Agent-Specific Todo Usage

- [ ] **human-writer todos**
  - Invoke @human-writer for complex writing project
  - Verify creates todos for multi-phase writing (outline → draft → revise → polish)
  - Check single-document writing works with or without todos

- [ ] **document-summarizer todos**
  - Invoke @document-summarizer for multi-document analysis
  - Verify creates todos when analyzing multiple documents
  - Check simple summarization works without requiring todos

## Memory Integration

- [ ] **Memory entity created**
  - Query memory: `memory_search_nodes("phased execution")`
  - Verify Josh_Lane_Phased_Execution_Preferences exists
  - Check observations include: continuous execution, adaptive granularity, moderate blocker threshold, hybrid orchestration

- [ ] **Agents check memory**
  - Give complex task to Build agent
  - Verify agent queries memory before starting
  - Check references phased execution preferences in reasoning

- [ ] **Record learnings**
  - Complete multi-phase task
  - Verify agent records key learnings to memory/PKM
  - Check happens after completion, not during execution

## Integration Tests

- [ ] **TDD workflow with phased execution**
  - Give task: "Add feature X with TDD approach"
  - Verify todo tracks: write test → implement → verify test passes
  - Check agent runs full cycle without stopping between red/green/refactor
  - Verify only blocks if tests fail unexpectedly

- [ ] **Multi-file refactoring**
  - Give task requiring changes across 5+ files
  - Verify adaptive breakdown into file-specific phases
  - Check continuous execution through all files
  - Verify completion without artificial stops

## Error Cases

- [ ] **Orchestrator can't recursively invoke**
  - Manually invoke @orchestrator
  - Give task that orchestrator might delegate
  - Verify orchestrator doesn't try to invoke itself
  - Check permission denied if attempted

- [ ] **Handling subagent blockers**
  - Orchestrator delegates to @general
  - @general encounters genuine blocker
  - Verify orchestrator reports blocker to user
  - Check other workstreams continue if possible

## Performance

- [ ] **Long-running task**
  - Give complex task with 10+ phases
  - Verify agent continues execution without timeout
  - Check todos update throughout
  - Verify no artificial stops or step limits

- [ ] **Progress visibility**
  - During multi-phase execution
  - Verify todo list shows in UI
  - Check shows: completed, in progress, pending
  - Verify user can see progress in real-time

## Rollback Verification

If phased execution causes issues:

- [ ] **Revert opencode.json**
  - Set todowrite: false, todoread: false for all agents
  - Remove orchestrator config
  - Remove custom prompts
  - Verify agents return to immediate execution

- [ ] **Clean memory**
  - Delete Josh_Lane_Phased_Execution_Preferences
  - Verify no phased execution references remain

---

## Test Status

**Date tested**: ___________  
**OpenCode version**: ___________  
**Tested by**: ___________  

**Overall result**: PASS / FAIL / PARTIAL

**Issues found**:

**Notes**:
