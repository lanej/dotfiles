---
name: treehouse
description: Use when inspecting or returning an existing Treehouse pool lease. New agent worktrees use the worktree manager and its canonical worktree skill.
---

# Legacy Treehouse leases

For new agent-created checkouts, read `../worktree/SKILL.md` and use the native `worktree` manager. Do not acquire another Treehouse lease. Preserve outstanding pool directories and their original lease identities while the tools coexist.

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
