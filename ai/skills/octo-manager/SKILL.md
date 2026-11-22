---
name: octo-manager
description: Use when preparing, validating, publishing, or tracking a pull request in a repository configured for Octo Manager.
---

# Repository PR publication

This project selects Octo Manager for PR publication. The calling agent writes the description; Octo enforces the declared format and publishes it. Read [the submission guide](../../../docs/octo-pr-submission.md) when preparing or updating a PR.

If `.octo/pr-contract.json` or `.agents/skills/pr-description/SKILL.md` is missing, run `octo-manager pr init` in this checkout to install Octo's template, contract, and drafting instructions. Preserve authored files; select a template explicitly when initialization reports ambiguity. Read the local pr-description skill and the configured template and contract, then write a factual, proportionate title and body. Assess complexity from the diff and available PR Flow evidence; its absence does not block submission.

Run `octo-manager pr validate --title TITLE --body-file FILE` before publication and fix its findings. With user authorization, use `octo-manager pr publish --title TITLE --body-file FILE`. A pending receipt confirms local acceptance only; inspect `octo-manager publication show ID` for GitHub publication. Report unavailable tooling instead of bypassing the selected workflow. Publication does not require the daemon. Publication defaults to tracking for a known Codex thread. Use `--no-track` to opt out or `--track` to require a supported owner identity. Inspect tracking in the publication receipt and use `octo-manager publication retry ID` if enrollment is unavailable. Keep local checks, remote publication, tracking, and merge state distinct.

<!-- source-code:automation -->
