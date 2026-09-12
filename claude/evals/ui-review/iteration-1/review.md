# Review and validation scope

Reviewed by the implementing Codex agent against the preserved fixture pair,
actual screenshots, current source, and executable results. This is a manual
instruction review plus program validation, not an independent native-Claude
behavior benchmark or user approval.

Authoring guidance used: OpenAI skill-creator, skill://flora-skills/root/.codex/skills/.system/skill-creator/SKILL.md
and skill://flora-skills/root/.codex/skills/oai/skill-creator/SKILL.md.
The exact Anthropic skill-creator:skill-creator plugin required by the new
repository policy is not exposed in this runtime's installed catalog. Its native
paired authoring/grading workflow could not be performed. No claim is made that
it was followed. The source/baseline/candidate and observed results below are
retained so this limitation is reviewable rather than hidden.

## Observed program behavior

The current 14-test run is in tool-tests.txt. Tests exercise rendered broken and
corrected pages, every rule family, missing readiness and HTTP failures, scoped
rules, invalid configuration, feedback provenance, approval reference copying,
source freshness, and the real executable launcher. A failed automated result
remains failed after visual approval; unknown feedback cannot promote a rule.

Large-screen tests compare a region at 1000x800 with the same fixed-size content at
2560x1440. They detect coverage dilution and an 840px empty vertical band. Another
test proves that measuring a fitted wrapper can show 100% coverage while the
whole viewport has only 25% coverage. Text coverage stays small when its enclosing
boxes expand. Overlapping/nested rectangles do not double-count covered area.

The 3840x2160 capture test verifies complete grid coverage, exact PNG dimensions,
and the actual red bottom-right marker in the final tile. A one-tile cap fails
both the review result and the Stop gate. Captures retain one pixel per CSS pixel;
this does not prove a model inspected them or certify their semantic content.

Current large-screen report metrics and a representative tile were independently
read/viewed by the implementing agent: 0.78% selected-text viewport coverage and
approximately 1419px empty vertical band in the illustrative 4K fixture. These
numbers are diagnostics against example thresholds, not approved global limits.

## Instruction review and prior trial

The exact current candidate is retained in candidate.md. It directs the consumer
to inspect original-size tiles, keeps density scoped, forbids invented universal
thresholds and model self-approval, and requires repair evidence. Subjective notes
remain guidance. It distinguishes capture completeness from visual assessment.

initial-trial.md records an independent agent's actual pre-extension repair trial.
The prompt was to use /ui-review to improve a carrier comparison whose primary
job was comparing eight carriers on desktop. The trial used the same configured
rule set and real browser captures, fixed the UI without weakening checks, and
did not record approval. Its screenshot is docs/examples/ui-review/skill-trial.png.
The evaluator inherited the parent runtime's model/settings; no Sonnet or Opus
model was selected. The large-screen instruction additions happened afterward,
so this historical trial is not represented as a fresh run of the exact current
skill. They are covered by the current manual instruction review and program
tests, not a fresh model behavior claim.

## Judgment

The executable constraints and capture coverage are supported by observed tests.
The skill has a useful initial smoke trial, but its effect on native Claude Code
Sonnet/Opus design judgment is unmeasured. Actual application fixtures and Josh's
accepted screenshots should calibrate density thresholds. Neither this record nor
CI means Josh approved the example designs.
