# Independent recheck of review findings

Both original P2 findings are resolved in the current source.

- Root Gemini coverage: `check_evidence.py` now includes `GEMINI.md` in `CONTROL_FILES`, and the governed-path parameterized test covers it. Changes to the actual root instruction file now require evidence.
- CRLF size calculation: `check_size.py` now reads working files as bytes and obtains base blobs without subprocess text-mode conversion, then explicitly decodes UTF-8. This preserves CRLF bytes in both arms of the budget calculation. The new CLI regression checks that a 490-line, 16,170-byte new entrypoint fails at 4,043 estimated tokens, and that the identical committed overage subsequently passes the non-growth rule.

Validation: `python3 -m pytest -q claude/evals/skill-maintenance -k 'GEMINI or crlf'` passed: **4 passed, 39 deselected**.

No outstanding actionable bugs in the two reviewed fixes. The original review file was preserved; repository files were not edited during this recheck.
