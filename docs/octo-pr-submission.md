# Optional PR submission through Octo

This workflow is opt-in. Ordinary PR creation with the separate PR writer remains the default, and tracking checks/reviews does not require Octo to publish the PR.

When choosing this experiment, commit and push the change, then hand Octo facts about its purpose and validation. Octo reads the frozen GitHub diff and contribution guidance, runs a dedicated PR writer, publishes, and enrolls the PR to the calling session. Agents can continue working while Octo watches checks and actionable reviews. Public and private repositories require no allowlists.

Use `octo-manager submit-pr --intent-file FILE --thread-id SESSION --cwd DIRECTORY`. The Codex hook supplies session identity from its event; outside a hook, pass it explicitly. An example intent follows; use the actual pushed revision and a stable request ID. The installed Octo schema is the authoritative contract.

```json
{
  "requestId": "my-task-submit-v1",
  "repository": "owner/repository",
  "headRef": "fix/example",
  "headSha": "0123456789abcdef0123456789abcdef01234567",
  "baseRef": "main",
  "purpose": "Explain the observed problem and intended behavior.",
  "validation": [
    {"command": "make check", "result": "passed", "note": "Caller observed the command complete locally."}
  ],
  "draft": false,
  "owner": {"harness": "codex", "endpoint": "local", "sessionId": "CALLER_SESSION", "label": "/path/to/repository"}
}
```

Alternatively, use `octo-manager submit-pr --purpose 'Problem and intended outcome'` from the pushed branch. This derives the repository, base branch, and head revision. Use an intent file when supplying validation or precise branch facts. The hook also translates standalone `gh pr create` with title/body/base/head/repo/draft flags and `gh-pr-create-from FILE`; these become drafting context for Octo's writer. Run publication separately from shell pipelines, redirections, variable expansion, or compound commands. Unrelated shell commands pass through. This hook is an ergonomic adapter; the agent contract governs submission.

`octo-manager submission ID` shows the durable record, worker results, pinned policy, draft, and published URL. Retry a failed or uncertain operation with `retry-submission ID`; reuse the same request when retrying a timed-out initial call. Use a new request ID when facts change. A `needs_input` result requires corrected facts in a new request. `cancel-submission ID` cancels work before publication; after publication begins, reconcile with retry. Success means both publication and enrollment completed. Receipt of a notification is separate from completing its requested action.

Inspect policy using `repo-policy get --repo owner/repository`, render its template with `repo-policy template --repo owner/repository --tier routine`, or request `repo-policy refresh` from a pushed change branch. Repository policies are immutable versions keyed by relevant source hashes and contract versions. Routine commits reuse the policy; contribution/template changes trigger analysis. Description ranges are advisory: routine 20–100 words, standard 100–250, complex 250–600. Risk and semantic scope matter alongside size; include necessary context without padding. Explicit repository requirements and writer blockers gate publication.

The submission hook is not installed by the default Codex setup. Explicitly opt into its command translation with `make codex-octo-hook`, then review/trust the changed definition through Codex's native Hooks interface. Installation appends to existing configuration without reordering hooks or changing trust. Reload global instructions using `make codex-guidance`. Existing sessions may require hook review or reload before the new adapter runs.

To stop automatic translation, run `python3 bin/codex-octo-submit --uninstall`. This removes only the submission hook, preserves other hooks and native trust, and leaves explicit `octo-manager submit-pr` commands available.
