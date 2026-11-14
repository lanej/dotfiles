# Git and GitHub verification

### Git push/merge

Read the actual remote ref or PR head after publication and compare it with the intended commit. A local cached tracking ref, a remote description, or the command’s exit code alone does not establish the resulting remote commit. Resolve the destination branch from the task rather than assuming `main`.

### Branch-comparison claims ("clean fast-forward")
Before telling the user a merge/push is safe or a fast-forward, run the comparison in its own isolated tool call (not concatenated with other commands) and check both directions explicitly (`git log --oneline HEAD..main` AND `main..HEAD`, or `git merge-base` plus both counts) — a one-directional or concatenated-output check is easy to misread as "no divergence" when the other direction actually has commits. Confirmed in `analysis-doc` (2026-08-29): told the user "clean fast-forward" based on a misread `HEAD..main` check, when `main` actually had 6 commits the branch lacked and the branch had 13 `main` lacked — a real fork, not a fast-forward. (detail: memory "feedback_verify_branch_comparison_before_stating")

### Unattributed repo changes

A delegate’s denial is still self-report. Inspect current history and diffs, task timing, and the host’s available transcript or activity records before attributing a change. Claude JSONL session logs can be useful on Claude hosts; use the actual host’s records and tools instead of assuming those paths or `CronList` exist. Preserve uncertain changes, report unavailable provenance evidence, and ask the owner before discarding work.

### Unauthorized remote/repo creation by a `gh`-capable sub-agent
A commit/build/live-smoke-test verification pass does not surface a sub-agent creating org-visible remote infrastructure (a new GitHub repo, a changed `origin`, a webhook) it wasn't briefed to create — this isn't fork-specific, it happens with any agent that has `gh` or another network-mutating tool. After any such dispatch, add `git remote -v` (and `gh repo view <name>` if a new remote appears) to the verification pass as a matter of course, not only when a later task happens to need the remote state. If an unauthorized remote turns up, the next brief into that repo must explicitly enumerate what's forbidden (`gh repo create`, `git push`, Pages/settings changes) rather than assuming "local only" was implicit. (detail: memory "feedback_subagent_remote_repo_creation_missed_by_verification")

- **Monorepo git pathspec double-prefixing**: from a cwd already inside `~/workspace/projects/<name>/`, a pathspec re-prefixed with `projects/<name>/...` silently returns empty (`git log`/`git diff` exit 0, no error) instead of erroring — use the path relative to cwd instead. Recurred in two different projects 4 days apart. (detail: memory "feedback_monorepo_git_pathspec_double_prefix")

Stage exact intended paths or hunks. Review the staged snapshot and resulting commit after each commit-capable dispatch; source-code project policy controls attribution and commit conventions.
