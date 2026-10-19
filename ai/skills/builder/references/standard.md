# Pragmatic Hexagonal Architecture

## Purpose and normative language

**Architectural formulation:**

> Functional Core, Imperative Shell, a Thin Canonical Model, and Selective Ports and Adapters at genuine substitution or isolation boundaries.

**Governing objective:**

> Construct software whose behavior can be understood, whose consequential claims can be challenged by evidence, and whose disproven assumptions can be revised without unnecessarily disturbing unrelated capabilities.

This specification governs software produced by humans or agents.
It applies to new capabilities and changes within existing systems.

**MUST** identifies required software properties.
**SHOULD** identifies default architectural techniques; departures need a concrete justification.
**MAY** identifies context-dependent choices.
Requirement identifiers remain stable when wording changes.

Three concerns remain separate:

1. PHA-P requirements describe properties of the resulting software.
2. PHA-A requirements constrain architecture to support those properties.
3. Codex instructions and installation apply this standard; they cannot establish software compliance.

Directory layouts, interfaces, completed checklists, and passing CI are insufficient evidence.
Neither instruction-following nor test authorship substitutes for a required software property.
A written explanation cannot compensate for contradictory software behavior.

Consequential behavior affects meaningful outcomes, obligations, resources, access, or downstream decisions.
Scale evidence and structure to its consequences and complexity.

## Required solution properties

### PHA-P01 — Explicit expectations

- **Property:** Consequential behavior MUST have identifiable contracts, invariants, assumptions, and applicability conditions.
  Expected behavior MUST remain distinguishable from the implementation's current behavior.
- **Why:** An implementation cannot serve as its own definition of correctness.
- **Violation:** A discount calculation's only specification is its current output snapshot.
  Nobody can identify which purchases qualify or whether the threshold includes equality.
- **Evidence:** Contracts, types, independent acceptance examples, or policy sources establish intended behavior.
  A counterexample violating an invariant challenges implementation compliance.
- **Applicability:** Use existing artifacts; a function contract can suffice for a small utility.
  Exploratory behavior MAY remain provisional, with its unresolved expectations explicitly bounded.
  Do not present provisional behavior as an established guarantee.

### PHA-P02 — Inspectable decisions

- **Property:** Domain decisions MUST be exercisable and inspectable using explicit inputs and relevant state.
  Hidden clocks, randomness, environment reads, and infrastructure MUST NOT unnecessarily obstruct reproduction.
- **Why:** Contradictions need distinguishable causes, including changed facts and changed policy.
- **Violation:** Evaluating quote eligibility requires a live provider and reads an undisclosed current time.
- **Evidence:** Supplied facts and state reproduce a consequential decision without unrelated live dependencies.
  Unexpected output from the same relevant inputs challenges the claimed decision contract.
- **Applicability:** Deterministic functions are the default, not a universal purity requirement.
  Inherently stochastic or concurrent behavior MAY expose seeds, distributions, ordering, or bounded observations.
  State the remaining reproduction limits instead of promising exact replay.

### PHA-P03 — Observable effects

- **Property:** Software MUST distinguish intended actions, attempts, confirmed outcomes, failures, and unknown outcomes
  wherever conflating them changes a consequential conclusion or subsequent action.
- **Why:** Acceptance, delivery, and completion are different observations.
  A request accepted by a queue does not establish its intended effect.
- **Violation:** A timeout after submitting payment becomes either “paid” or “payment failed.”
  An automatic retry then risks duplicating an already completed payment.
- **Evidence:** Returned states, acknowledgments, correlation identities, reconciliation, or runtime measurements expose these distinctions.
  An external receipt contradicts an asserted failure; missing confirmation challenges asserted success.
- **Applicability:** Use return values and errors for local operations where those establish outcomes.
  Remote effects MAY require bounded reconciliation or explicit unresolved states.
  When confirmation is unavailable, retain uncertainty rather than inventing a terminal outcome.

### PHA-P04 — Preserved evidence

- **Property:** Translation, normalization, retries, errors, and aggregation MUST preserve information needed to challenge consequential conclusions.
  Software MUST keep observations, predictions, assumptions, and inferred explanations distinguishable.
- **Why:** A conclusion becomes unfalsifiable when processing destroys its potential counterevidence.
- **Violation:** An adapter converts provider rejection, missing data, and transport uncertainty into “no eligible options.”
  A report then claims the market offered nothing suitable.
- **Evidence:** Typed distinctions, relevant provenance, bounded diagnostic context, or independent source comparisons reveal information loss.
  A provider response contradicting the normalized conclusion exposes a violation.
- **Applicability:** Preserve sufficient evidence, not every input forever.
  Apply privacy, security, retention, and cost limits; use redaction or summaries when sufficient.
  If these limits prevent a consequential claim's verification, expose that limitation or narrow the claim.

### PHA-P05 — Revisability

- **Property:** Consequential policies and assumptions MUST have identifiable ownership and boundaries.
  Correcting a disproven assumption MUST permit localized changes wherever practical.
