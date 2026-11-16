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
Selecting a PR loads its current revision with ghlite. If you are already in that revision's checkout, comments load in your existing source buffer. Otherwise, its description opens in the current window; use `,ol` to open a detached review worktree without changing your original checkout.

## Inline review

For the PR on your current branch, run `:PRReviewCurrent` or press `,gP`. Review threads appear as diagnostics in ordinary source buffers, alongside your usual navigation and language-server features. Start or resume a pending review with `,or`; adding inline feedback with `,oc` also starts or resumes one automatically. These actions use the current tab and do not open a diff layout.

In an active review's source buffers and PR description, `,o` opens the which-key review menu. Outside those buffers, `,o` retains Treesitter selection. The previous `,rs`, `,rp`, `,rv`, `,rq`, and `,rl` shortcuts remain available.

| Review menu | Action |
| --- | --- |
| `,or` | Start or resume a pending GitHub review |
| `,oc` | Add an inline comment or reply; visual mode comments on selected lines |
| `,oh` | Read the thread at the current line |
| `,of` | Open the file picker in the review checkout |
| `,ov` | Toggle file viewed |
| `,op` | Load review comments, including pending comments, into quickfix |
| `,os` | Submit the pending review |
| `,oa` | Approve the PR, including pending feedback |
| `,ox` | Request changes, including pending feedback |
| `,oq` | Return to the originating review queue |
| `,ol` | Open a local review worktree |
| `,ob` | Open the PR in the browser |
| `,ot` | Resolve the thread at the current line |
| `,oT` | Reopen the thread at the current line |

Comment entry uses a temporary buffer in the current window. Press **Ctrl-S** in normal or insert mode to save it to the pending review and return to the source buffer. Inline feedback remains unpublished until you submit the review. Pending reviews are stored on GitHub and can be resumed after restarting Neovim. The review shortcuts use ghlite's GitHub review mode explicitly.

The checkout must match the loaded PR head. Inline comments are refused when the current source file has unsaved edits or differs from that revision on disk, so shifted local lines cannot be mistaken for PR lines. Opening source files uses your normal editor configuration, including language servers and project-local tooling.

Submission uses ghlite's native review actions. Failed submission retains the pending review for retry. Use `,oq` to return, then refresh with **Ctrl-R** to hide PRs reviewed at their current head. Select the next PR yourself.

The native `:GHLitePR*` commands remain available. Optional diff views are available through `:GHLitePRDiff`; they are not part of the default inline flow.

## Local files

Run `:PRReviewCheckout [clone-path]` from a queued PR; the path is optional. Choose a matching clone under `~/src`, or supply its path when prompted. Checkout creates a detached worktree under `<primary-checkout>/.worktrees/`, which must be ignored. Its files open in the current tab, with inline feedback attached to the selected PR.

Run `:PRReviewCleanup` to remove an owned review worktree after leaving its working directory and unloading its source buffers. Cleanup retains active worktrees, uncommitted work, and ignored artifacts. It preserves the review commit on a named retention branch.

## Workflow detectors

```sh
nvim --headless -u NONE -i NONE -n -l nvim/tests/pr-reviews.lua
nvim --headless -u NONE -i NONE -n -l nvim/tests/pr-review-checkout.lua
```

The queue detector exercises configured startup with controlled GitHub responses, without live review submissions.
