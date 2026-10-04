# Automatic code review

Before completing any task that creates or modifies code, scripts, or
configuration, invoke the `code-reviewer` custom agent as a separate subagent.
Do this automatically; the user does not need to ask for review. Give it the
task's changed files and relevant context, keeping unrelated work out of scope.
Ask for actionable correctness, security, and regression findings under the
repository's own conventions and testing policy. Wait for its review and
address actionable findings before the final response. If review-driven fixes
materially change the implementation, have it review those fixes too.

This rule applies to the primary agent. The `code-reviewer` subagent must not
invoke another reviewer. If the runtime cannot select custom agents by name,
launch a generic subagent with the `developer_instructions` from
`~/.codex/agents/code-reviewer.toml` and require a read-only review. If neither
route is available, report the review gap explicitly rather than claiming the
review ran.

# Pull request descriptions

Keep PR descriptions concise: explain the final change and why, show the result, and add only context the diff and checks do not already provide. Let tests and automated checks report their own results; do not duplicate test cases, coverage figures, test counts, or CI results in the description. Mention manual validation, external evidence, or known verification gaps only when they add information. Omit unused sections, boilerplate checklists, and implementation history.

Include a screenshot when it helps reviewers understand or assess a visual change. Omit it when the diff and prose already explain the change adequately; screenshots are not required for every PR. When included, show the actual current result, use a durable image URL that renders inline on GitHub, and verify that it loads before handing off.
