---
name: distill
description: Shorten prose while preserving its meaning, precision, and author voice. Use when asked to distill, trim, condense, or remove redundancy from a document. Excludes source code and data transformations.
---

# Distill

Read the full document and identify its purpose, audience, key claims, and dependencies.
Remove repetition and material the audience does not need. Compress the remaining prose
without changing factual claims, qualifications, or the author's voice.

Preserve numbers, citations, links, and the context needed to interpret them. Leave
configuration, executable content, and document machinery unchanged during a prose edit.
If a proposed cut might change meaning, retain it or flag the specific ambiguity.

Edit the supplied file in place when an edit was requested. For pasted text, return the
revision inline unless the user requests a file. Ask for a target only when it is missing
or ambiguous. Honor an explicit request for a proposal or diff before applying edits.

Check that the shortened document still answers the original purpose and supports its
conclusions. Report material cuts or unresolved questions briefly. If reporting word
counts or a reduction percentage, compute them from the actual before and after text
and state whether the count excludes document machinery.
