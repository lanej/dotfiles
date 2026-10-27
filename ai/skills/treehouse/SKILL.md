---
name: treehouse
description: Use when isolating a coding task, creating agent Git worktrees, or using Treehouse. Acquire and return leased task worktrees for Codex and Claude through the native Treehouse CLI.
---

# Treehouse task worktrees

Use Treehouse for task worktrees the agent creates.

## Reuse assigned checkouts

Keep explicit user-selected, host-managed, and preassigned Firstmate worktrees.
This includes Codex App/`codex --worktree` and Claude `--worktree`/`EnterWorktree` checkouts.
Continue there; do not nest worktrees, reacquire them, or claim their leases.

## Acquire

Read repository instructions for location constraints.
Resolve the primary checkout with `git worktree list --porcelain`.
The dotfiles default places the pool under `<primary-checkout>/.worktrees/.treehouse/`.
Verify `git check-ignore` excludes that destination before allocation.
Stop and report any conflict between the configured pool root and repository constraints.

If Treehouse is missing, stop allocation and identify dotfiles `bootstrap.sh` as its installer.
Keep the native CLI available for standalone use.

Choose a unique task label and named task branch.
Run from the primary checkout:

```sh
treehouse get --lease --json \
  --lease-holder "<unique-task-label>" \
  --branch "<named-task-branch>"
```

Keep returned `path`, `lease_id`, `lease_holder`, `leased_at`, and `base_branch` in task context.
Record the requested branch too, and preserve these details through handoffs.
Work at the returned `path`.

## Return

Return only leases this task acquired.
Preserve commits on a named branch or verified remote ref before returning.
Check `git status --short --untracked-files=all` and valuable ignored artifacts.
Retain checkouts containing unsaved work or needed artifacts.
Confirm no user, agent, session, process, or pending task still needs the checkout.

Move outside the checkout to the primary checkout, then run:

```sh
treehouse return "<path>" \
  --if-lease-id "<lease-id>" \
  --if-lease-holder "<holder>"
```

Native return can terminate lingering processes.
Use neither `--force` nor `--all` for routine cleanup.
Check the return result; report the path and reason if it fails.
Keep native pool directories intact; never remove them with `git worktree remove`.
Apply ordinary Git cleanup rules only to non-pool temporary worktrees.
