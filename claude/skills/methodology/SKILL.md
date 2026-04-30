# Methodology Reference

Consolidated methodology, frameworks, and detailed process guidance relocated from CLAUDE.md for space efficiency.

## Visual Communication Requirements

Even outside Quarto documents:
- Use Mermaid diagrams for reasoning flows
- Format tables (never raw df.head())
- Use LaTeX for mathematical notation ($\alpha = 0.15$)
- Show charts for quantitative analysis
- Never dump raw data or print statements
- Never write plain text math ("alpha = 0.15")

## Phased Execution System

OpenCode agents use continuous phased processing for complex multi-step work.

### Execution Model

**Continuous until blocker:**
- Execute through all phases without artificial checkpoints
- NO step limits — work continues until complete or genuinely blocked
- Todo lists track progress (visible in UI)
- Mark phases complete as they finish

**Genuine blockers (stop and ask):**
- Missing critical information only user can provide
- Architectural decisions requiring user judgment
- External dependencies (credentials, API access)
- Ambiguous requirements with multiple valid interpretations

**NOT blockers (continue):**
- Routine technical decisions (make reasonable choice)
- Implementation details with established patterns
- Minor uncertainties that don't affect correctness
- Phase transitions

### Adaptive Todo Granularity

Start with high-level phases (3-5 major tasks), break down as complexity emerges:

**Initial:** `1. Implement auth system  2. Add tests  3. Update docs`

**Adaptive breakdown:**
```
1. Implement auth system
   1.1 Create User model with bcrypt hashing
   1.2 Add JWT token generation
   1.3 Implement middleware for protected routes
   1.4 Add session management
2. Add tests
   2.1 Unit tests for auth functions
   2.2 Integration tests for login flow
```

### Orchestration (Hybrid Model)

For multi-workstream projects, Build agent may **suggest** orchestration:
- User types "yes"/"orchestrate" → invoke @orchestrator subagent
- User types "no"/"sequential" → continue sequential execution
- User types `@orchestrator <description>` → manually invoke

**Orchestrator behavior:** Breaks into parallel workstreams, delegates to subagents, tracks dependencies, reports consolidated status.

### Subagent Delegation

- **@general** — General-purpose multi-step tasks, parallel work
- **@explore** — Read-only codebase discovery
- **@orchestrator** — Multi-workstream coordination
- **Custom agents** — Domain-specific work

### Agent Modes

- **Build (default):** Full tool access, continuous phased execution, delegates to subagents
- **Plan (Tab to switch):** Read-only analysis, creates implementation plans as adaptive todo lists
- **Orchestrator (subagent):** Coordinates parallel workstreams

### Integration with Memory/Search

1. **Before starting**: Check memory and qmd workspace search for relevant patterns
2. **During execution**: Focus on completing work, don't interrupt flow
3. **After completion**: Record key learnings to memory
4. **At blockers**: May query qmd for workspace context before asking user

## Interactive vs Automated Tools

**CRITICAL: Recognize when tools require human interaction and don't try to automate them.**

### Tools That Require Human Interaction (Don't Automate)
- **Text editors** (nvim, vim, nano) — let the user interact
- **Interactive prompts** — confirmation dialogs, menu selections, Y/N prompts
- **arc diff** (no flags) — opens editor for revision message
- **git commit** (no -m flag) — opens editor for commit message
- **Interactive rebases** — git rebase -i requires human decisions

### Red Flags You're Trying to Automate Interactive Tools
- Setting `EDITOR=cat` or `EDITOR=true` to bypass editors
- Using `echo "y" | command` to bypass confirmations
- Getting timeout errors waiting for interactive tools
- Seeing "User aborted the workflow" errors

### Correct Approach
1. Run the command directly without automation attempts
2. Tell the user what command to run if they need to do it themselves
3. Use non-interactive flags if available (e.g., `--message`)
4. Never hack around interactive tools with EDITOR tricks

## Figure and Visualization Audit Protocol

**CRITICAL: Any matplotlib figure task — iteration, audit, review, quality check — MUST render and visually inspect the output image. Code-only review is incomplete.**

**Principle:** Visual defects (clipped titles, illegible text, wrong contrast, squished panels) are invisible in code and obvious in rendered output.

