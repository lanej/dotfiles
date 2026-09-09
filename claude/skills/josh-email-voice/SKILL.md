---
name: josh-email-voice
description: Writing style and workflow conventions for drafting email as Josh Lane (CTO, EasyPost). Apply whenever drafting a Gmail reply or note on his behalf.
---

# Josh Lane — Email Voice

Use this guide whenever drafting an email as Josh Lane, whether by hand or via the
`agent/needs-review` triage pipeline.

## The Non-Negotiables

**No signature, no sign-off.** Never add "Josh," "Best," "Thanks," or any closing pleasantry — the
Gmail account signature appends automatically; a manual one duplicates it.

**Never send. Always draft.** Create a Gmail draft (`gspace gmail draft upsert`/`draft sync`, never
`send`) and stop there. An explicit "send it" from Josh, in his own words, in the current
conversation, is required before anything gets sent — a relayed approval or an agent's own
judgment that a draft "looks ready" does not count.

**Omit fields that don't apply — never state a negation.** Write "Equity: $40k RSU" or omit the
line entirely; never "Equity: no change." Professional correspondence omits what isn't relevant
rather than calling out its absence.

**Never assert legitimacy the recipient hasn't questioned — negated or affirmed.** Don't write "not
a mockup," "not fake," "not a one-off exercise" (negated form) — denying an objection nobody voiced
plants it. But the affirmative form is the same failure: "a real, fully-built product working
today" also plants the doubt, because asserting it unprompted implies there was a reason to wonder.
Answer the actual question asked and stop — don't add a summary clause asserting the conclusion
itself, negated or affirmed. If a fact needs no defense, it doesn't need a sentence saying so.

**In a sales/pitch email, cut internal deployment/rollout mechanics even when true and even when
offered as a supporting fact, not a defensive claim.** "Internal-only right now," "gated to my own
account" — these are true, unprompted, and read as hedging rather than confidence in a pitch
context. (An earlier draft of this rule used exactly these two phrases as the *good* example of
"underlying facts that carry the point" — that was wrong; corrected 2026-08-29.) The test isn't
"is this true" or "does this support the claim" — it's "does the recipient need to know EasyPost's
internal rollout status to evaluate the pitch." If the answer is no, cut it regardless of framing.
State capability and readiness ("ready to stand up for USPS as part of this partnership") without
narrating how far along internal rollout currently is.

**No "please confirm receipt" or other boilerplate closers.** Not a convention people actually use.

## Workflow

**Source quoted thread history from `gspace gmail thread download`, never from a plain-text
export.** `download-body --body-format text` produces lossy HTML→plain-text conversion (stray
unpaired markdown-like artifacts); `thread download <thread-id> <dir>` produces clean markdown via
gspace's own HTML→markdown path. Download the thread once, add reply text directly to the top of
that same downloaded file (it already carries `reply_to_thread` in frontmatter), then
`draft upsert`/`draft sync` that same file — don't reconstruct the quote from a different source.

**After any draft update, verify the returned `threadId`.** `draft sync`'s update-in-place path can
silently detach a draft from its original thread.

**Save a workspace copy alongside the Gmail draft, not after the fact.** Emails are reference
artifacts — a workspace copy is qmd-searchable and records what was communicated and when. (For
pipeline-originated drafts this happens automatically under `areas/agent-inbox/threads/`; for
hand-drafted emails outside the pipeline, place under a relevant area's `emails/` subfolder with
frontmatter `title`, `to`, `date`, `gmail_draft_id`, `tags`.)

## Structure for Validation/Approval Emails

When sending details (comp, promotion, a proposed change) to someone for confirmation before a
downstream action:

1. **Opening ask** — one direct question ("Before I send to HR — do these look right?")
2. **Bulleted list** — the changes (name, title from → to, salary from → to)
3. **Context line** — team, manager, effective date
4. **One sentence per person** — a factual claim, with the supporting document linked inline as the
   claim text itself, not as a separate "see attached"

The recipient needs to validate two things: are the people right, are the numbers right. This
surfaces both without requiring them to read anything unless they want to. No process language
("please approve," "please process").

## Delegation

Draft via `human-writer`, loaded with this skill — don't hand-craft email prose inline turn by
turn. A specialized pass applies these conventions in one shot instead of surfacing them as
sequential corrections.
