# PR publication through Octo

The calling agent writes the title and description. Octo installs local writing guidance, validates declared format rules, accepts a durable request, and publishes the submitted draft. It does not generate, rewrite, or semantically judge the description. Publication does not require the Octo daemon; tracking is separate and opt-in.

## Prepare and validate

Run `octo-manager pr init` in the repository. Octo preserves existing templates and authored instructions, installs `.agents/skills/pr-description/SKILL.md`, and records the selected template and mechanical rules in `.octo/pr-contract.json`. If several templates exist, choose one with `--template PATH`. Read that skill, the selected template, and the applicable repository contribution/development guidance before drafting.

Optionally run `octo-manager pr init --derive` or `octo-manager pr refresh` to derive concise advisory guidance from bounded repository signal files and recent merged PRs. Choose `--sample-remote origin|upstream` and at most 20 samples with `--sample-count N`. Derivation may invoke one model; validation and submission never do. Historical medians and proposed rules remain advisory in `.octo/pr-style.json`; only rules explicitly configured in the active format contract block publication.

Assess complexity from the actual diff and use only the detail a reviewer needs. PR Flow can provide evidence for an existing PR or revision; its current analysis interface requires a PR URL, so it is not a prerequisite for creating one. Do not turn a complexity assessment into a mandatory schema or word-count gate.

Write a finished description file, then run:

```sh
octo-manager pr validate --title 'feat: explain the outcome' --body-file description.md
```

Validation is offline: it does not contact GitHub, create a receipt, or start a worker. Empty drafts, invalid title lines, unfilled Octo template prompts, and violations of explicitly declared mechanical rules fail immediately with a short fix list. The agent owns factual accuracy, evidence, authorization, and semantic compliance with repository instructions. No separate drafting agent or process attestation is required.

## Submit and inspect

Commit and push the intended branch, then submit the exact finished draft when the user has authorized publication:

```sh
octo-manager submit-pr --title 'feat: explain the outcome' --body-file description.md
octo-manager submission REQUEST_ID
```

Invalid drafts exit nonzero before acceptance. A valid request is saved before Octo returns a small pending receipt. Pending means accepted locally for publication; it does not mean GitHub accepted the PR. The short-lived publisher revalidates the contract and pushed revision, then records `published` with a URL, a known `failed` result, or `uncertain` when a remote effect cannot be confirmed.

Use `retry-submission REQUEST_ID` to retry pre-publication failures or reconcile an uncertain create. Reuse the existing receipt after a timeout rather than submitting another request. A hidden marker binds recovery to the frozen title, body, repository, head, and base; Octo refuses to overwrite an unrelated PR. Purpose-only requests and legacy intent files receive migration guidance instead of starting analysis/writer jobs. Historical records remain inspectable.

Use `--track --thread-id SESSION` only when daemon-backed tracking is wanted. Use the actual calling session identity; do not invent an owner for an unsupported harness. A tracking failure is reported separately and does not undo publication. Existing PR title/body revisions use the same local drafting and validation guidance, followed by the review platform's update command and verification of the saved result.

Inspect the published title, rendered body, head/base, links, and any included images before reporting publication as verified. Creating a PR does not authorize merging it.

## Hook integration

The optional Codex submission hook translates supported standalone `gh pr create` commands to `octo-manager submit-pr`, preserving the caller's completed title and body. It supplies actual session context for optional tracking and never treats the draft as input to a separate writer. Unsupported flags and retired `gh-pr-create-from` calls return concise migration instructions.

Enable the hook with `make codex-octo-hook`, then review/trust it through the host's native Hooks interface. Run publication separately from pipelines, redirections, variable expansion, or compound commands. Installation preserves other hooks and native trust; it does not grant publication authority or contain arbitrary shell execution. Remove only this adapter with `python3 bin/codex-octo-submit --uninstall`.
