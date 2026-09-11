---
name: methodology
description: "Consolidated methodology reference covering phased execution (continuous work through genuine blockers only, adaptive todo granularity), visual communication requirements (Mermaid diagrams, formatted tables, LaTeX math instead of raw data/plain-text math), and other process guidance relocated from CLAUDE.md for space efficiency. Load when working through multi-step tasks needing phased-execution guidance, or when producing analytical/quantitative output that should follow visual communication standards."
---

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

Claude agents use continuous phased processing for complex multi-step work.

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

**Implementation:** Command at `~/.files/claude/commands/reflection-harder.md`. On-demand only; no tmux status bar integration.

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

**Design the feedback loop before writing code.** Before the first line of implementation, identify what "verifiably done" looks like: which tests run, which lint/type-check passes, which grep/diff confirms the output is correct. The verification path is part of the design, not an afterthought.

### Verification Rigor Tiers

Rigor is a budget spent where it buys detection, not a level to maximize. Pick the cheapest tier that would catch a fault in the deliverable at hand.

| Tier | When | What runs | Typical cost |
|---|---|---|---|
| **V0 — Inline** | Within a task, after each edit | Type-check / compile / lint on the changed files; read the diff | seconds |
| **V1 — Scoped** | Task exit gate (the default) | Tests covering the changed file or package only, plus the task's own `Feedback signal:` from `plan.md` | seconds–low minutes |
| **V2 — Branch** | Once, after the last task, before the final review | Full test suite + full lint/type-check | minutes |
| **V3a — Wave review** | At each dependency-graph wave boundary (see `shape.md` Stage 4) | Review agent over the diff **since the last review checkpoint** only | one bounded dispatch |
| **V3b — Branch review** | Once, after V2 passes | Review agent over the complete branch diff | one dispatch |
| **V4 — Post-merge CI** | After merge, where CI exists | The merged commit's own check-runs, classified against the pre-merge commit | polled, async |

Rules:
- **V1 is the per-task default. Do not run V2 between tasks.** A full suite per task is near-pure duplication of V2: it re-verifies untouched code N times to catch regressions that a per-task commit plus V2 already localizes by bisect.
- **Commit per task.** This is what preserves attribution when V2 or V3 finds something. Without it, the argument for V1-only collapses and you owe a fuller check per task.
- **V3 finds what V1 cannot.** Cross-task interaction faults, pattern-level bugs, and spec drift are invisible to any per-task check regardless of its breadth. Widening V1 does not substitute for V3 — it just spends the budget in the wrong place.
- **Review is the detector, so review cadence — not test breadth — is the lever on compounding.** Since a per-task test catches approximately none of the faults that actually occur (see the audit below), running tests more often does nothing to stop a fault from compounding across a long plan; running *review* more often does. Hence V3a: at each wave boundary, review only the diff since the last checkpoint. That diff is bounded (it does not grow with the branch), so the cost is roughly constant per checkpoint, and a finding is attributable to the handful of tasks in that wave rather than to the whole branch.
- **V3a does not replace V3b.** The audited cross-task drift fault (`c19fe01`) was three gaps that appeared only once Task 1 and Task 3 were both merged — each task locally coherent, jointly inconsistent. An incremental review that never sees the assembled whole cannot find that class. Run both.
- **Anchor the checkpoint to structure, not to a count.** Wave boundaries come from the plan's own dependency graph. Do not substitute "every N tasks" — that is an invented threshold of exactly the kind this section warns about below.
- **V3 and V4 are where faults are actually found — do not skip them to save time.** Audited against this repo's own history (14 post-implementation faults over ~6 months, commits `51c57bd`, `331d3af`, `31a6d52`, `c19fe01`): 12 were found by review reading the diff, 2 by post-merge CI, and **0 by a test suite run at any breadth**. The faults were injection vectors, a fail-open safety gate, stale cross-invocation state, error-path ordering, and cross-task doc drift — none of which a test written for the task's happy path catches, regardless of how wide it runs. V1 is where the *time* is saved; V3/V4 are where the *quality* is preserved. Trading V3 or V4 away for speed is not the same trade as narrowing V1, and is not authorized by this section.
- **A clean local verify is not a CI pass.** One audited fault (`31a6d52`) was a task's own regression test passing locally and failing on main's post-merge CI. Local rigor of any tier cannot catch an environment difference — that is what V4 is for.
- **Escalate on evidence, not on anxiety.** Promote the remaining tasks from V1 to V2 when: V2/V3 surfaces a fault a scoped check should have caught, or a task touches shared/global state (schema, config loader, build system, auth, a widely-imported module). State the escalation and its trigger in narration. Do not invent additional numeric trip-wires without validating them against real run history first — an earlier draft of this section carried a "two consecutive tasks fail their scoped check" trigger that the audit showed had never once fired, because scoped checks were not what was failing.
- **De-escalate too.** Once the trigger's cause is fixed and one task passes clean at V2, drop back to V1.
- **Where the suite is thin, V1 and V2 are the same empty check.** `bin/bugfix-worker` carried 9 of the 14 audited faults and has no test file; `make test` runs two unrelated pytest files. Before budgeting tiers, confirm the tier you are relying on actually covers the changed code — if it does not, the detection load falls entirely on V3, and the review is not optional.
- **Brief the reviewer with the fault classes below.** An unguided "review this diff" dispatch relies on the reviewer happening to look in the right place. Each class below is derived from a fault that actually shipped past a green check, so none is speculative.
- **Break-checks are per harness, not per test.** Falsifiability (Constitution IV) is satisfied by one break-check the first time a harness is wired up — not by re-breaking an established suite each task.

