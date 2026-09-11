# Skill-maintenance review

## Scope and authoring sources

Add repository routing through the installed authoring workflows, a provenance
check for changed instructions and their declared dependencies, and entrypoint
size budgets. Existing skill behavior and installed plugins are unchanged.

Authoring sources read by the implementing agent:

- Superpowers 6.3.0: `writing-skills`, its `test-driven-development` background,
  and `writing-good-tests.md`.
- Enabled Anthropic `skill-creator` plugin revision `3deb821cb71c`.

The qualified plugin name avoids confusing the enabled Anthropic workflow with
the older repo-owned skill of the same name. The policy assigns baseline-first
sequencing to writing-skills and evaluation/review mechanics to skill-creator.

## Advisory evaluation

Baseline repository instructions came from master
`eeb7d8b9d48a4e4c85a4a56bb796f860afbd2a0b`, before adding the routing paragraphs.
Separate Codex agents received the same three requests and the same stated target
Claude plugin availability. Each read the relevant repository instructions;
the candidate additionally followed their new policy reference. Neither agent
received the other's answers or the review criteria below. Both inherited the
parent runtime settings; no separate model or effort override was selected. The
agent tool did not expose a resolved per-run model identity or token measurement.

`baseline.md` and `candidate.md` retain their responses verbatim. They are advisory
descriptions of intended actions, not executions of the three example tasks.

The baseline already selected both authoring skills and rejected stale evidence.
There is no demonstrated improvement in model capability or claimed failure-rate
reduction. The candidate made the expectations explicit: read the qualified
workflows, establish the old failure before editing, retain paired evidence,
bind shared dependencies, preserve prior runs, and distinguish mechanical checks
from behavioral validation. All three responses preserve the request's authority
and identify the applicable verification instead of treating green helper tests
as proof of behavior. The implementing agent reviewed these responses.

## Mechanical checks and independent review

Tests were written before gate implementation. With minimal no-op gates modeling
the absence of enforcement, 35 assertions failed and six passed: stale evidence,
missing coverage, failed reviews, growth, and invalid overrides were accepted.
After implementation, all 41 initial tests passed. This control establishes the
gate tests' sensitivity; it is not a model-behavior baseline.

Independent code review then reproduced two defects: root `GEMINI.md` was not
governed, and universal newline conversion undercounted CRLF source bytes. The
new focused tests failed on both defects before the fixes. Preserve the original
findings in `code-review.md`; `code-recheck.md` independently confirms both fixes.

Final verification: 43 maintenance tests pass. The combined repository suite
passes 173 tests with four existing live tmux tests excluded, as documented in
the preceding Socrates work. `tests.txt` records the final command result.
`size-report.txt` reports 123 entrypoints with 19 existing overages permitted
without growth. No blanket budget overrides were added.

## Review conclusions and limits

- Routing is explicit in both repository instruction entrypoints and points to
  one shared policy rather than repeating authoring procedures in runtime skills.
- Evidence checks exercise real files and Git diffs, including changed dependencies,
  stale review artifacts, deletion/rename coverage, and retained historical runs.
- Size checks independently enforce 500 lines and approximately 4,000 tokens,
  preserve byte counts for CRLF inputs, and allow reviewed per-file budgets.
- CI uses read-only repository permissions and makes no model/API calls.

The token estimate is a UTF-8 byte proxy, not Claude tokenization. The evidence
gate checks declared hashes and passing review fields; it cannot prove review
truth, dependency completeness, or independent judgment. No claim is made that
these advisory scenarios exercise Claude's native skill discovery, file writes,
or approval interface. The size gate measures entrypoints, not complete runtime
context. Historical overages remain visible and must not grow.
