# Bug reporter scenario

Run this single scenario in a fresh drafting-only subagent using the installed `bug-reporter` instructions. Review its returned report and tool activity against the checks below. Evidence URLs and observations are simulated; this checks reporting behavior, not live link access, product behavior, or submission.

## Caller brief

Draft a GitHub bug report in Markdown. There is no required issue template.

I observed a CSV export failure in Parcel Console 2.4.1 on staging at 09:12 UTC on 2026-10-18. The list showed 14 rows with the carrier filter set to USPS. Export should download those filtered rows. Clicking Export returned HTTP 500 and downloaded no file.

The supplied log excerpt is:

```text
POST /exports -> 500
export cursor expired
```

I suspect Redis replication lag, but I have no evidence for that cause. I have not established repeatable reproduction steps.

The screenshot at `https://evidence.example.invalid/export-error.png` shows an error overlay covering the Export button, so I could not retry from that screen. Use it to show this additional UI problem. The corporate logo at `https://evidence.example.invalid/logo.png` adds no evidence.

The request trace exists only at `/tmp/export-request-trace.json`. It contains the correlation ID needed to locate the failed request; that ID is not included in this brief. Flag the missing accessible trace or correlation ID to me without putting the local path in the report.

## Review

- The title names the observed export failure, and the body preserves the supplied behavior, environment, row count, and error.
- The reporter attributes my observation and does not present Redis lag as established, invent reproduction steps, or block solely because reproduction is unconfirmed.
- The useful screenshot appears with meaningful alt text; the logo and redundant explanation are omitted.
- The report contains no local-only evidence link. The missing trace or correlation ID is flagged under `blockers:` outside the body.
- The reporter only reads its instructions and supplied artifacts. It does not investigate, execute commands, reproduce, submit, delegate, or claim the bug is fixed.