The accepted tradeoff: a local, short-lived error rate is cheaper than uniform maximum rigor. A *compounding* error rate, or one whose cause can no longer be attributed, is not.

### Review Fault Classes

What V3a/V3b should actively hunt for. Derived from the 14 audited faults — every class below is a fault that actually shipped past a green check, not a hypothetical. Include this list in the review dispatch brief.

1. **Untrusted input reaching a path, lock, identifier, or interpreter.** Does a value originating outside the process (an LLM-generated slug, a cross-session message, a filename) reach a filesystem path, lock name, session name, or — worst — get spliced unescaped into a shell or `python -c` string? Validate against an allowlist *before* first use, and pass via environment, not string splice. (`51c57bd`: both, in one script.)
2. **Fail-open error handling.** When a command inside a safety gate errors, does the gate report clean or report failure? An error swallowed into an empty result set reads exactly like "nothing wrong." Every gate must fail loud. (`51c57bd`: a `git diff` error produced a falsely-empty risky-paths list — the one check meant to catch secrets-adjacent changes was failing open.)
3. **Stale state.** Two shapes: a reused identifier binding to state left over from a prior run, and a diff/merge-base computed without fetching first. Both produce confidently wrong answers from correct-looking code. (`51c57bd`: both.)
4. **Error-path ordering.** Does any failure get raised *after* an irreversible action already completed — a push, a merge, a write? The fix is ordering, not a better message. (`51c57bd`: a `git branch -f` failure aborting after the push had landed.)
5. **Divergent parallel branches.** When the same logic is implemented N times (per runner, per platform, per path), diff the branches against each other. One of them is usually different in a way nobody intended. (`51c57bd`: log truncation differed across three of them.)
6. **Cross-task drift.** For each task merged this branch, grep for the claims other tasks' files make about it. Two locally-coherent changes are routinely jointly wrong — this is the class per-task checks structurally cannot see, and it is why V3b exists. (`c19fe01`: three SKILL.md gaps after Tasks 1 and 3 merged.)
7. **Validation that contradicts its own stated intent.** Read each validator against the sentence describing what it rejects. Charsets are the usual offender. (`331d3af`: the charset permitted `.`, so `".."` passed a check written to forbid traversal.)
8. **Local/CI environment divergence.** A clean local verify is evidence about your machine. Where CI exists, the claim "done" is not supported until V4. (`31a6d52`: a task's own new regression test passed locally, failed on main's post-merge CI.)

When a review finds a fault outside all eight, add it here — that is how the list stays worth briefing.

**Harness verification (false-red / false-green discipline).** When writing tests in new test files, new packages, or any setup where harness wiring is uncertain:
1. Write the failing test
2. Break the implementation in a targeted way (wrong return value, removed function body, inverted condition) to confirm the test catches that specific failure
3. Restore the implementation and confirm green
4. Only then proceed — a green result you haven't confirmed can turn red is a false green and tells you nothing

This applies once per new harness, not to every test in an established suite and not repeated on each task that adds tests to a harness already break-checked.

**Return only when self-validated.** Do not surface results, ask for human confirmation, or request feedback on something you can verify yourself. Run the tier the task calls for (V1 by default, see Verification Rigor Tiers), confirm the diff, check the output — then return with evidence of completion, not a question.

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