- **Why:** Evidence matters when software can incorporate the correction without unrelated reconstruction.
- **Violation:** Changing one provider's eligibility rule requires changing unrelated billing and notification behavior.
  Shared generic machinery silently embeds that provider's assumption everywhere.
- **Evidence:** A bounded policy change, dependency tracing, and affected behavior demonstrate change locality.
  Unrelated necessary edits or unexplained downstream changes challenge the claimed boundary.
- **Applicability:** Locality follows real capability dependencies, not an absolute file-count limit.
  A cross-cutting invariant MAY require coordinated changes; identify that genuine coupling.
  Incidental convenience or “legacy” alone does not justify unrelated reconstruction.

### PHA-P06 — Operational falsifiability

- **Property:** Consequential claims MUST admit accessible contradictory evidence under stated applicability conditions.
  Associate each claim with an observable contradiction, evidence source, and interpretation limits.
  Expose missing evidence and unresolved uncertainty where they affect consequential conclusions.
- **Why:** Agreement with implementation output cannot establish whether its assumptions or outcomes hold.
- **Violation:** Tests copy a selection algorithm, while no independent expectation can contradict its ranking.
  A dashboard reports success solely because the request handler returned HTTP 202.
- **Evidence:** Use the claim expression below in contracts, types, acceptance examples, tests, or runtime mechanisms.
  Independent expectations and external observations can disagree with the implementation.
- **Applicability:** No separate claim registry or per-function document is required.
  A provisional claim MAY lack current evidence, but MUST expose that gap and its limits.
  Absence of detected failures does not establish correctness or remove uncertainty.

## Making falsifiability operational

Use this expression where consequential behavior already lives:

> Claim → applicability conditions → observable contradiction → evidence source → interpretation limits.

An acceptance example, contract comment, test, reconciliation record, or runtime signal can carry it.
Choose accessible evidence proportional to the claim; do not prescribe a development ceremony.

Distinguish three questions:

| Question | Example claim | Evidence and limits |
| --- | --- | --- |
| Contract | The algorithm selects the cheapest eligible quote. | Independent acceptance expectations challenge ranking; they do not validate eligibility assumptions. |
| Environment | A provider quote remains usable until its supplied expiry. | Provider acceptance or rejection challenges this assumption; a local simulation cannot establish it. |
| Outcome | Selecting that quote reduces the customer's actual shipping cost. | Actual charges and relevant customer outcomes challenge this claim; quoted price alone cannot establish it. |

Specify a contradictory observation before treating evidence as confirmation.
Tests reproducing the production algorithm lack an independent oracle.
Use independently specified acceptance expectations for intended decisions.
Use external observations when claims concern actual providers, environments, or customer outcomes.
Account for sampling, delayed observations, confounding factors, and unavailable evidence where relevant.

A green test establishes only the behavior and conditions it actually exercises.
A clean dependency graph establishes a structural boundary, not a correct business policy.
Claims about architectural effectiveness also remain challengeable through concrete change and failure evidence.

## Default architectural constraints

### PHA-A01 — Functional core

- **Default:** Domain meaning, policy, and decisions SHOULD remain independent of effectful infrastructure.
  Supply relevant external facts explicitly; evaluating a rule SHOULD NOT require provider SDKs or services.
- **Why:** Explicit facts support PHA-P02 and expose assumptions for PHA-P06.
- **Violation:** Calculating a discount requires a database connection solely to obtain policy inputs.
- **Evidence:** Exercise the rule with supplied values; inspect imports and dependencies for unnecessary infrastructure coupling.
- **Limits:** An atomic database constraint MAY enforce an invariant near its authoritative state.
  Preserve an inspectable contract and evidence of its actual enforcement.

### PHA-A02 — Imperative shell

- **Default:** The shell SHOULD own orchestration, I/O, composition, and effect execution.
  Meaningful business decisions SHOULD remain identifiable outside transport, persistence, and vendor glue.
- **Why:** Separating decisions from execution supports PHA-P02, PHA-P03, and PHA-P05.
- **Violation:** A retry handler silently changes eligibility policy after a provider timeout.
- **Evidence:** Trace one capability from input through decision and effect to observable outcome.
  Inspect which component owns retries, commit boundaries, and uncertain results.
- **Limits:** Small handlers MAY perform simple decisions directly when those remain explicit and exercisable.
  Transactional decisions MAY remain close to storage when isolation requires that placement.

### PHA-A03 — Thin canonical model

- **Default:** Normalize only application-owned concepts; preserve consequential distinctions and provenance.
  Models SHOULD NOT force materially different providers into false equivalence.
- **Why:** Thin models support PHA-P04 without creating an enterprise-wide vocabulary dependency.
- **Violation:** One generic “unavailable” value replaces provider rejection, unsupported capability, and uncertain status.
- **Evidence:** Compare relevant source representations with normalized values and resulting decisions.
  Identify which distinctions survive and which conclusions depend on discarded information.
- **Limits:** Direct provider types MAY remain appropriate where the application owns no shared concept.
  Lossy summaries MAY serve bounded purposes when their limits preserve PHA-P04 and PHA-P06.

### PHA-A04 — Selective ports and adapters