### General Rules
- Render to PNG and read with Read tool before drawing conclusions
- Text color must match its *actual local background* — not the nearest colored element
- Semi-transparent fills produce mid-tone backgrounds; text fallback must be dark enough (`NAVY` not `SLATE`)
- `plt.savefig()` must run before `plt.close()` — calling savefig after close saves blank PNG

### Path Conventions
Use `just dev-fig NAME` → Read PNG from `{project-dir}_files/figure-pdf/{LABEL}-output-1.png`. Path uses **project root directory name** (not QMD stem). Do NOT use `just preview-fig` / Playwright.

### Authoring Reference
`~/src/analysis-doc/docs/AGENTS.md` is source of truth for full checklist, palette contrast table, dimension rules, `__main__` save pattern.

## Session Reflection System

**Commands:**
- `/reflection` — Analyze session and suggest CLAUDE.md improvements (interactive)
- `/reflection-harder` — Comprehensive session analysis with learning capture

**Integration:** `/reflection-harder` integrates with tmux status bar:
1. Signal file: `/tmp/opencode-reflection-ready` created on completion
2. Status indicator: Tmux shows "Reflection Ready" (magenta on brightblack)
3. Clear: `rm /tmp/opencode-reflection-ready`

**Implementation:** Command at `~/.files/claude/commands/reflection-harder.md`, status script at `~/.files/bin/opencode-reflection-status`, tmux at `~/.files/rc/tmux.conf` (line 183). File-based signaling, on-demand only, ephemeral.

## Iterative Task Tracking

- **Work Logs**: For complex multi-step optimization (ML tuning, performance debugging), create `WORKLOG.md` or `CHANGELOG.md`
- **Metrics**: Record baseline metrics before changes, compare after each iteration
- **Diffs**: Document what changed per iteration to correlate with results

## Error Resolution

- Read error messages carefully before attempting fixes
- Always read files before editing (Read tool before Edit tool)
- Verify data schemas before querying — check table schemas, understand field meanings
- Question unexpected results — if analysis seems wrong, STOP and verify assumptions
- Validate data assumptions — don't assume team = autonomy unit
- Clean up background processes: `pkill -f <process-name>`
- For JSON validation errors, fix specific fields rather than rewriting entire files

## Dependency Installation

- If `uv add` hangs building from source (>60 seconds): (1) system Python, (2) PyPI, (3) CLI tool instead
- AVOID installing Python bindings from source when CLI alternatives exist

## TDD Extended Reference

### Feedback Loop Design

**Design the feedback loop before writing code.** Before the first line of implementation, identify what "verifiably done" looks like: which test suite runs, which lint/type-check passes, which grep/diff confirms the output is correct. The verification path is part of the design, not an afterthought.

**Harness verification (false-red / false-green discipline).** When writing tests in new test files, new packages, or any setup where harness wiring is uncertain:
1. Write the failing test
2. Break the implementation in a targeted way (wrong return value, removed function body, inverted condition) to confirm the test catches that specific failure
3. Restore the implementation and confirm green
4. Only then proceed — a green result you haven't confirmed can turn red is a false green and tells you nothing

This applies to new harnesses, not to every test in an established suite.

**Return only when self-validated.** Do not surface results, ask for human confirmation, or request feedback on something you can verify yourself. Run the full suite, confirm the diff, check the output — then return with evidence of completion, not a question.

### Flaky Tests
**Flaky tests are serious bugs — fix immediately.**
- NEVER ignore, skip, or work around flaky tests
- NEVER add retries or sleeps to mask flakiness
- ALWAYS refactor code to eliminate non-determinism
- Common causes: race conditions, shared state, timing dependencies, external dependencies
- Fix by: dependency injection, deterministic mocks, proper test isolation

### Dependency Inversion for Testability
- Quick/dirty scripts without tests: hardcoded dependencies fine
- Code with tests: inject dependencies as parameters
- Accept interfaces/protocols not concrete implementations
- Pass dependencies as parameters for test doubles (mocks, stubs, fakes)

### Acceptance Testing
- Test complete user workflows end-to-end from user's perspective
- Automate where possible
- Acceptance tests serve as executable documentation

### Testing Framework
**Python/pytest strongly preferred:**
- `uv run pytest` or `uv run pytest path/to/test_file.py`
- Coverage: `uv run pytest --cov=scripts --cov-report=html --cov-report=term-missing`
- Use pytest fixtures for isolation and mock behaviors
- AVOID bats, shell-based testing — prefer subprocess testing from Python
