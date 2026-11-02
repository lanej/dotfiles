# Firstmate through Paseo and GitHub

Use one ordinary Paseo conversation for intake, steering, and status. Firstmate owns the queue, task assignment, supervision, recovery, and delivery policy. An assigned Pi worker implements its task, receives GitHub feedback directly, revises and verifies, and replies in the same discussion. [Issue #134](https://github.com/lanej/dotfiles/issues/134) owns the requirements and design diagrams.

This replaces the resident Claude bugfix dispatcher and generic dispatcher. There is no separate model agent relaying each review comment.

## Setup

Add `firstmate-mobile` to the machine's existing `sets` array in `~/.config/dotfiles/config.toml`. Keep the native OS set and any work sets such as `easypost`.

```sh
make plan
make install
```

The opt-in set installs Pi 1.4.0 and the Paseo 0.14.0 CLI, uses the existing Firstmate installer, and configures a dedicated **Firstmate** provider extending Paseo's native Pi provider. Existing providers, credentials, pairing, and machine choices are preserved. Configuration alone is available through `make firstmate-mobile-config FIRSTMATE_HOME=/path/to/firstmate`; it requires an initialized Firstmate home and Node. Default `make` retains its configuration-only behavior, and `make base` remains the dependency-light native baseline.

Use the existing Paseo app/daemon and private connection. Open one conversation in the selected Firstmate home with the **Firstmate** provider, and return to that conversation for further work. Paseo owns its process and persisted session reference; the configured command is `firstmate rpc`. It forwards Paseo's RPC/session arguments unchanged, sets the Firstmate home, and loads the feedback extension without starting a tmux or Zellij captain. The worker backend remains independently selected.

Trust the Firstmate checkout through Pi's normal project-trust flow so the tracked watcher, turn-end guard, and supervision branch load. `firstmate rpc` checks prerequisites but does not prove those extensions are running. Existing upstream session-start diagnostics still apply. Do not create a second captain while the terminal primary is supervising the same home.

The generated `config/github-feedback.json` is private to that Firstmate home:

```json
{"owner":"lanej","pollSeconds":30}
```

Set `owner` deliberately: that login's feedback is task direction. Other authors supply review input within the assigned scope. Agent replies are recognized by locally recorded reply intent and a GitHub marker, so using the same login for human and agent comments does not discard human feedback. Existing local configuration is preserved during setup.

GitHub authentication uses `GH_TOKEN`, `GITHUB_TOKEN`, or the existing HTTPS git credential helper. The bridge never prompts for credentials, invokes `gh`, or writes tokens into Paseo configuration. Grant access to the intended repositories, issues, PR discussions/reviews, and checks. Authentication or observation failures retain pending work and surface an error in the owning Pi conversation.

For work, keep `easypost` selected and choose the intended `amazon-bedrock` model in Paseo. The Pi launch imports the existing `~/.config/bedrock/env` when a Bedrock token is not already inherited; it does not change models, credentials, or providers. Verify the actual selected provider with a small live task before adoption. Missing/expired credentials must be repaired through the existing work credential setup.

## Intake and ownership

Give Firstmate work through Paseo, or explicitly queue an existing GitHub object:

```sh
firstmate github intake https://github.com/owner/repository/issues/123
```

Intake uses Firstmate's existing tasks-axi wrapper and a stable URL-derived task ID; repeated intake keeps the same task. It queues work and leaves dispatch to Firstmate. For tracked implementation work, Firstmate selects a Pi worker through its existing spawn/profile policy, preserving other crew preferences. Follow the normal project registration, scope, review, and delivery rules. Link a resulting PR through existing task/backlog records or `bin/fm-contributions.sh enroll <task> <PR URL>` in the Firstmate home.

The bridge reads the canonical contribution projection from `fm-fleet-snapshot.sh` and `fm-contributions.sh`; labels, repository-wide issue discovery, and session-name searches do not establish ownership. Multiple recorded owners or unavailable/non-Pi owners require Firstmate reconciliation before direct delivery. Task records remain authoritative for generation, branch, and worktree.

The worker extension records its persisted session under `data/<task>/github-session.json`, tied to the current native task generation and worktree. An existing generation requires resuming that exact session. A different live process cannot claim it. Keep the owner and worktree through review waits; opening a PR does not complete the task.

## Feedback and recovery

The primary extension polls tracked issue/PR comments, formal reviews, inline comments/thread resolution, PR revision/check/status changes, and issue/PR state. REST observations reuse ETags within the live runtime. It checks the PR head again after observation and retries later if it changed. Polling is deterministic and does not request a model turn unless work or recovery needs attention. A failed object's observation does not prevent unrelated tasks from receiving feedback.

Pending observations and their cursor are saved together under `state/github-feedback/`. Delivery uses Firstmate's own idempotent steering-inbox writer. The owning Pi extension consumes GitHub records from its existing `state/<task>.inbox/` and queues a follow-up through Pi's extension API. No second process competes for Paseo's RPC stdin. Ordinary Firstmate steering records retain their existing handling.

The worker reads the current thread, revision, and checks, makes scoped changes, and runs the project's verification. `firstmate_github_reply` posts in the source conversation or inline thread; a retry searches for the exact recorded reply before posting. `firstmate_github_done` records a concise outcome in the existing task status file and moves that event into the inbox's native `handled/` directory. Its `needsFirstmate` flag opens a keyed decision for scope, priority, blockers, or delivery authority. Finishing an event does not finish the task. Firstmate reconciles answers with its existing outstanding-decision records across GitHub and Paseo.

Delivery is at least once across interrupted turns. Pending inbox records are presented again after a session resumes, and reply retries are idempotent. The worker must inspect existing GitHub/branch results before repeating work. The bridge does not promise exactly-once arbitrary model or git operations.

If a Pi worker exits, feedback stays in its inbox and Firstmate receives the recorded session reference for recovery. Reconcile surviving workers, then resume through Firstmate's supported lifecycle or explicitly reassign the task. Do not create another worker merely because its endpoint is unavailable. The owner record remains available after process exit.

The primary owns the poller and must hold Firstmate's native session lock; a lock-refused session cannot poll or route work. While its host process is stopped there are no polls. Paseo's supported session recovery resumes the primary, whose first eligible poll catches up. A phone disconnect does not stop the host process or workers. Native Firstmate locks serialize pollers and owner registration; the lease process releases its lock when its parent pipe closes.

```sh
# Inspect/catch up using the same deterministic adapter (outside another active poll).
firstmate github poll
# Reinstall the provider configuration after deliberately changing the selected home.
firstmate github configure-paseo
```

Approval satisfies the applicable review requirement. Firstmate must separately confirm delivery authority and revalidate the actual current head and required checks before merging. Neither the bridge nor its worker tools has an automatic merge path. A changed revision or failing check invalidates prior readiness under the project's existing policy.

## Retiring the dispatcher

The old launcher, workers, skills, and their standalone launch detector are removed. Setup removes only obsolete bin symlinks targeting those exact files in this checkout; normal shared-agent synchronization prunes retired skill links. Existing dispatcher sessions, worktrees, locks, and unlanded changes are preserved. Finish or explicitly retire old work before moving it into Firstmate; do not run both owners against the same task.

## Verification and adoption

```sh
npm install --prefix /tmp/firstmate-github-runtime --ignore-scripts \
  @earendil-works/pi-coding-agent@1.4.0 @getpaseo/server@0.14.0 \
  @getpaseo/cli@0.14.0 tasks-axi@0.2.6
FIRSTMATE_TEST_RUNTIME=/tmp/firstmate-github-runtime \
  FIRSTMATE_SOURCE=/path/to/firstmate make test-firstmate-github
```

The representative workflow uses the actual installer, Firstmate ownership projection/inbox library, Paseo's native Pi RPC runtime, and real Pi processes. It queues an issue, resumes the same primary and worker, catches up review left during downtime, edits and tests a real fixture repository, publishes its isolated branch to a local bare remote, replies inline, and returns an outcome without merging on approval. HTTP model responses and GitHub are controlled fixtures; native Firstmate dispatch metadata/primary lock are seeded and ambient upstream primary extensions are disabled in this detector. Workers load the bridge through the installed global Pi configuration. It establishes the bridge and RPC/session path, not live autonomous crew supervision or model judgment.

The native scripts are measured against Firstmate commit `21180385d1cb782941df13ed91ba7c44f0d76351`. Use an updated checkout with compatible contribution, steering-inbox, and Pi supervision contracts. Changes to those contracts need deliberate revalidation.

Keep this opt-in until a live Bedrock/Pi/Paseo/GitHub smoke run proves upstream watcher/guard/branch loading, task completion reaching the primary without another prompt, actual phone disconnect/reconnect, and notifications. Fixture success does not establish those live properties. Issue #134 remains open for that adoption evidence.
