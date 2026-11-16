---
name: octo-manager
description: Use when preparing, validating, publishing, or tracking a pull request in a repository configured for Octo Manager.
---

# Repository PR publication

This project selects Octo Manager for PR publication. The calling agent writes the description; Octo enforces the declared format and publishes it. Read [the submission guide](references/submission.md) when preparing or updating a PR.

If `.octo/pr-contract.json` or `.agents/skills/pr-description/SKILL.md` is missing, run `octo-manager pr init` in this checkout to install Octo's template, contract, and drafting instructions. Preserve authored files; select a template explicitly when initialization reports ambiguity. Read the local pr-description skill and the configured template and contract, then write a factual, proportionate title and body. Assess complexity from the diff and available PR Flow evidence; its absence does not block submission.

Run `octo-manager pr validate --title TITLE --body-file FILE` before publication and fix its findings. With user authorization, use `octo-manager submit-pr --title TITLE --body-file FILE`. A pending receipt confirms local acceptance only; inspect `octo-manager submission ID` for GitHub publication. Report unavailable tooling instead of bypassing the selected workflow. Publication does not require the daemon. Tracking is explicit with `--track --thread-id SESSION` and a supported actual owner identity; tracking failure does not undo publication. Keep local checks, remote publication, tracking, and merge state distinct.

## Repository automation

Read `octo-manager.toml` when acting on Octo notifications. Source-code seeds it when this integration is selected and preserves authored settings on later setup runs. The `project_stage` auto-merge default follows the installed source-code stage: research and alpha enable it; beta, production, and unknown stages disable it. Explicit per-PR settings take precedence. State-specific instructions describe the requested follow-up; receipt alone does not complete that work. Follow installed project guidance and existing user authority.
