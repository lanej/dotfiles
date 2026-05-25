---
description: "Orchestrate the full document lifecycle: Socratic interrogation → research → thesis brief → draft → reader critique → revision → release. Use for any document that matters: proposals, strategy docs, 6-pagers, announcements, decision memos, technical writeups. Every claim is traceable to a recorded source or explicit first-principles reasoning."
argument-hint: [document description or path to existing doc]
allowed-tools:
  - Read
  - Write
  - Edit
  - Task
tags:
  - writing
  - workflow
  - documents
---

# /compose — Document Shaping Workflow

Purpose: orchestrate the cognitive lifecycle from ambiguous writing intent to a releasable document where every claim is traceable to recorded evidence or explicit first-principles reasoning.

The goal: a document where inaccuracies cannot silently persist because every claim either has a recorded source behind it or is explicitly labeled as first-principles reasoning.

## Lifecycle

```text
Intent → Interrogate → Research → Brief → Draft → Critique → Revise → Release
```

## Artifact Model

All stages operate on explicit artifacts inside:

```text
.compose/YYYYMMDD-HHMMSS/
├── brief.md        # interrogation output + section map
├── sources.md      # evidence ledger: one entry per recorded source
├── draft.md        # document in progress
├── critique.md     # reader attack findings
└── release/
    └── doc.md      # final output (no annotations)
```

### draft.md Status Header

Every `draft.md` must begin with:

```
Status: Brief | Outlined | Drafted | Under Critique | Reconciling | Released
```

The current state must be determinable from the artifact alone — never from the conversation.

### sources.md Format

```markdown
## [S001] [Title of source]
- **Source**: [where it came from]
- **URL**: [link if available]
- **Date**: YYYY-MM-DD
- **Confidence**: low|medium|high
- **Claim**: [what this source supports]
```

Each entry gets a sequential ID (S001, S002, ...). Draft claims reference these IDs via footnotes: `[^S001]`. Claims without a footnote reference are unsourced.

## Adaptive Rigor

### Trivial
Examples: casual update, internal Slack message, quick note.
Behavior: skip to Draft. No sources.md required. Write a one-line skip justification to `.compose/TIMESTAMP/skip.md`.

### Moderate
Examples: memo, internal proposal, announcement, decision doc.
Behavior: Interrogate → Brief → Draft → Critique → Release. Record sources for external or quantitative claims. First-principles reasoning does not require a source entry.

### Complex
Examples: 6-pager, strategy document, external publication, board memo, anything with cited claims.
Behavior: full workflow, no stages skipped.

## Workflow Stages

### Stage 1 — Interrogate

Conduct Socratic interrogation before any writing. Surface hidden assumptions now, not in revision.

Ask all six questions. Do not proceed until all are answered:

1. **Reader**: Who specifically will read this? What is their role, context, and prior knowledge? What objections will they arrive with?
2. **Purpose**: What must the reader believe, decide, or do after reading? One sentence.
3. **Success**: What does "this document worked" look like, concretely? What changes downstream?
4. **Evidence**: What facts, data, or reasoning support the core claim? What is not yet known?
5. **Constraints**: Length, tone, format, deadline, sensitivity, distribution scope?
6. **Cost of inaction**: What is the measurable cost of NOT making this change or decision? If this document is a budget or approval request, what does the ask produce in quantifiable return? If the answer is "unclear," that is evidence the thesis needs tightening before drafting.

Record answers in `brief.md` under `## Interrogation`.

**Pause here.** Do not proceed until reader, purpose, and success criteria are explicit.

### Stage 2 — Research

Search for evidence before drafting. Do not write claims you cannot support.

1. Search workspace KB (`mcp__qmd__query`, `rerank: false`) for prior analysis, domain context, existing positions.
2. Search external sources (`mcp__codex__codex`) for data, benchmarks, precedents — only for external claims.
3. Record each piece of evidence in `sources.md` with its full citation (see format above).
4. Record what was searched and NOT found — note gaps in `brief.md` under `## Evidence Gaps`.

**Classification of claim types** (established now, enforced in Stage 4):
- **Sourced**: has a `sources.md` entry with a footnote reference in the draft (`[^S001]`)
- **Organizational** (`[^org: description]`): facts about EasyPost's own infrastructure, team composition, or internal state that are author-attested but not externally sourced. Not unsourced — but must be explicitly labeled. Example: `[^org: EasyPost runs Envoy as its internal proxy]`.
- **Unsourced**: neither of the above — inaccuracy risk, flagged in critique

There is no first-principles exemption. If a claim is genuinely definitional (a protocol property, a language semantic, a mathematical fact), write the reasoning into the prose — the sentence itself is the justification. If you cannot write the reasoning naturally into the prose, that is a signal the claim needs a source. The Skeptic in Stage 5 is the backstop for anything that feels asserted.

### Stage 3 — Brief

Write the thesis-driven brief before any prose.

`brief.md` must contain:

