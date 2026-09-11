# Receipt contract — does returning a pointer beat returning prose?

Same three research tasks against this repo, run headless (haiku-4.5), 3 trials
each, 18 runs total. **plain** = task only. **receipt** = task plus "write
findings to <path>, reply with three lines."

## Result: 17.2x, with findings preserved

| arm | n | mean reply | median | range |
|---|---|---|---|---|
| plain | 9 | 2,587 B | 2,065 | 1,506–5,036 |
| receipt | 9 | **150 B** | 150 | 150–150 |

Findings were not lost — the receipt arm wrote 4,625–10,751 byte files. The
content moved to disk; only the context cost went away. Receipt replies were
150 bytes every single time, so the saving is predictable rather than
best-case.

## Compliance: 12/12

Every `wrote:` claim was checked against the filesystem. All 9 clean-run
agents wrote the file; the 3 smoke-run agents did too. Zero false receipts.

**An earlier version of this writeup claimed 2 of 3 agents fabricated their
receipt.** That was wrong — a bad glob in the checker looked in one directory
while two files had been written to another. The agents complied; the
measurement lied. This is the second time in this eval series that a harness
bug nearly became a reported finding, which is the argument for verifying
claims against primary state rather than against your own instrumentation.

## What this does not establish

- Haiku only. A larger model may be more verbose in the plain arm (inflating
  the ratio) or better at compliance.
- Three research-shaped tasks. An agent asked for a decision, not findings,
  has nothing useful to put in a file.
- 12/12 compliance on a contract stated in the *prompt*. The version now baked
  into `document-summarizer`'s definition is untested.
- Says nothing about whether an orchestrator actually uses the contract
  unprompted.

## Gotchas the harness hit
- `--allowedTools` is variadic: a prompt placed after it is swallowed as a
  tool name and the run returns zero bytes with exit 0.
- Headless runs need the workspace trusted or `Write` is silently denied.
- Parallel `claude` processes must have stdin redirected from `/dev/null`.
