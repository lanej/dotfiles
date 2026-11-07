---
name: builder
description: Use when designing, implementing, modifying, debugging or reviewing software. Build small working paths, protect retained behavior and apply Pragmatic Hexagonal Architecture with proportionate evidence.
---

# Builder

This core applies to software produced by humans or agents. `MUST` properties are required; `SHOULD` techniques are defaults whose departures need concrete justification. Apply it within the changed capability, preserving project constraints and instruction precedence. Passing checks, instruction following, directory layout and written explanations cannot establish software compliance.

## Required properties

- **PHA-P01 — Explicit expectations:** Consequential behavior MUST have identifiable contracts, invariants, assumptions and applicability conditions. Distinguish intended behavior from current implementation. Existing types, policy sources or independent acceptance examples suffice; a small function contract needs no report. Provisional behavior MAY have bounded unresolved expectations; do not present it as a guarantee.
- **PHA-P02 — Inspectable decisions:** Domain decisions MUST be exercisable and inspectable with explicit inputs and relevant state. Hidden clocks, randomness, environment reads or infrastructure MUST NOT unnecessarily obstruct reproduction. Determinism is a default; stochastic or concurrent behavior MAY expose seeds, distributions, ordering or bounded observations. State remaining reproduction limits.
- **PHA-P03 — Observable effects:** Software MUST distinguish intentions, attempts, confirmations, failures and unknown outcomes wherever conflation changes a consequential conclusion or next action. Local return values/errors may suffice; remote effects MAY need bounded reconciliation. Missing confirmation remains unknown.
- **PHA-P04 — Preserved evidence:** Translation, normalization, retries, errors and aggregation MUST preserve information needed to challenge consequential conclusions. Keep observations, predictions, assumptions and inferences distinct. Preserve sufficient evidence under privacy, security, retention and cost limits; use redaction or summaries where sufficient. If verification becomes impossible, expose the limit or narrow the claim.
- **PHA-P05 — Revisability:** Consequential policies and assumptions MUST have identifiable owners and boundaries; correcting a disproven assumption MUST permit localized changes wherever practical. Genuine cross-cutting invariants MAY require coordinated changes: name that coupling. Locality has no file-count rule; convenience or “legacy” alone cannot justify unrelated reconstruction.
- **PHA-P06 — Operational falsifiability:** Consequential claims MUST admit accessible contradictory evidence under stated conditions: **claim → applicability conditions → observable contradiction → evidence source → interpretation limits**. Use existing contracts, tests, results or runtime mechanisms; no claim registry or per-function document is required. Expose missing evidence and consequential uncertainty. Provisional claims MAY lack evidence but MUST expose the gap and limits.

Specify what could contradict a claim before treating evidence as confirmation. Contract claims need independent expectations; environment/provider/customer-outcome claims need external observations. Account for sampling, delays, confounding and unavailable evidence where relevant. Tests copying the production algorithm provide no independent oracle; a green check establishes only exercised behavior and conditions. Distinguish a violated contract, a failed environmental assumption and an outcome the contract never guaranteed. Preserve relevant contradictory evidence before proposing a correction.

## Default architecture

- **PHA-A01 — Functional core:** Domain meaning, policy and decisions SHOULD be independent of effectful infrastructure, with external facts supplied explicitly. Atomic database constraints MAY enforce authoritative invariants; retain an inspectable contract and evidence of actual enforcement.
- **PHA-A02 — Imperative shell:** The shell SHOULD own orchestration, I/O, composition and effects; business decisions SHOULD remain identifiable outside transport, storage and vendor glue. Small handlers MAY make explicit, exercisable simple decisions directly; isolation-dependent transactional decisions MAY stay near storage.
- **PHA-A03 — Thin canonical model:** Normalize only application-owned concepts while preserving consequential distinctions and provenance; models SHOULD NOT force materially different providers into false equivalence. Direct provider types MAY fit where no shared concept is owned. Lossy summaries MAY serve bounded purposes while preserving PHA-P04/P06 limits.
- **PHA-A04 — Selective ports:** Introduce interfaces for demonstrated substitution or meaningful isolation. Prefer explicit integrations retaining capabilities; a boundary SHOULD simplify the whole workflow, including failures and diagnostics. Direct calls are appropriate without a useful boundary; test doubles alone cannot justify abstraction.
- **PHA-A05 — Minimum structure:** Organize by capability/locality with minimum supporting structure. Limited duplication can avoid premature coupling; shared genuine invariants justify shared mechanisms, and duplication must not hide conflicting obligations. No universal layers, tree, framework or language is required.
- **PHA-A06 — External clients:** Prefer official SDKs, otherwise authoritative generated clients. Handwritten clients need a concrete constraint such as unsupported runtime, missing capability, dependency limits or absent specification. Preserve protocol expectations/error distinctions; official provenance does not prove correctness.

Scale structure and evidence to consequence and complexity. Small utilities need no interface hierarchy; distributed workflows may need reconciliation. No universal decision logging, permanent input retention, event sourcing, replay infrastructure or new observability platform is required. Adopt incrementally; identify inherited limits affecting changed behavior without unrelated rewrites or blanket compliance claims.

Record material deviations near the contract: **requirement ID → concrete constraint → retained protections → revisit condition**. A prevented MUST property remains an explicit compliance gap; justified alternatives to SHOULD techniques do not erase contradictory evidence.

## Working increments

Establish the smallest meaningful executable behavior, then simplify and expand. Resolve consequential uncertainty with a result that could contradict the approach; failure can be useful. For known requirements an early test may fit; for feasibility use a credible experiment at the relevant real boundary. Mocks cannot resolve uncertainty about the boundary they replace. Use safe, authorized experiments without bypassing permissions or production protections.

TDD is optional; verification is mandatory. Once meaningful behavior will be retained or its conclusion relied on, capture repeatable protection before expansion or material restructuring. Prefer extending an existing behavioral detector; protect intended behavior rather than speculative internals and preserve failures where practical. Characterize old observed behavior separately from required behavior.

Discarded experiments do not automatically need a permanent suite. One-off manual demonstrations do not provide regression protection: automate consequential retained behavior where practical, otherwise preserve a reproducible check and its limits. Address security, performance and failure handling initially when they determine viability; never defer safeguards against irreversible harm.

Plan working-and-verifying increments together, without prescribed commit sequences or reports per loop. Construction feedback does not waive delivery gates, reviews, CI or explicit test-first mandates. Review protection of retained behavior, not test authorship order unless mandated. Report specific requirement violations, affected behavior, contradictory evidence, assumptions and verification gaps.

## Load detail when needed

Read [the architecture standard](references/standard.md) for capability boundaries, models, adapters, consequential effects or architecture reviews for rationale, evidence and limits. Read the [construction policy](references/construction.md) for uncertain feasibility, retained prototypes, manual-only protection, security/performance viability or ambiguity about verification timing. Read [instruction routing](references/instructions.md) when configuring host loading.

For concrete examples, run `python3 scripts/check_examples.py` from this skill directory. These exercise example behavior and detector sensitivity, not real providers or assistant adherence.