- **Default:** Introduce interfaces for demonstrated substitution or meaningful isolation needs.
  Prefer explicit provider integrations over generalized wrappers hiding useful capabilities.
  A boundary SHOULD simplify the whole workflow, including failures and diagnostics.
- **Why:** Real boundaries support revisability without making evidence harder to inspect.
- **Violation:** A universal provider interface removes reconciliation because only one provider supports it.
  The core looks simpler while the workflow loses a necessary outcome distinction.
- **Evidence:** Name the actual substitution or isolation need and trace its end-to-end effect.
  Compare total workflow complexity and retained capabilities across the proposed boundary.
- **Limits:** Direct calls are appropriate when no valuable boundary exists.
  Test doubles alone do not establish a useful abstraction.

### PHA-A05 — Capability locality and minimum structure

- **Default:** Organize by capability and locality; choose the minimum supporting architecture.
  Accept limited duplication when it avoids premature coupling.
- **Why:** Local reasoning and changes support PHA-P02 and PHA-P05.
- **Violation:** A short transformation requires domain, service, repository, and adapter layers without useful boundaries.
- **Evidence:** Trace a capability and a plausible policy correction across its actual dependencies.
  Challenge abstractions whose removal preserves required properties while simplifying the workflow.
- **Limits:** Shared invariants justify shared mechanisms; duplication must not conceal conflicting obligations.
  No universal horizontal layers, fixed directory tree, framework, or language is required.

### PHA-A06 — Authoritative external clients

- **Default:** Prefer official SDKs; otherwise generate clients from authoritative API specifications.
  Handwritten clients require a concrete reason those options are unsuitable.
- **Why:** Authoritative contracts reduce accidental protocol assumptions while retaining provider capabilities.
- **Violation:** Handwritten authentication and pagination duplicate a suitable supported SDK without explanation.
- **Evidence:** Identify the SDK or specification and inspect consequential protocol behavior and failures.
  Provider observations can contradict SDK behavior; official provenance does not prove correctness.
- **Limits:** Unsupported runtimes, missing capabilities, dependency constraints, or absent specifications can justify handwritten clients.
  Record the reason and retain explicit protocol expectations and error distinctions.

## Applicability, adoption, and exceptions

Apply PHA-P requirements across software categories; adapt techniques to the capability:

| Software | Proportional expression |
| --- | --- |
| Services | Explicit policies, effect states, bounded correlation, and reconciliation where required. |
| Libraries | Contracts, supplied dependencies or values, and observable results or errors. |
| Interfaces | Explicit user state and transitions; distinguish submitted actions from confirmed effects. |
| Scripts and utilities | Functions, arguments, exit status, return values, and useful errors. |
| Data pipelines | Distinguish source observations, transformations, missingness, predictions, and aggregation limits. |
| Infrastructure code | Separate desired state, planned operations, applied state, and observed readiness. |

A small utility needs no interface hierarchy to satisfy this standard.
Distributed workflows can need reconciliation and bounded runtime evidence.
This standard does not mandate production logging of every decision, permanent input retention,
event sourcing, replay infrastructure, or a new observability platform.

Adopt incrementally within the changed capability; avoid unrelated rewrites.
Identify inherited limitations that affect the changed behavior instead of claiming blanket compliance.
Project constraints can justify deviations, but do not erase contradictory evidence.

Document exceptions near the affected contract or decision using:
**affected requirement ID → concrete constraint → retained protections → revisit condition**.
“Legacy,” preference, and a passing checklist are insufficient explanations.
Exceptions to defaults explain the alternative technique.
Exceptions preventing a required property remain explicit compliance gaps, not equivalent compliance.

## Executable reference examples

Run `python3 ../scripts/check_examples.py` from this directory.
The runner exercises baseline behavior and isolated controlled defects.

- [Pure decision](../scripts/decisions.py): quotes expire at the supplied instant, including equality.
  An independently specified expected selection challenges the consequential boundary condition.
- [External operation](../scripts/operations.py): a provider commits, then the request times out.
  The caller preserves an unknown outcome and correlation identity; reconciliation establishes completion later.
  Treating that timeout as confirmed success or failure asserts unsupported knowledge.
- [Small utility](../scripts/utility.py): unique input lines retain their first occurrence and ordering.
  Whitespace and blank lines remain meaningful; line endings normalize to LF.
  Invalid UTF-8 reports an error with exit status 2 and no output.
  Standard input, output, and a direct transformation suffice without extra architectural layers.
- **Tidy counterexample:** the operations example includes a layered, lossy adapter.
  It collapses rejection and unknown observations into an empty canonical tuple, then publishes a complete report.
  The report loses source distinctions and provenance needed to challenge its market conclusion.
  Its tidy structure does not satisfy PHA-P03, PHA-P04, or PHA-P06.

The [runner](../scripts/check_examples.py) introduces controlled defects in isolated example execution.
It changes expiry equality and collapses timeout uncertainty.
Relevant detectors must fail for the intended assertion, while baseline behavior passes.
These experiments challenge the detectors' sensitivity to those specific defects.
They do not validate a real provider, prove future solutions correct, or establish universal architectural effectiveness.
