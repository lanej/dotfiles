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
