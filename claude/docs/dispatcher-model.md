# The Dispatcher Model

A proposed design for keeping the main session a coordinator. The ledger, pointer briefs, and freshness hook below are not implemented; only the receipt return contract has been adopted. The cycle estimates below are illustrative, distinct from the measured receipt-only results in `../evals/receipt-contract/RESULTS.md`.

## The measurement this is built on

One live session, 123K chars (~31K tokens):

| block | share |
|---|---|
| `tool_result` (what comes back) | 51.4% |
| `tool_use` (what you send) | 37.1% |
| assistant text | 11.0% |
| **user conversation** | **0.5%** |

Top 10 tool results = 42% of all context.

Two conclusions:

1. **Conversation is not the problem.** Protecting "room for the user's
   conversation" protects 0.5% of the budget. The enemy is tool I/O.
2. **Outbound costs nearly as much as inbound.** A six-field brief averages
   ~1KB. Dispatching is not free — every dispatch spends context twice.

A dispatcher that writes rich briefs and reads rich summaries burns context
*faster per unit of work delivered* than one that does small work inline.
That is why "delegate more" alone does not scale.

## The core move: pass pointers, not payloads

Every dispatch is a round trip. Make both directions references.

```
                 BY VALUE (now)            BY REFERENCE (proposed)
brief out    ~1,000 chars of prose    →    "Read work/<slug>/STATE.md; do task 3"   ~80
result in    ~1,400 chars of summary  →    "done; wrote findings/auth.md; no blk"   ~60
             ─────────────────────         ─────────────────────
             ~2,400 chars/dispatch         ~140 chars/dispatch
```

~17x per cycle. The context that used to live in your window now lives on
disk, where agents read it directly and you don't pay for it.

## The ledger

One directory per task: `.claude/work/<slug>/`

```
STATE.md              # source of truth. goal, decisions, open questions,
                      # file inventory, task list w/ status. YOU maintain this.
findings/<agent>.md   # each agent writes its own. never returns prose.
artifacts/            # anything produced
```

`STATE.md` replaces the six-field brief. It is written once, amended
incrementally, and read by every agent. Context, Domain, and Constraints stop
being retyped per dispatch — they are a file.

### Contract

**Inbound (your brief):** a pointer plus a task id. Nothing else, unless the
task needs something genuinely not in STATE.md.

**Outbound (agent return):** at most three lines.
```
status: done | blocked | context-insufficient
wrote:  findings/explore-auth.md
blockers: none
```
Prose findings go in the file. You read the file only when you must decide
something — often never.

## Why this fixes the briefing floor

The floor exists because a dispatcher must *hold* context to write a good
brief. With a ledger it must only *maintain* it. Writing STATE.md is bounded
work you do once per decision; writing briefs is unbounded work you do per
dispatch. The floor moves from "how much can you remember" to "is the file
current" — which is checkable.

## Why /handoff becomes trivial

Today `/handoff` reconstructs context by digesting a 335KB JSONL because
nothing durable exists. With a ledger, handoff is "read STATE.md." The
transcript digest becomes a fallback for when the ledger is stale or missing,
not the primary mechanism.

This demotes handoff from a terminal, once-per-session event to something you
can do freely — which is closer to what you actually wanted.

## Enforcement, not norms

Your own record: the fork write-suppression rule failed six times as prose,
including once immediately after the model read the incident writeup. Prose in
a brief is advisory. Two mechanisms that are not:

1. **Bake the contract into agent definitions.** `operating-lessons:76` already
   makes this point: an agent's own definition is always loaded, a brief's
   instructions are not. Define `ledger-worker` variants whose system prompt
   *is* the write-to-disk/terse-receipt contract. Then the contract holds even
   when your brief forgets it.
2. **A Stop hook that checks ledger freshness** — if `git diff` shows changed
   files that `STATE.md` does not mention, say so before the turn ends.

## When NOT to use this

Ceremony has a floor cost. Skip the ledger for anything under ~3 dispatches or
a single session's worth of work; a direct `Agent` call is cheaper. The ledger
earns its keep on multi-hour, multi-agent tasks — which is exactly where the
current model breaks down.

## Failure modes this introduces

Honest accounting of what gets worse:

- **STATE.md staleness becomes catastrophic.** It is now the single source of
  truth for every agent. A stale ledger silently misbriefs everything
  downstream. Today's polluted-but-accurate context degrades gracefully; a
  stale ledger does not. This is the main risk and needs the freshness hook.
- **Concurrent writes.** Parallel fan-out into one directory collides. Per-agent
  filenames are mandatory, not stylistic.
- **A terse receipt can lie more cheaply than a long one.** "status: done" is
  three tokens of unverified claim. Your existing verification rules
  (`operating-lessons` § sub-agent output) apply harder here, not less.
- **`CLAUDE.md:21` conflicts.** The six-field rule must become conditional:
  six fields for a cold one-off dispatch, pointer brief when a ledger exists.

## Migration

1. Amend `CLAUDE.md:21` to make six-field briefs conditional on there being no
   ledger.
2. Add one `ledger-worker` agent definition carrying the receipt contract.
3. Rewrite `/handoff` step 1 to prefer `STATE.md` and fall back to the
   transcript digest.
4. Add the freshness Stop hook.
5. Run it on one real multi-hour task before adopting further.
