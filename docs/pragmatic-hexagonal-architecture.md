# Pragmatic Hexagonal Architecture — Engineering Standard v1

Status: default for new software and changed boundaries; applies proportionally to the size and risk of the system. Existing code is migrated when touched, not rewritten for cosmetic compliance.

## Objective

Make software easy to reason about, change, and **prove wrong**. Prefer functional core / imperative shell, a thin owned canonical model, and ports at real boundaries. Never mistake architectural ceremony for isolation.

## Normative rules

1. **Decisions in the core.** Domain decisions, calculations, validation, transitions, and invariants SHOULD be explicit deterministic functions over values. Make time, randomness and policy dependencies inputs. If purity is impractical, isolate the effect and document the tradeoff.
2. **Effects in the shell.** Keep networking, storage, clocks, queues, process execution, retries, logging, provider SDKs, and transaction coordination at boundaries. The shell obtains facts, calls core decisions, performs authorized effects, and reports outcomes.
3. **Own only your domain.** Convert external data into a minimal canonical representation of concepts the application actually owns. Do not normalize every vendor detail. Preserve vendor-specific features in explicit integration modules and expose them where useful.
4. **Dependencies point toward decisions.** Core logic SHOULD NOT import transport, database, UI, cloud, or vendor SDK modules. Pure standard-library utilities are fine. Integrations MAY depend on core types; core MUST NOT depend on integrations.
5. **Ports are selective.** Introduce an interface when there is a concrete substitution, test isolation, independent lifecycle, or ownership boundary. Do not require one interface per service, adapter, database, or dependency. Test doubles alone are not proof an abstraction is valuable.
6. **Organize for locality.** Prefer vertical capabilities that co-locate domain decisions, orchestration, adapters, and tests where feasible. Do not mandate directory names or layers that obscure a workflow.
7. **Make transactions and failure explicit.** Define commit boundaries, idempotency, delivery uncertainty, retries, cancellation, and reconciliation as required by the workflow. Do not silently retry non-idempotent actions.
8. **Use maintained clients.** Prefer official SDKs, then generated clients from maintained machine-readable API specifications; handwrite integrations only with a stated reason.
9. **Simplest fit wins.** A pure function or short script need not grow a port, interface, use-case class, domain object, or dependency injection framework. Complexity must purchase a concrete capability.
10. **No performative rewrites.** For legacy systems, improve boundaries while changing the relevant behavior. Preserve the existing public contract unless an intentional change is authorized.

MUST marks a strong invariant, SHOULD is a default with justified exceptions. Document exceptions close to the relevant boundary, with a cost and a revisit trigger.

## Workflow design

For a meaningful change, state:
- The user-visible outcome and its real entrypoint.
- Decisions and invariants; facts and effects; ownership of each.
- External representations and the minimum canonical shape (if any).
- Actual substitution / isolation boundaries, or explicitly **none**.
- Failure modes and irreversible effects.
- A concrete claim that can be disproved and the cheapest detector capable of disproving it.

Implement a thin, working vertical slice; prove the first meaningful failure, then the first success; simplify only after it works. Do not build generic infrastructure before a real workflow needs it.

## Falsifiability and evidence

**A behavioral detector** MUST enter through the real caller-facing entrypoint and assert an observable outcome. It is insufficient to assert private method calls, copied source text, exact filenames, or mock invocation counts. Prefer one representative detector per user-visible feature. Establish once for a new test harness that removing the protected behavior makes it fail; don't repeatedly perform mutation checks in an established harness.

**An architectural detector** SHOULD automatically enforce objective boundaries where practical (e.g., import cycles and core-to-provider dependency prohibitions). Run it on the changed slice or affected modules; do not invent brittle regex rules for semantic judgments.

**A design review** MUST examine claims static tests cannot establish: unnecessary indirection, leaky canonical types, hidden decisions in adapters, false provider equivalence, and cross-feature drift. An unsupported claim of compliance is a gap, not a pass.

For each substantial feature, record the falsifiable claims in the PR or design:
| Claim | Counterexample | Detector | Observed evidence |
| --- | --- | --- | --- |
| Decision independent of provider | Changing provider changes the decision on equivalent facts | Pure contract test across equivalent inputs | Result / gap |
| Workflow fulfills user outcome | Remove critical effect yet the check remains green | Acceptance detector through real entrypoint | Result / gap |
| Core isolated from I/O | Domain module imports provider or storage client | Dependency graph / import boundary check | Result / gap |
| Retries do not duplicate effects | Timeout after success causes duplicate external action | Fault injection at effect boundary | Result / gap |

Do not require every claim in every change. Select claims that materially constrain the implementation and could fail.

## Review questions

- Can a reviewer understand this feature end-to-end without tracing unrelated layers?
- Where are the actual decisions? Can those decisions be evaluated using supplied facts?
- Can the integration change without changing the decision? If not, is the coupling intentional?
- Which abstraction would be removed if there were only one provider?
- What observable check fails if the important behavior disappears?
- What important failure remains untested, and why is that residual risk acceptable?

## Applicability

For scripts, configuration and infrastructure-as-code, translate “core” to deterministic transformations and policy, and “shell” to commands and side effects. For GUIs, distinguish pure view state / transitions from network and browser effects. For event-driven systems, keep event interpretation and decisions separate from delivery and acknowledgments. No framework or directory template is mandated.

## Adoption and evolution

Treat this standard as a hypothesis. Track review findings attributable to architecture, escaped regressions, implementation lead time, and interface/adapter churn. If the rules add ceremony without making failures easier to localize or changes safer, simplify or remove the rules. A compliance checklist without evidence is not success.

See `ai/skills/pragmatic-hexagonal/SKILL.md` for the Codex workflow. The existing `methodology` skill remains authoritative for verification tiers, test scope, and PR review cadence.
