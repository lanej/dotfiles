---
name: compose
description: Develop an evidence-backed document through a brief, draft, independent reader critique, revision, and release. Use when asked to compose a substantial document or run the document-shaping workflow on an existing file.
---

# Compose

Turn the requested document into a releasable artifact whose claims have inspectable support. Use the current conversation's established audience, intent, evidence, and decisions. Ask only about missing consequential choices; do not repeat a fixed interview or invent requirements. Invocation with a file path means revise that document; a description means create the requested document.

## Artifacts and rigor

Create a unique `.compose/YYYYMMDD-HHMMSS/` session, or continue an explicitly selected/bound one. Keep `brief.md`, `sources.md`, `draft.md`, `critique.md`, and a clean `release/doc.md` copy there. Preserve previous drafts/reports under unique timestamped `history/` paths before replacing them. The draft's status is `Brief`, `Outlined`, `Drafted`, `Under Critique`, `Reconciling`, or `Released`; saved state, not conversational memory, records progress.

A trivial note may go directly to drafting, recording the skipped stages in `skip.md`. A moderate memo uses a brief, draft, reader critique, and revision, researching claims as needed. Complex, externally distributed, or consequential documents use every applicable stage. Apply the user's requested format and voice; this workflow does not require Quarto.

## Develop the document

1. **Interrogate intent.** Establish reader/context, intended decision/action, observable success, available evidence, constraints, and cost of inaction where relevant. Record answers in the brief. Do not invent numerical returns for a document whose purpose does not entail them. Resolve consequential gaps before drafting.
2. **Research.** Use available authorized sources and installed skills appropriate to the service; do not assume a specific MCP server. For each inspected source, record an S001, S002, ... entry in `sources.md` with title, URL or local evidence path, date, confidence, and supported claim. Distinguish observations, author-attested organizational facts, explicit reasoning, and unsupported inferences. Record unavailable evidence as a gap, not an absence. Quantitative/comparative factual claims need inspectable support; internal records can support internal claims without an invented external citation.
3. **Brief.** Record a thesis, audience, intended outcome, and a section map with columns `Section | Claim | Backing | Audience Assumption`. Each substantive claim has a source ID, explicit attribution, or stated first-principles reasoning. A reasoning label alone cannot establish an empirical claim. If backing is missing, research or narrow the claim before drafting.
4. **Draft.** Fulfill the section map. Cite sources inline with Markdown links matching ledger entries; attribute organizational facts explicitly and make actual reasoning legible. Preserve material qualifications. Unsupported claims return to research or are removed. Set `Drafted` only when the brief's claims are addressed.
5. **Critique.** Dispatch two independent fresh-context readers with only the draft: a naive reader for missing context/logical gaps, and a skeptic for unsupported claims and unnecessary content. Readers return findings inline and do not dispatch further agents. The parent audits citations against the ledger and checks stale sources against the claim's time sensitivity. Before rereading the draft, derive a few concrete reader questions from the brief, then test whether the draft answers them. Save findings in `critique.md`. If dispatch is unavailable, label the inline review and the missing independence; do not claim two independent readers or mark a required critique complete.
6. **Revise.** Record accepted/rejected/deferred dispositions and reasons; accepted means incorporated. Resolve unsupported claims by obtaining evidence, writing valid reasoning/attribution, narrowing, or cutting. Reopen the brief when critique changes the thesis, reader, or purpose. Read and apply [distill](../distill/SKILL.md) to the full document once accuracy is settled. Preserve citations and qualifications.
7. **Release.** Release only when consequential findings and evidence gaps are resolved, reader questions are answered, and required independent critique is complete. Write clean content without workflow status/section-map annotations to `release/doc.md` and the requested destination. For an existing input path, update that file; for a description, use a descriptive Markdown filename in the working directory unless the user chose another format/path. Set `Released` after writing and checking the final output.

Local release does not authorize sending, publishing, changing sharing, or writing global memory. Respect active write restrictions; identify unsaved artifacts and unmet gates. Resume from recorded state rather than restarting settled dialogue.
