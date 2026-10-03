---
name: gh-pr-stack
description: Use when creating, registering, extending, or verifying native GitHub PR stacks with the official github/gh-stack extension, including existing PR chains that lack native stack registration.
---

# Native GitHub PR stacks

Use `gh stack` from `github/gh-stack`. The command is not `gh pr stack`.
Chaining PR bases with `gh pr create --base` or adding merge-order prose does
not register a native GitHub stack.

## Establish scope

- Confirm the repository, trunk, and layers ordered bottom to top from the
  request and repository state; do not hard-code repository names or PR IDs.
- Inspect `gh extension list` and `gh stack --help`, then help for the selected
  subcommand. If missing, install with `gh extension install github/gh-stack`
  only when the task authorizes setup. Otherwise report the missing dependency.
- Inspect `git status --short` before local branch operations. Preserve dirty
  work; do not reset, stash, stage, or commit unrelated changes.
- Native registration and submission mutate GitHub. Stay within the user's
  authorized scope. Do not automatically merge, bypass credentials, or use
  `--open` unless the user explicitly requests readiness for review.

## Register existing PRs

Prefer remote-only linking when PRs already exist:

```sh
gh stack link --base <trunk> <bottom-PR> <next-PR> <top-PR>
```

Replace placeholders with resolved inputs. Verify each PR's repository, state,
head, base, and draft status first, using `gh pr view` as needed. Use PR URLs
to avoid numeric argument ambiguity: the first number may identify an
existing stack. Do not pass branch names when the intent is only to register
existing PRs: branch arguments are pushed and may create missing PRs.

`link` creates or updates native registration without adopting local tracking.
Reuse the existing PRs and preserve draft states by omitting `--open`; do not
close or recreate them. An update retains existing stack members rather than
removing them. Inspect existing membership before linking so unintended
members are not silently retained; stop on conflicting stack membership.

To append to a known stack, use:

```sh
gh stack link <stack-number> <additional-PRs...>
```

Repeated arguments already in that stack are skipped. Use the same resolved
inputs if a retry is needed; inspect remote state after a partial failure
before retrying. Do not create replacement PRs or stacks to work around it.

## Create a locally tracked stack

For authorized local stack creation, inspect branch ancestry and existing
tracking before initializing:

```sh
gh stack init --base <trunk> <bottom-branch> <next-branch> <top-branch>
gh stack view --json
```

`init` adopts existing branches and creates missing ones. Confirm which is
intended; do not assume registration repairs incompatible ancestry. If
rewriting history is needed, preserve a recovery checkpoint and proceed within
already-authorized local stack restructuring. Ask only when published-history
rewriting or destructive changes exceed existing authorization. Do not run
`rebase`, `sync`, or force pushes as incidental setup.

Add an authorized new layer with `gh stack add <branch>`. Avoid its staging
and commit flags unless those changes are expressly intended.

When publication is authorized:

```sh
gh stack submit --auto
```

`submit` pushes branches, creates or updates PRs and their bases, and registers
the native stack. `--auto` creates new PRs as drafts without the editor.
Interactive submission defaults new PRs to ready for review; explicitly
select drafts unless readiness was requested. Use `--remote <remote>` only
after resolving the intended destination.

Remote-only `link` does not make `gh stack view` a remote verification tool.
If local tracking is requested later, `gh stack checkout <PR-URL>` can
discover the remote stack, fetch branches, and establish tracking; it also
changes checkout state, so preserve dirty work before using it.

## Verify and report

Perform one focused verification of the resulting remote stack: confirm
native membership, bottom-to-top order, trunk, unchanged PR identities, and
preserved draft states. Use the stack identity from command output and
corroborate it with read-only remote stack data or the GitHub stack UI.
For local tracking, `gh stack view --json` supplies additional local evidence.

Make verification safe to repeat: read existing state rather than recreating
PRs or re-submitting merely to check success. If native remote evidence is
unavailable, report that limit instead of treating base chaining as proof.
Return the native stack number, ordered PRs, trunk, draft states, and whether
local tracking exists. Distinguish the stack number from a PR number.
