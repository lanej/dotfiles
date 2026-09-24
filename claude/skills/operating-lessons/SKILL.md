---
name: operating-lessons
description: "Situational verification, delegation and coordination rules covering sub-agent output trust (numeric claims, data availability, infra completion, hallucination), peer-session coordination procedure, which agents can honor the receipt contract, worktree and briefing gotchas, interactive-tool and auto-approve pressure cases, search and 1Password lookup gotchas, and misc technical corrections (BigQuery join fanout, replace_all safety, interactive Bash prompts, git worktree cleanup ordering). Use before messaging a peer session or asking Josh a scoping/sequencing question, when reviewing sub-agent output before surfacing it, when briefing an Agent call or choosing an agent for a file-writing receipt contract, when targeting a worktree, finishing/merging a worktree-isolated branch (including when the primary/orchestrator session itself — not a sub-agent — hits a git-operation refusal targeting the shared main checkout), before running an apply or other interactive tool under auto-approve, before searching for an internal company document, or double-checking a specific verification or safety procedure referenced from CLAUDE.md. Don't use for general TDD, git commit conventions, or domain-specific language gotchas already covered by the git, javascript, python, or bigquery skills."
---

# Operating Lessons

Situational rules pulled out of CLAUDE.md to keep it lean — each fires in a specific circumstance rather than every session. CLAUDE.md carries the general principle for each family below as an always-loaded default; this file is the detail/backstop layer, not the primary enforcement. Every rule is backed by a memory file with the full incident unless noted otherwise.

The rules live in three reference files. **Read the one matching your situation before acting — the index below is a locator, not a substitute for the rule.** When in doubt which applies, read `delegation.md`: it covers the largest share of the recurrences.

## `references/delegation.md` — is this reported result actually true?

Read before surfacing a delegate's output, and before reporting any result you haven't independently checked.

- Sub-agent numeric, cost, data-availability and infra-completion claims are unverified intent until you run the check yourself
- Resumed sub-agent threads drift; killed agents misreport status; git push/merge and "clean fast-forward" claims need direct confirmation
- Unattributed repo changes: a second session on the same repo is the mundane cause — resolve provenance before committing
- Verification-before-reporting family: aggregate counts, refactor output, multi-file refactors, architectural pivots, full-stack wiring, parallel frontend/backend contracts, single-example metrics, pricing generations, and **rendered document/page content** (a clean exit code is not proof — read the rendered output; recurred 5× across three projects)
- Bug attribution: a familiar-looking failure is not confirmed to share the old root cause; a dead field in a user's hint doesn't mean the lead was wrong
- **Peer-session coordination**: the full `ListAgents` → `SendMessage` procedure behind CLAUDE.md's trigger — name-matching, bounded timeout, what a peer can and cannot answer, and why a peer's agreement never authorizes a consequential action
- **Receipt contract**: which agents can honor "write findings to a file, reply in three lines" — read-only agents cannot, `code-reviewer` structurally cannot
- **Delegation vs handoff**: the mechanism behind the routing rule

## `references/worktrees.md` — worktrees, briefings, concurrent sessions

Read when briefing an Agent targeting a worktree, or finishing, merging, or cleaning up a worktree-isolated branch.

- Briefings must state the worktree's absolute path; prefer `Agent(..., isolation: "worktree")`
- `EnterWorktree` is pinned to the session's original root; process/port kill scope binds you directly, not just sub-agents
- `gh pr checkout` is not worktree-safe; `core.hooksPath` collides across worktrees; `git worktree remove` has an ordering requirement
- Merging or pushing a worktree branch into `main`; concurrent multi-session repo drift; no duplicate background commands
- npm/yarn workspaces and pytest in a fresh worktree; a dispatched Agent can inherit an unexited Plan Mode and dead-end

## `references/technical.md` — specific tool, query, document and design corrections

Read when double-checking a procedure this index names.

- `replace_all` safety; script argv verification; double-backgrounding inside `run_in_background`; interactive prompts in non-interactive Bash (and when `--quiet` is legitimate)
- API result ownership; **BigQuery event-level join fanout** (silent aggregate inflation); Vertex has no `/fast`
- Document editing: dependency/sibling-doc grep after *every* change that moves a number, including rebases; citations in externally-shareable artifacts
- Architecture: extend the existing codebase idiom before proposing a new layer; name the optimal layer explicitly; query the real distribution before picking a threshold; validate a new classification bar against a known-good example before scaling it
- **Interactive tools and auto-approve**: the Stop-hook/`/goal` pressure cases behind CLAUDE.md's rule, and the gate that was built and revoked
- **Search and credential gotchas**: why no web search can reach an internal company document; 1Password dual-account lookups
- Misc: Dockerfile `COPY`, TOML comment placement, monorepo git pathspec double-prefixing, cross-task bug-class propagation, no hard-wrapping markdown, implementer-brief gaps (git-staging discipline, evidentiary rigor), `CronCreate`/`ScheduleWakeup` cron-math verification

## Error Handling

- If a cited memory file no longer exists, treat the rule as still in force and note the missing citation — don't drop the rule on that basis alone.
- If a rule here conflicts with something newer in CLAUDE.md, CLAUDE.md wins — this file is the detail layer, not the source of truth.
- If unsure whether a specific check applies to the current task, run it — the cost of an unnecessary verification is far lower than a fabricated or stale claim reaching the user.
