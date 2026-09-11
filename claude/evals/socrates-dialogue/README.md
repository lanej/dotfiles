# Socrates dialogue evaluation

Eight scripted conversations compare the old and revised command instructions on
the same model and settings. They cover a clear request, hidden consequential
choice, conflicting requirements, unsupported premise, accepted tradeoff, new
evidence, disposed critique, and legacy confidence scores.

The candidate must pass **every scenario's readiness and preservation checks**.
Question count is not a readiness measure. Record unnecessary questions, repeated
questions, and premature planning separately, including when a scenario passes.

## Run the comparison

Use an already configured Claude CLI. This does not provision credentials or change
the installed commands. Both refs must contain committed command files.

```sh
python3 claude/evals/socrates-dialogue/run.py \
  --baseline 71a4f0fcf72a408eb5302f90a965361d1ec0402c \
  --candidate HEAD --model 'claude-sonnet-5[1m]' --effort high \
  --trials 1 --jobs 2 --out /absolute/path/to/new-evaluation-directory
```

Use the same explicit model and effort for both arms. The manifest captures resolved
commits, requested settings, CLI version, and fixture/prompt hashes. Each record
captures the actual resolved model; model drift or any infrastructure failure
invalidates the comparison. New output directories prevent overwriting prior runs.

Every turn starts a fresh tool-free CLI call in an empty temporary directory, with
the exact prior dialogue and specification supplied explicitly. Tools, MCP servers,
slash-command expansion, and session persistence are disabled. The CLI's system
prompt is replaced by a common replay driver plus the selected command bundle.
Only fictional task data is used. Expected actions, required facts, future replies,
and assessment rubrics are withheld from the model. Arm order alternates by pair.

The replay preserves complete model responses, including verbose legacy score
tables. Raw CLI envelopes remain local because they may contain host metadata.
Timeouts, process errors, malformed outputs, permission failures, and unresolved
model identity are infrastructure failures; they never count as successful dialogue.

## Review and adoption gate

The runner checks endpoints and fixture facts mechanically. Its `PASS` output means
those checks passed, **not** that the qualitative review is complete. Inspect every
reply and proposed specification against the scenario's `rubric`:

- **Readiness and endpoint:** did it stop for a real blocker, continue when ready,
  respect `/specify`'s endpoint, and keep plan approval separate?
- **Seeded blockers:** did it discover the scenario's consequential gap or conflict
  before planning, without inventing unrelated blockers?
- **Decision preservation:** did accepted choices, authority, critique dispositions,
  and historical evidence survive? Were changed decisions justified and versioned?
- **Executable specification:** can a fresh executor meet observable criteria
  without guessing intent or making an undelegated consequential choice?

For a scenario with no seeded blocker, record why none needs discovery. A passing
check needs concrete evidence from the captured response, not only a Boolean.

Count each independently answerable request for information as a question,
including multiple requests in one sentence. An **unnecessary question** changes
none of goal, scope, approach, authority, or acceptance given established evidence
and decisions. A **repeated question** duplicates an information request within a
turn, or reopens a settled answer without a concrete trigger. **Premature planning** is a turn entering planning with a seeded blocker
unresolved, or entering planning through `/specify`. Counts can overlap. Explain
the classification; do not equate fewer turns with improvement.

Create `reviews.json` keyed by `<arm>-<scenario>-<trial>`. Each entry has:

```json
{
  "record_sha256": "SHA256 of that captured record.json",
  "checks": {
    "readiness_and_endpoint": {"passed": true, "evidence": "Specific response evidence"},
    "seeded_blockers": {"passed": true, "evidence": "Specific response evidence"},
    "decision_preservation": {"passed": true, "evidence": "Specific response evidence"},
    "executable_spec": {"passed": true, "evidence": "Specific response evidence"}
  },
  "counts": {"unnecessary_questions": 0, "repeated_questions": 0, "premature_planning": 0},
  "question_notes": "Explain which decision each question changes, or why none is needed."
}
```

Then run the gate; it rejects missing or stale reviews and fails unless every
candidate scenario passes both mechanical and documented review checks:

```sh
python3 claude/evals/socrates-dialogue/review.py /absolute/path/to/evaluation-directory \
  --reviews /absolute/path/to/evaluation-directory/reviews.json
```

Keep unsuccessful runs when revising the instructions. Any fixture or driver
change requires a new paired comparison, not relabeling old outputs. Record the
reason for changes so a narrower test cannot masquerade as a workflow improvement.

## Deterministic checks and limits

```sh
python3 -m pytest -q claude/evals/socrates-dialogue/socrates_dialogue_test.py
```

CI runs these boundary, review-gate, and shared-contract checks without model calls.
The dialogue comparison is a bounded simulation, not a test of native tool calls,
actual session-file writes, sockets, plan-mode restrictions, or approval UI. It
captures proposed preservation, not proof that files were physically preserved.
The current reviewer is the implementing agent; the evidence is saved for a human
to audit. Repeated samples and independent review can increase confidence, but
this small scenario set cannot establish performance across all real tasks.
