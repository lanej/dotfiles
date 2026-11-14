# Codex PR publication through Octo

In Codex, use `octo-manager submit-pr` to create GitHub PRs. It replaces Codex's use of `gh-pr-create-from`: callers supply purpose and validation facts, and Octo owns the dedicated writer, publication checks, creation, and tracking. Do not fall back to direct publication when Octo is unavailable or a requirement is unmet; report the limitation and preserve the submission for recovery. Tracking an existing PR remains independently available and does not establish publication compliance. Claude retains its separate `github-pr-writer` and `gh-pr-create-from <file>` publication path.

Commit and push the change, then hand Octo facts about its purpose and validation. Octo reads the frozen GitHub diff and contribution guidance, runs a dedicated PR writer, publishes, and enrolls the PR to the calling session. Agents can continue working while Octo watches checks and actionable reviews. Public and private repositories require no allowlists.

The submission record binds the request to a repository, head SHA, resolved base SHA, policy version, recorded writer stage, structured draft, and requirement results. Octo checks publication blockers and rechecks the Git revision before publishing. Missing required content and unresolved blockers prevent publication. Mechanical checks enforce supported title and body rules; semantic requirement results remain model assessments, and caller-reported validation is not independently observed evidence. This is a publication workflow contract, not a claim that prose correctness can be proven by a schema.

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

Alternatively, use `octo-manager submit-pr --purpose 'Problem and intended outcome' --thread-id SESSION --cwd DIRECTORY` from the pushed branch. This derives the repository, base branch, and head revision. Use an intent file when supplying validation or precise branch facts. Title/body arguments are drafting context for Octo's writer, not approved publication artifacts. The Codex hook rejects publication through `gh-pr-create-from` with migration guidance; read-only `--check` remains available, and Claude retains the publisher.

The current Octo submission schema supports `owner.harness = "codex"` only. Use the actual calling session identity; do not submit from Claude or another harness using an invented Codex owner. Do not treat this command as an update operation: existing PR title/body revisions still require a separate `github-pr-writer`, resolution of its blockers, and verification of the saved revision; they do not acquire Octo publication provenance retroactively.

`octo-manager submission ID` shows the durable record, worker results, pinned policy, draft, and published URL. Retry a failed or uncertain operation with `retry-submission ID`; reuse the same request when retrying a timed-out initial call. Use a new request ID when facts change. A `needs_input` result requires corrected facts in a new request. `cancel-submission ID` cancels work before publication; after publication begins, reconcile with retry. Success means both publication and enrollment completed. Receipt of a notification is separate from completing its requested action.

Inspect policy using `repo-policy get --repo owner/repository`, render its template with `repo-policy template --repo owner/repository --tier routine`, or request `repo-policy refresh` from a pushed change branch. Repository policies are immutable versions keyed by relevant source hashes and contract versions. Routine commits reuse the policy; contribution/template changes trigger analysis. Description ranges are advisory: routine 20–100 words, standard 100–250, complex 250–600. Risk and semantic scope matter alongside size; include necessary context without padding. Explicit repository requirements and writer blockers gate publication.

The Codex submission hook is not installed by default. Enable it with `make codex-octo-hook`, then review/trust the changed definition through Codex's native Hooks interface. It translates supported standalone `gh pr create` commands into Octo submissions and supplies the actual calling session identity for explicit submissions. Run publication separately from shell pipelines, redirections, variable expansion, or compound commands. Unrelated shell commands pass through. Installation appends to existing configuration without reordering hooks or changing trust. Reload global instructions using `make codex-guidance`. Existing sessions may require hook review or reload before the adapter runs. The required publication command applies without the hook; enforcement by a hook requires installation and host trust. These hooks inspect supported tool commands, not arbitrary shell execution or use of GitHub credentials outside that boundary.

To stop automatic translation, run `python3 bin/codex-octo-submit --uninstall`. This removes only the submission hook, preserves other hooks and native trust, and leaves explicit `octo-manager submit-pr` commands available.
