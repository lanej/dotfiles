# Neovim PR review queue

In a GitHub checkout, open `:PRReviews` or press `,gR` for that repository’s review requests.
Use `:PRReviewsAll` for personal and team requests across repositories from any Neovim session.
Outside a GitHub checkout, `:PRReviews` explains the failure and suggests `:PRReviewsAll`.

Run `nvim-gh-review` to launch your configured Neovim into the cross-project queue.
The queue opens after startup, with automatic project session restore and save disabled.
It accepts normal Neovim arguments and makes `:PRReviews` and `,gR` global for that session.
Install with `make nvim-gh-review`; `make vim-config` also installs the launcher.

Authenticate `gh` against GitHub.com with repository access.
Discovery searches your personal requests and requests to teams you belong to.
Sources appear as **personal** or **team**.
The picker displays discovery errors and truncation.

The picker reopens from cache; snapshots stay separate by account and queue scope.
Saved snapshots survive editor restarts.
Snapshots stay fresh for five minutes; older snapshots refresh in the background.

Rows stay visible and your typed filter stays intact during refresh.
The header shows scope, cache age, account, and refresh progress.

Passing checks come first, followed by pending, failed, missing, and unknown results.
Within each group, personal requests precede team requests; older PRs come first.
Successful, skipped, and neutral checks count as passing.
Only `check-all-owners` in **Require All Owners Approval** is excluded from ranking.
Its status remains visible in the preview.

Drafts, your own PRs, and PRs reviewed at their current head are omitted.

Press **Ctrl-R** to refresh and verify the active account.
Add `!` to `:PRReviews` or `:PRReviewsAll` to force refresh.
**Ctrl-A** toggles already reviewed PRs using cached rows.

Picker actions and `,oq` preserve the originating queue.
Directory changes and local checkout keep that scope.
Selecting a PR reloads its clean Octo description and discussion.

In PR and review buffers, `,o` opens the which-key review menu.
In ordinary code buffers, `,o` retains Treesitter selection.

| Review menu | Action |
| --- | --- |
| `,or` | Start or resume review |
| `,oc` | Add a comment or reply |
| `,oS` | Suggest on current or selected diff lines |
| `,of` | Pick changed files; toggle panel in diff review |
| `,ov` | Toggle file viewed |
| `,op` | View pending comments |
| `,os` | Open native submission window |
| `,oq` | Return to the originating queue |
| `,ol` | Open a local worktree |
| `,ob` | Open PR in browser from description buffer |
| `,ot` | Resolve thread |
| `,oT` | Reopen thread |

The previous `,rs`, `,rp`, `,rv`, `,rq`, and `,rl` shortcuts remain available.

Use Octo’s remote diffs, inline comments, and suggestions.
Opening a PR does not start a review.
Save inline comment buffers with `:write` before submitting.

In the submission window’s normal mode, `,oa` approves, `,oc` comments, and `,or` requests changes.
**Ctrl-A**, **Ctrl-M**, and **Ctrl-R** perform the same actions.

Submission uses installed Octo behavior, without added stale-head checks or outcome reconciliation.
Successful submission closes the review layout.

Use `,oq` to return, then refresh with **Ctrl-R** to hide reviews at the current head.
Select the next PR yourself.

## Local files

Run `:PRReviewCheckout [clone-path]` from a queued PR; the path is optional.
Choose a matching clone under `~/src`, or supply its path when prompted.
Checkout creates a detached worktree under `<primary-checkout>/.worktrees/`, which must be ignored.
Local files open in a separate tab; leave feedback in the remote Octo review.

Run `:PRReviewCleanup` to remove an owned review worktree.
Cleanup retains active worktrees, uncommitted work, and ignored artifacts.
It preserves the review commit on a named retention branch.

## Workflow detectors

```sh
nvim --headless -u NONE -i NONE -n -l nvim/tests/pr-reviews.lua
nvim --headless -u NONE -i NONE -n -l nvim/tests/pr-review-checkout.lua
```

The queue detector exercises configured startup with controlled GitHub responses, without live review submissions.
