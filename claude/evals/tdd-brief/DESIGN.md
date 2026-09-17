# Ablation: does "write tests first" in the `Agent` brief change behavior?

**Pre-registered 2026-09-16, before any run.** Commit this file before producing
results; a decision rule written after seeing data is not a decision rule.

## The claim

`claude/CLAUDE.md` requires every `Agent` call to carry six fields, and for
implementation work the Success field must include `"write tests first"`.

Josh's position: current models write tests first by default, so the clause is
inert and should be deleted to save tokens.

Claude's position: nothing in the default system prompt instructs test-first,
and sub-agents optimize for returning a finished result, so the clause is
load-bearing.

One of these is wrong. This measures which.

## What is and is not being tested

The rule instructs the *orchestrator* to include the clause. Its payoff depends
on a necessary condition: that the clause changes the *sub-agent's* behavior.
If it does not, the rule is inert no matter how faithfully the orchestrator
follows it. This eval tests that necessary condition only.

It does **not** test whether an orchestrator includes the clause unprompted,
whether test-first produces better code, or whether the effect holds for models
other than the one run.

## Design

Two arms, identical six-field brief, differing in exactly one clause:

| arm | Success field |
|---|---|
| `omit` | scoped check only |
| `state` | scoped check **plus `write tests first`** |

4 implementation tasks x 5 trials = **20 runs per arm, 40 total**.

Each run gets a fresh copy of `fixture/` (a small Python package with one
existing function and one existing passing test, no `CLAUDE.md` or `AGENTS.md`)
and a fresh empty `HOME`, so no global instruction file loads. The brief is the
only instructional difference between arms.

## Outcome measure

Observed, not self-reported. The run is captured as `--output-format
stream-json`; `classify.py` matches `Write`/`Edit` requests to successful tool
results and classifies by which path was touched first. Failed or missing write
results, overlapping writes, incomplete streams, and unobserved mutation tools
make a run unclassifiable: the runner fails without appending a measurement.

Both arms use Write/Edit for file changes and Read/Grep/Glob for inspection.
Bash is limited to `python -m pytest` or `python3 -m pytest`, optionally with
`-q`/`-v`; any other shell command is unclassifiable. The fixture's tests must
remain assertions about string helpers, not programs that modify source files.
This is a constrained write-order experiment, not a general shell-write tracer.

| outcome | meaning |
|---|---|
| `test_first` | first write to a test path precedes first write to an implementation path |
| `impl_first` | the reverse |
| `no_test` | implementation written, no test file ever written |
| `no_impl` | no implementation written (degenerate; excluded, and the run is re-drawn) |

Primary metric: `test_first` rate per arm, over 20 runs.

The analyzer requires exactly 20 scored runs per arm. It rejects oversized
datasets rather than silently lowering the 18/20 bar or selecting a subset.
Additional trials require a new design and a separate output directory.

`no_test` and `impl_first` both count as failures of test-first. They are
recorded separately because they mean different things — `no_test` is the more
severe outcome and the one the clause most plausibly prevents.

## Decision rule (binding)

Let `p_omit` and `p_state` be the `test_first` rates, and `p` be the two-sided
Fisher exact p-value on the 2x2 table.

- **DELETE the clause** iff `p_omit >= 18/20` **and** `p > 0.05`.
- **KEEP the clause** iff `p <= 0.05` and `p_state > p_omit`.
- **INCONCLUSIVE** otherwise — and inconclusive means keep.

The asymmetry is deliberate. Deletion requires the `omit` arm to clear an
absolute bar, not merely to be statistically indistinguishable from `state`:
at n=20, indistinguishable is cheap. The cost of wrongly deleting is a
recurring, silent defect class; the cost of wrongly keeping is ~40 bytes.

## What n=20 buys

With 20 per arm, Fisher's exact at alpha=0.05 has roughly 80% power against
`p_state=0.95` vs `p_omit=0.55`. It can detect a large effect and nothing
subtler. A `DELETE` verdict therefore means "no large effect, and the omit arm
independently cleared 90%" — not "safe". By the rule of three, 20/20 clean runs
bound the true failure rate at about 15%, not at zero.

If the result lands INCONCLUSIVE and the clause's fate matters enough, the next
step is more trials, not a reinterpretation of these.

## Running it

```sh
for t in 1 2 3 4 5; do
  bash claude/evals/tdd-brief/run.sh omit  "$t" /tmp/tdd-brief
  bash claude/evals/tdd-brief/run.sh state "$t" /tmp/tdd-brief
done
python3 claude/evals/tdd-brief/analyze.py /tmp/tdd-brief
```

Arms are interleaved per trial so that any drift in model serving over the run
hits both arms equally.

`analyze.py` prints the 2x2 table, the Fisher p-value, and the verdict
mechanically from the rule above. Record the output in `RESULTS.md` along with
the model id actually served, and a "what this does not establish" section.

## Operational caveat: HOME isolation vs credentials

The blanked `HOME` is the load-bearing control — without it the operator's own
`~/.claude/CLAUDE.md` loads into both arms and swamps the clause under test.
Verified working in the container this was built in, where credentials come from
the environment. If your credentials live under `HOME`, copy only the credential
file into the temp home; copying `.claude/` wholesale reintroduces the
contamination this control exists to prevent.

## Pipeline smoke, 2026-09-16 (NOT a result)

This historical smoke predates successful-write validation. Its classifications
are unverified; reclassify the original event logs with the current classifier
or rerun it before using these numbers as evidence.

One trial per arm, 8 live runs, `claude-sonnet-5`, to validate the harness end
to end before spending the full 40.

| arm | n | test_first | no_test | rate |
|---|---|---|---|---|
| omit | 4 | 0 | 4 | 0% |
| state | 4 | 0 | 0 | 100% |

Fisher p = 0.0286. `analyze.py` correctly refused a verdict (exit 1, INCOMPLETE).

This is 8 historical runs against one model with one draw per task, not the
ablation. No conclusion about the clause follows from these unverified counts.
Run the full 20 scored runs per arm with the repaired observer before concluding
anything.
