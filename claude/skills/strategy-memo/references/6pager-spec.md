# Amazon 6-Pager Specification — Strategy Memo Edition

This document reconciles the original Amazon 6-pager format with the specific patterns proven in `pre-read.qmd`. Where they differ, `pre-read.qmd`'s approach takes precedence — it was written for a real leadership session and is the canonical reference.

## The Core Philosophy (unchanged from Amazon)

A 6-pager is a **narrative memo, not a presentation**. Writing in complete sentences forces deeper clarity than bullet points. The reader internalizes the argument rather than watching someone present it.

**Why it works:**
- Sentences require complete arguments — you cannot hide behind a label
- Self-answering: questions raised on page 2 are answered by page 4
- Equal playing field: no pre-meeting lobbying determines outcomes
- Silent reading guarantees everyone has the same context

## Format Requirements

**Length**: 6 pages is the Amazon canon. Up to 8 pages is acceptable when the extra pages contain figures that carry narrative weight — not prose overflow. A figure does not "cost" a page if it replaces 300 words of description.

**No bullet points in narrative sections.** Bullets are acceptable only for the strategic questions in Part 4.

**Evidence-based**: every claim must be supported by data visible in the same document. "Significant" losses — cite the number. "Growing" — show the chart.

**Self-answering**: the document must be complete on its own. If the reader has questions, they should be questions of judgment (Part 4), not questions of comprehension.

## Document Structure (proven in pre-read.qmd)

Amazon's generic structure (Introduction, Metrics, Prior Period, Goals, Resources, Risks) is adapted for a strategic inflection-point memo. The standard sections are replaced by:

### Introduction: Intent Declarations

Three statements of "I intend to…" followed by the evidence and logic that justifies them.

> "I intend to build the decision layer — the intelligence component that transforms carrier selection from cost-minimization into multi-dimensional optimization — as EasyPost's primary product surface."

The introduction ends with "How These Sessions Work" — a brief explanation of the two-session format (pressure-test the policy in Session 1, design coherent actions in Session 2).

**IBL framing replaces standard planning language:**
- Use: "I intend to…" (not "We should consider…")
- Use: "What am I missing?" (not "Here's the plan")
- Use: Active voice — "We must move" (not "It is recommended that we move")
- Avoid: Hedging, defensive framing, top-down action items

### Part 1: The Situation

The diagnosis. What is true about the world right now that demands a strategic response?

**Structure:**
1. Opening paragraph — the problem in plain terms, no jargon
2. A customer or evidence quote (LaTeX `\begin{quote}` block) — grounds the abstract in the concrete
3. Primary visualization — the data that makes the problem undeniable
4. Analysis prose — what the data shows and why it matters
5. Continuation — the structural risk or second-order consequence

**What belongs here:** observed facts, quantified problems, current state evidence.
**What does not belong:** solutions, intent statements, tactical plans.

### Part 2: Why This Intent

The strategic rationale. Why does the proposed direction address the situation better than alternatives?

This section answers: "Given what we just learned about the situation, why is this the right response?"

**Common patterns:**
- A historical parallel ("Stripe did this for payments…")
- A data moat argument ("Every shipment that passes through Luma improves the model for everyone else")
- A revenue/unit economics case ("The spread-to-SaaS ratio tells us where value is going")
- A market position argument ("The first carrier intelligence layer to achieve cross-carrier signal at scale sets the standard")

**What belongs here:** strategic logic, analogues, economic rationale, competitive positioning.
**What does not belong:** tactical product features, timelines, sprint plans.

### Part 3: What This Requires

The dependencies. What must be true for the strategy to succeed?

Three consistent sub-headings (not numbered):

**Technical Competence** — the engineering capabilities required. Focus on architecture and data, not features.

**Organizational Clarity** — ownership, sequencing, what stops. Explicit about what the organization must stop doing to create capacity.

**Execution Discipline** — the behavioral commitments. How decisions get made. What "done" looks like.

**What belongs here:** capability requirements, organizational pre-conditions, execution principles.
**What does not belong:** "Risks and Mitigations" framing (it invites defensive thinking), detailed roadmaps, resource requests.

### Part 4: Questions to Refine Intent

Exactly 3–5 strategic choices that the document does not resolve. These are not rhetorical questions — they are genuine decision points that Session 1 must surface or Session 2 must answer.

**Format:** Bold question, followed by 2–4 sentences framing the choice — what each path implies, what the cost of getting it wrong is.

**What belongs here:** genuine strategic ambiguities, resource allocation choices, sequencing decisions, boundary decisions.
**What does not belong:** more than 5 questions (signals lack of clarity about what matters), tactical questions (feature priorities, sprint sequencing), questions with obvious answers.

## Writing Quality Standards

### Precision

Every number in prose must either:
1. Flow from a `{python}` inline expression referencing a named variable, or
2. Be a non-factual stylistic value ("25 minutes of silent reading")

Never: `Analysis of 847 lost opportunities` — this becomes stale and cannot be validated.
Always: `` Analysis of `{python} f"{total_deals:,}"` lost opportunities ``

### Prose rhythm

The pre-read.qmd prose has a specific rhythm: short declarative sentences followed by longer analytical ones. No hedging. No defensive qualifiers. Concrete → analytical → implication.

Example (from Part 1):
> "Status quo --- prospects who evaluated EasyPost and produced no signal about why they did not proceed --- accounts for 74% of lost revenue, or $74M. 22% of closed-lost opportunities carry no recorded reason at all. That is not just a CRM hygiene problem --- it is a value gap."

### Customer quotes

Use real quotes when available. Format with LaTeX `\begin{quote}`:

```latex
\begin{quote}
\small\itshape
"Quote text here."

\upshape---Name, Organization, Date
\end{quote}
```

The quote should illustrate the mechanism described in the surrounding prose — not just support the thesis, but reveal _why_ the situation is as it is.

### Bold call-outs

For the single most important framing in each part, use a bold quote block:

```latex
\begin{quote}
\small\bfseries
The challenge is not competition. It is invisibility.
\end{quote}
```

Use sparingly — once per part at most.

## Where pre-read.qmd Deliberately Deviates from Amazon Canon

| Amazon 6-pager | pre-read.qmd approach | Rationale |
|---|---|---|
| "Risks and Mitigations" section | Removed entirely | Invites defensive framing; risks belong in Part 4 as strategic choices |
| "Goals and Initiatives" section | Replaced with "What This Requires" | Initiatives are Session 2 output, not pre-read content |
| "Key Metrics" section | Integrated into Part 1 and Part 2 | Metrics without narrative context are just numbers |
| 6 pages hard limit | Up to 8 pages acceptable with figures | Figures carry more information per page than prose |
| Any format for intent | IBL "I intend to…" declarations | Specific to the leadership framework of these sessions |
| Pre-meeting distribution | Read silently in the room | Guarantees equal context; the warm feeling of being read |

## The Silent Reading Protocol

The document is read silently at the start of each session (25–30 minutes). This is not optional — it is the mechanism that guarantees equal context.

**Implications for writing:**
- Every sentence must work without a speaker to explain it
- Jargon must be defined or avoided
- Arguments must be complete within the document
- The reader must not need to ask "what does that mean?" — only "is that right?"