```markdown
## Thesis
[One sentence. Falsifiable. The single claim the document proves.]

## Audience
[Who. What they know. What objections they will have.]

## Success
[What changes downstream if this works.]

## Section Map
| Section | Claim | Backing | Audience Assumption |
|---|---|---|---|
| [name] | [what this section proves] | [source ID OR "first-principles: [reasoning]"] | [what reader already knows] |
```

Every section must have a claim and explicit backing. If you cannot state the backing, you do not have the evidence yet — return to Stage 2.

**Transition gate**: every section in the Section Map has either a source ID or an explicit first-principles label.

### Stage 4 — Draft

Write against the Brief. Every section fulfills its stated claim.

Rules:
- One idea per sentence
- No hedging, no throat-clearing, no summaries of what you just said
- Every quantitative or comparative claim annotated: `[^S001]` for sourced, `[^org: description]` for internal organizational facts
- If a claim lacks either annotation: stop, return to Stage 2, record the source before continuing
- Preserve structure only where it aids navigation

Draft is complete when every section in the Section Map is addressed and no unannotated claims remain. Set status to `Drafted`.

### Stage 5 — Critique

Run two independent reader attacks plus a source audit. Critics receive only `draft.md` — no brief, no sources, no conversation history. Low-context confusion is diagnostic.

**Reader 1 — Naive Reader**: No prior knowledge assumed. Finds: undefined terms, missing context, logical gaps, places the document fails a first-time reader.

**Reader 2 — Skeptic**: Adversarial. Finds: claims that feel asserted without support, sections that could be cut without loss, hedging that undermines authority.

**Source Audit** (primary agent — requires access to sources.md):
- Every `[^Sxxx]` reference in the draft must resolve to an entry in `sources.md`
- Any claim without `[^Sxxx]` or `[^org:]` annotation is unsourced
- Source entries older than 90 days with confidence < high: flag as potentially stale
- Quantitative claims with only `[^org:]`: flag — numbers need an external source entry, not just author attestation

Write findings to `critique.md`:

```markdown
## Naive Reader Findings

## Skeptic Findings

## Unsourced Claims
[Claims in draft with no footnote annotation — inaccuracy risks]

## Stale Sources
[Sources older than 90 days at medium/low confidence]

## Distillation Check
[Generate 5 specific falsifiable questions from the Brief's thesis and section claims — BEFORE re-reading draft.md. Write them down. Then read draft.md and answer each from the text alone. Flag any question the draft cannot answer.]
```

**Pause here.** Do not revise until findings are reviewed.

### Stage 6 — Revise

Classify every critique finding before touching the draft:

| Classification | Meaning |
|---|---|
| `accepted` | Incorporated into draft |
| `rejected` | Explicitly dismissed, reason recorded |
| `deferred` | Out of scope for this version, reason recorded |

No finding may silently disappear.

For each Unsourced Claim finding: either (a) return to Stage 2 and record the source, then annotate the claim, or (b) rewrite the claim so the reasoning is self-evident in the prose and no annotation is needed, or (c) cut the claim.

For each Stale Source finding: update the source entry with current information or lower the claim's confidence level in the draft.

Once all findings are classified and sourcing is resolved, run the `distill` skill on the full `draft.md` as a mandatory whole-document pass — not section-by-section. This catches cross-section redundancy that per-section cuts miss. Distill runs after accuracy is settled so brevity doesn't obscure remaining problems. Update status to `Reconciling` before distill, `Released` after.

### Stage 7 — Release

Determine the release path before writing:
- If invoked with an existing file path (`/compose path/to/doc.md`): write the release back to that path, overwriting it.
- If invoked with a description: derive a slug from the thesis (e.g., `eng-org-consolidation-memo.md`) and write to the current working directory, or a path the user specifies.

Write the release to that path — not inside `.compose/`. The `.compose/` directory is scaffolding (artifact trail, sources, critique); it stays hidden. The released document is a normal file at a real path.

The release document contains only the document — no status headers, no `[^Sxxx]` or `[^org:]` annotations (these live in sources.md), no metadata beyond what belongs in the document itself. Where citations are appropriate for the audience (external docs, academic-style memos), convert `[^Sxxx]` references to standard footnotes with the source URL from sources.md.

## Transition Rules

Do not proceed to Draft until:
- Every section has a claim and explicit backing in the Section Map
- Evidence gaps are documented in `brief.md`

Do not proceed to Release until:
- Every critique finding is classified
- No Unsourced Claims remain
- Stale sources are updated or claims are downgraded
- Distillation check passes (Stage 5 verification probe)
- Full-document `distill` pass is complete (Stage 6 editorial cut)

If critique reveals a thesis-level problem (wrong audience, wrong purpose, core claim unsupportable by available evidence): reopen Stage 1. Do not patch a structural problem in revision.

## Usage

```bash
# New document
/compose "Q3 shipping strategy memo for board"

# Editing an existing document
/compose path/to/existing/doc.md
```

For editing an existing document: start at Stage 1 (interrogate whether the document still serves its stated purpose). Diff existing structure against the Brief; treat sections without a Brief claim as Cut candidates.
