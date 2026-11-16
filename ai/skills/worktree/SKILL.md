---
name: worktree
description: Use when isolating coding work, creating agent Git worktrees, or finishing owned task protection with the native worktree manager. Preserve assigned checkouts and prune explicitly.
---

# Agent worktrees

Use the native `worktree` manager for agent-created checkouts. New allocations live at `<primary-repository>/.worktrees/<agent>-<8-hex>/`, before a task name exists. Never fall back to a temporary directory or another allocator when the manager is missing or fails; report the failure and identify dotfiles `make install` as the supported installer.

## Reuse assigned checkouts

Keep explicit user-selected, host-managed and preassigned checkouts, including Codex App, Codex CLI, Claude and Firstmate assignments. Continue there without nesting another checkout or claiming its task/lease ownership. An explicitly requested independent task may allocate from the primary repository.

## Create

Read repository location constraints. The manager resolves the primary checkout even when invoked from a linked worktree, requires the default destination to be ignored, and rejects symlink redirection. Do not pass `--path` to bypass the agent placement convention.

```sh
worktree create --agent codex --owner-id "<full-allocation-or-agent-identity>" --json
```

Use the actual client slug, such as `codex`, `claude` or `pi`. Supply an available full owner identity; do not invent a native session ID before startup. Omit `--branch` for an automatically named branch or provide a fresh descriptive name. Use `--base REF` when the task specifies a base; otherwise the manager uses local `HEAD` without fetching. Task and branch descriptions may change without renaming the checkout.

Read the `schema_version`, `command` and `result` envelope. Retain the full `id`, `path`, `branch`, `agent`, optional `owner_id` and lifecycle state through handoffs. Work only at the returned path. A nonzero result can still identify a surviving protected task after a Git hook failure; inspect `worktree status --json` before retrying. Missing confirmation is unknown, not rollback. Do not allocate a second checkout to work around an uncertain result.

## Finish and cleanup

Finish only task protection this task owns, after preserving commits on a named branch or verified remote ref and confirming no active session, process or pending work needs its protection. Inspect tracked, untracked and valuable ignored files. Keep protection when completion or ownership is uncertain.

```sh
worktree finish "<full-task-id>" --json
```

Verify the returned task identity and `finished` state. Finishing keeps the checkout and branches. Preview and explicitly prune a finished checkout when its files and activity checks permit removal:

```sh
worktree prune --worktree "<returned-path>"
worktree prune --worktree "<returned-path>" --apply
```

Do not use `--force` for routine cleanup. Preserve pre-existing and other agents' checkouts. Follow the shared cleanup procedure before removal and report any retained path with its concrete reason.
