# Pull request publication

Use `octo-manager pr publish --title TITLE --body-file FILE --track` to publish a caller-written PR description and enroll tracking. Omit `--track` when only publication is wanted. Follow repository contribution requirements and the PR-writer guidance before publication. Octo validates the local contract and pushed revision; it does not draft descriptions or require model-generated policy analysis.

Initialize a repository contract with `octo-manager pr init`, inspect its instructions with `octo-manager pr instructions`, and validate the final description with `octo-manager pr validate --title TITLE --body-file FILE`. Explicit `pr init --derive` or `pr guidance refresh` can sample repository history for advisory guidance; inferred rules do not become mandatory automatically.

`pr publish` runs independently of the daemon and saves a durable local publication receipt. Inspect receipts with `octo-manager publication list` and `octo-manager publication show ID`. `publication retry ID` reconciles uncertain creation before attempting any permitted publication; it must not create another PR after an uncertain write. The daemon automatically reconciles saved legacy publication attempts without drafting or publishing new PRs.

The optional Codex hook translates standalone `gh pr create` commands and supplies the calling session identity. It also recognizes `octo-manager pr publish` and the retained `submit-pr` compatibility entrypoint, replacing caller identity flags with the hook event identity. Unrelated commands pass through. Shell composition and expansion around publication commands are rejected rather than guessed.

Install the hook through the opt-in Octo integration. `python3 bin/codex-octo-submit --uninstall` removes only this submission hook and preserves other hooks and native trust. Explicit publication commands remain available.

Tracking an existing PR is independent: use `octo-manager pr track --url URL --thread-id SESSION`. Tracking or receipt does not establish review approval, resolve actions, or authorize a merge.
