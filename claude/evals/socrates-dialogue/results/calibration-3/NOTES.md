# Third calibration — not an adoption result

Baseline: `71a4f0fcf72a408eb5302f90a965361d1ec0402c`; candidate: `50301c7`.
Both arms used `claude-sonnet-5[1m]`, medium effort, one trial per scenario and four
workers. No infrastructure failures occurred. Mechanical checks passed for 5/8 old
and 6/8 new conversations; the candidate was not accepted.

- `new-new_evidence-1` inferred a 7-day target from the policy ceiling, entered
  planning before asking the owner for the target, and invented day-6/day-8
  acceptance checks before the scripted user supplied them. This is recorded as
  premature planning, even though the subsequent answer happened to match.
- `new-legacy_scores-1` fixed the authority contradiction but called the correction
  metadata-only and kept v1. It also omitted the actual historical score/pass
  values from the returned artifact, referring only to a proposed snapshot.
- `new-unsupported_premise-1` correctly bounded the test/report, but its escalation
  section gave "one entry displays but not the other" as an ambiguous result,
  contradicting R1's explicit failure criterion. Optional risk sections also still
  invited unsupported acceptance language.

The next candidate makes the scaffold compact and conditional: no empty risk,
stakeholder, or escalation slots to fill with speculation. The readiness procedure
cross-checks defined outcomes against escalation rules and requires delegated
mechanics to satisfy the full requirement, not merely its sample tests. Critique
no longer treats an omitted optional heading as a finding by itself.

The confirmatory run uses **high effort for both arms**, with the same model and
the same eight fixtures as this run. Its comparison is within that paired run;
do not attribute a difference between calibration and confirmation solely to the
instruction changes, or claim these medium-effort runs passed. The normal command
does not change the user's configured model or effort.
