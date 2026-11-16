# Worktree lessons

Read for assigned worktree operations and delegated coding work. Repository governance and the selected checkout manager control allocation and cleanup; these lessons do not authorize creating or removing checkouts.

### Structured briefings targeting a worktree

State the assigned checkout’s absolute path in each brief. Reuse assigned checkouts without per-task isolation that would allocate another tree. Confirm cwd and branch before edits, then inspect the returned commit and any unexplained changes in the shared checkout before accepting the result.

### `EnterWorktree` is pinned to the session's original root

Host worktree APIs can retain the session’s original root after a relocation. Confirm the actual repository and base before allocating; follow the selected checkout manager and repository instructions instead of assuming a host API retargeted itself.

### `EnterWorktree`'s default `fresh` mode can silently branch from a stale `origin/main`

Confirm the intended base and fetch when needed before allocating. Remote default branches can differ from local unpublished work; compare both directions and choose the base explicitly rather than assuming a cached remote ref is current.

### Check a repo's own governance docs before adding a worktree/branch there — even one you don't primarily maintain
Creating a new worktree/branch in a shared external repo (a personal fork with worktrees already sitting next to each other, e.g. `~/src/easy-ui-worktrees/`) can violate that directory's own "use the existing checkout/branch/PR, do not create parallel stacks" convention, documented in a `README.md`/`CONTRIBUTING.md` you never read because the check only fires for the primary project. Treat "this repo already has other worktrees/checkouts next to it" as itself the signal to look for such a doc before adding another one. (detail: memory "feedback_worktree_governance_docs_not_checked")

### Two concurrent Agent tracks writing into the same worktree can race on the shared git index

Disjoint files still share one Git index. Serialize staging and commits, inspect the entire staged snapshot, and stage exact intended paths or hunks. A path-based commit can include unstaged content; it is not an index filter. Do not reset or rewrite another track’s work to repair a mixed commit.

### Concurrent multi-session repo drift
Unexplained repo/file state with no task-notification is often a concurrent human session on this machine, not noise or injection. Verify via `git log`/`git status`/`git diff` and available host activity records before assuming or overwriting. **Recurred a 4th time (2026-08-23, `technology-updates`) as an actual destructive action**, not just a risk: having already flagged an out-of-band commit from a concurrent session earlier in the same conversation, a later surprising diff in that same file was still attributed to a delegated sub-agent instead, and reverted with `git checkout -- <file>` before asking. If you've already surfaced concurrent-session evidence this session, that's the leading hypothesis for the next surprising diff — check it first, and never `git checkout`/`git restore`/`git reset` a diff of uncertain origin without a fresh `git log` on that exact file and, if still ambiguous, asking before reverting. (detail: memory "project_concurrent_multisession_repo_drift")

The same independent-check discipline runs the other direction too: a sub-agent's own claim that an anomaly is "possible concurrent activity" needs the identical verification as a claim that nothing's wrong — don't let a self-remediating implementer's more-alarming explanation for its own mistake pass unchecked just because it sounds like appropriate caution. Confirmed 2x in one plan: an implementer that had just fixed its own worktree-cd mistake flagged an untracked file on `main` as concurrent activity; independently checking `git log`/`git status`/file timestamps against session start showed it was pre-existing both times. (detail: memory "feedback_independent_verification_catches_false_alarms")

### `gh pr checkout` is not worktree-safe

Before switching a PR checkout, verify which checkout the host command will target. In an assigned worktree, fetch the branch and select it using Git from that checkout only when repository instructions and clean state permit. Verify cwd, branch, and status afterward; never switch another checkout as a side effect.

### `core.hooksPath` collision across worktrees
It's a single value in the shared `.git/config`, not per-worktree — a sibling worktree running `husky init` can silently overwrite it repo-wide, defeating the pre-commit hook everywhere else with no error at commit time. Fix per worktree needing isolation: `git config extensions.worktreeConfig true && git config --worktree core.hooksPath <relative-path>`. (detail: memory "project_hookspath_worktree_collision"; mechanism also documented in `git` skill)

### Remote default-branch changes do not repair existing clones

Changing the server’s default branch does not update every clone’s cached remote HEAD. Resolve the task’s actual remote and intended base, fetch when current remote state matters, and verify the new checkout’s ancestry against that base. Preserve deliberate feature-branch bases and unpublished local work; do not hard-code `origin/main` or require every checkout to equal the remote default.

### `git worktree remove` ordering

Preserve commits, untracked and valuable ignored artifacts, and confirm no session or process needs the checkout. Move outside it before removal. Return owned pool leases through their manager; use host lifecycle tools when they own the checkout. Never force removal or delete branches as a cleanup side effect.

### Merging/pushing a worktree branch into `main`

A checkout guard or sandbox refusal is a boundary. Do not bypass it, redirect Git into a protected shared checkout, or rewrite a checked-out branch through fetch. Preserve the task branch and use the authorized PR flow; report any remaining operation that requires the owner or host’s supported checkout transition.

### Worktree guard also refuses compound/chained git commands as "too complex"

Use a simple Git invocation against the assigned checkout. Do not hide a refused operation inside shell wrappers, an alternate interpreter, or a different session.

### The worktree sandbox blocks any `source`d command, not just git redirections

Use a supported installed runtime or explicit executable path. Do not reinterpret a sandbox denial as permission to bypass it. Report unavailable runtime setup when it blocks the requested check.

### Gitignored artifacts do not transfer with a worktree

Git checks out tracked content. Before allocation or removal, inspect valuable ignored review reports, screenshots, diagnostics, and untracked work. Preserve the artifacts the task still needs in a verified destination before removing the checkout. Do not copy mutable dependency trees or unrelated private files merely to reproduce the main checkout.
