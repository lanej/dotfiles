# Calibration run — not an adoption result

The initial paired run used baseline `71a4f0fcf72a408eb5302f90a965361d1ec0402c`
and candidate `fceba32`, with `claude-sonnet-5[1m]`, medium effort, one trial per
scenario and two workers. All calls completed on the same resolved model.

Mechanical checks passed for 3/8 old and 8/8 new conversations. **The new flow did
not pass semantic review.** Those numbers are retained as a demonstration of why
keyword and endpoint checks cannot establish readiness.

Review found:

- `new-conflicting_requirements-1`: D3 labeled unspecified cutoff semantics as
  accepted uncertainty without explicit acceptance. The spec also narrowed
  irreversibility to supported live-system access and left possible backups
  unaudited. Implementation delegation did not authorize either move. The fixture
  itself omitted age, cutoff, and storage definitions, so some extra questions
  from the old flow were legitimate and cannot be counted as wasted dialogue.
- `new-unsupported_premise-1`: "core functionality operates correctly" was not a
  concrete test. The response treated a smoke-test pass as established offline
  capability and invented unspecified follow-on study work. The fixture had not
  named the tested operation or the pass endpoint.
- `new-new_evidence-1`: the result replaced substantive sections with "carried over
  from v2" and invented a backup/log exclusion. The fixture provided only a summary
  of the earlier session, which could not test preservation of a complete artifact.
- `old-accepted_tradeoff-1`: it honored manual review but turned a check after two
  Fridays into a biweekly commitment, adding a timing decision absent from the user.

The next candidate explicitly separates mechanism delegation from accepted
uncertainty, forbids silently weakening requirement semantics, limits claims to
what a concrete test establishes, preserves one-time timing, and retains unchanged
spec content. The next fixtures supply established prototype retention semantics,
an offline operation with concrete results and both endpoints, and complete saved
artifacts for all three resume cases. Their rubrics require those facts to survive.

The common replay driver also requests plain artifact Markdown and prohibits
inventing missing prior content. Both arms are rerun with the same revised driver
and fixtures. The complete fictional response records from this calibration are
retained here; raw CLI envelopes containing host metadata remain outside the repo.
Do not combine this run's counts with the final run or describe it as passing.
