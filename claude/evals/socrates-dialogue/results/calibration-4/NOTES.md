# Fourth calibration — not an adoption result

Baseline: `71a4f0fcf72a408eb5302f90a965361d1ec0402c`; candidate: `dbf06a2`.
Both arms used `claude-sonnet-5[1m]`, high effort, one trial per scenario and four
workers. The compact template improved outcome consistency in the unsupported
premise case, but the run still did not satisfy the adoption gate.

- The old `unsupported_premise` and `new_evidence` conversations timed out at the
  180-second per-call limit. These are infrastructure failures, not dialogue passes
  or failures, and invalidate the aggregate comparison.
- `new-new_evidence-1` still treated a 7-day ceiling as if it uniquely selected a
  7-day target, planning before the owner chose the replacement value.
- `new-legacy_scores-1` again treated correction of contradictory authority as
  metadata-only and retained v1. The history and correct no-deletion authority
  were preserved; the failed check is the missing versioned reopening.

The next candidate makes both distinctions explicit: a constraint bounds a choice
without making it, and correcting erroneous authority in a frozen artifact versions
the correction even when the true answer is already known. The next new-evidence
fixture has the owner select **5 days below the 7-day cap**, with day-4/day-6 checks,
so an inferred maximum can no longer coincidentally match the later answer. Both
arms receive the same strengthened fixture; the answer is withheld until turn 2.

Both arms in the next run receive an equal 360-second call limit. Timeout capture
now preserves partial stdout/stderr and records a concise error instead of dumping
the entire command into the error field. The model and high-effort setting stay the
same. This run's original records remain intact, including the timeout errors.
