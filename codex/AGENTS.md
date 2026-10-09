# Unix philosophy

Follow Eric S. Raymond's 17 Unix rules when designing and changing software:

1. **Modularity:** Build simple components with clean interfaces.
2. **Clarity:** Prefer readable code over clever code.
3. **Composition:** Make programs easy to connect.
4. **Separation:** Keep policy apart from mechanism, and interfaces apart from engines.
5. **Simplicity:** Add complexity only when necessary.
6. **Parsimony:** Build large programs only when smaller solutions cannot work.
7. **Transparency:** Make behavior visible and easy to inspect.
8. **Robustness:** Reliability follows from simplicity and transparency.
9. **Representation:** Put knowledge into data so logic can stay simple.
10. **Least Surprise:** Make interfaces behave as users expect.
11. **Silence:** Produce no output when there's nothing useful to report.
12. **Repair:** Recover where possible; otherwise fail early and clearly.
13. **Economy:** Prioritize programmer time over machine time.
14. **Generation:** Automate repetitive programming work.
15. **Optimization:** Make it work before tuning performance.
16. **Diversity:** Be skeptical of any supposedly universal approach.
17. **Extensibility:** Design to accommodate future changes.

# Automatic PR writing and code review

For every pull request, invoke the `pull-request-writer` custom agent as a
separate subagent to draft or revise its title and description before opening
the PR or completing an update to it. Give it the final diff against the base
branch, the motivation, repository PR requirements, and relevant validation
evidence. Wait for its draft, resolve any blockers, and use its title and
description. This applies to simple and documentation-only PRs too. Run it
for each proposed PR revision, rather than every commit.

Invoke `code-reviewer` separately when a change is complex: interacting
components, nontrivial algorithms or state transitions, concurrency, migrations,
security-sensitive logic, or uncertainty about correctness that warrants an
independent technical review. Judge the behavior and interactions, not line
count. Simple, mechanically verifiable edits do not require it. Its trigger is
complexity, not committing or creating a PR.

Give the code reviewer the task's changed files and relevant context, keeping
unrelated work out of scope. Ask for actionable correctness, security, and
regression findings under the repository's conventions and testing policy.
Wait for the review and address actionable findings before finishing. Have the
reviewer check any material fixes made in response to its findings.

These rules apply to the primary agent; the writer and reviewer subagents must
not invoke further writers or reviewers. If named custom-agent selection is
unavailable, launch a generic subagent with the `developer_instructions` from
`~/.codex/agents/<agent-name>.toml` and require read-only drafting or review.
If neither route is available, report the delegation gap explicitly.

# Pull request descriptions

Keep PR descriptions concise: explain the final change and why, show the result, and add only context the diff and checks do not already provide. Let tests and automated checks report their own results; do not duplicate test cases, coverage figures, test counts, or CI results in the description. Mention manual validation, external evidence, or known verification gaps only when they add information. Omit unused sections, boilerplate checklists, and implementation history.

Include a screenshot when it helps reviewers understand or assess a visual change. Omit it when the diff and prose already explain the change adequately; screenshots are not required for every PR. When included, show the actual current result, use a durable image URL that renders inline on GitHub, and verify that it loads before handing off.

# Git worktree cleanup

Treat cleanup of temporary worktrees created for the task as part of completion.
This includes temporary worktrees created by subagents for the same task.
Record their paths and the starting checkout so ownership stays clear across
subagents and handoffs.

Before the final response, remove each task-owned temporary worktree whose work
is safely retained and which no active session, process, or pending task needs.
An open PR alone does not require keeping its checkout: keep the branch for
review updates and recreate a worktree when needed. Preserve commits on a named
branch or verified remote ref before removing a detached worktree.

Check `git status --short --untracked-files=all` and any valuable ignored files
before removal. Retain a worktree with uncommitted work or needed local artifacts
unless that work has been preserved elsewhere. Leave pre-existing, permanent,
user-owned, and other agents' active worktrees alone; age is not proof of
inactivity.

Move outside the worktree first, then use `git worktree remove <path>` from a
surviving checkout. Do not force removal or delete branches as a cleanup side
effect. For registrations whose directories are already gone, inspect
`git worktree prune --dry-run --verbose` before running `git worktree prune`.
Verify the result with `git worktree list`.

Do this cleanup within the authorized task without asking for routine
confirmation. If a task-owned worktree must remain or removal is blocked,
include its path and the concrete reason in the final response.

# Development storage

Use the normal shared package-manager download caches; do not create a cache
per worktree. Link read-only datasets, verified package artifacts, and browser
installations to their canonical locations. Keep mutable dependencies and build
outputs isolated when versions differ. Remove disposable test dependencies and
temporary caches at task completion while retaining useful logs and artifacts.
See `~/.files/docs/development-storage.md` for the installed cache budgets.
