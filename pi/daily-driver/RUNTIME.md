# Pi daily-driver runtime plan

This is the implementation sequence beyond the [foundation](README.md). The driver supports opt-in read-only delegation in native managed worktrees and browsing existing archives. Local Beads admission and interactive Zellij launch use the revision-guarded Beads HTTP service. Lead plan approval, Pi-owned Octo delivery, and operator-triggered archival use that launch path. The target is one usable local coding workflow before expanding fleet and remote interfaces.

The current [task contract](https://github.com/lanej/dotfiles/issues/353) keeps task identity, accepted briefs, hierarchy and dependencies in Beads. The Pi integration owns execution attempts and native sessions; Octo owns GitHub operations and their receipts. A task can exist without a GitHub issue or PR. This follows the live [parent design](https://github.com/lanej/dotfiles/issues/349) and [Octo boundary](https://github.com/lanej/dotfiles/issues/356).

## Reuse existing Pi packages

The driver uses [@tintinweb/pi-subagents](https://github.com/tintinweb/pi-subagents) for child execution. It supplies role-specific models/reasoning, background runs, steering, persistent sessions, a fleet view and lifecycle events. Keep the dotfiles extension focused on policy and integration. Do not build another subagent engine around the raw SDK.

| Package | Useful capability | Decision for this workflow |
| --- | --- | --- |
| [@tintinweb/pi-subagents](https://github.com/tintinweb/pi-subagents) | Delegation and lifecycle controls with a documented cross-extension RPC. | Pinned to 0.26.2. The driver loads its child runner behind a managed adapter. |
| [nicobailon/pi-subagents](https://github.com/nicobailon/pi-subagents) (`pi-subagents` on npm) | Structured delegation, launch preflight, capability ceilings and background-work integration. | Alternative if its [integration API](https://github.com/nicobailon/pi-subagents/blob/main/docs/extension-api.md) materially reduces the policy adapter. Published 0.89.1 and source 0.89.2 are distinct; compatibility remains untested here. |
| [pi-git-diff](https://github.com/max-miller1204/pi-git-diff) | Native terminal viewer for staged, unstaged and untracked changes. | Pin 0.1.1 and load its operator-facing `/diff` command in managed lead sessions. |
| [pi-smart-plan](https://github.com/jnardiello/pi-smart-plan) | Structured plans, approval, dependency validation and parallel execution. | The lead uses its existing revision-guarded Beads authority for task creation and approval. |
| [pi-workgraph](https://github.com/gjtorikian/pi-workgraph) | Leases, planning, independent judgment and an executor protocol. | Its per-repository SQLite store supplies its own task authority. Beads remains the canonical task store. |
| [pi-messenger](https://github.com/nicobailon/pi-messenger) | Peer messaging, presence and file reservations. | Optional later. Its Crew mode owns another task/dependency workflow, so it does not replace Beads in this design. |
| [pi-beads](https://pi.dev/packages/pi-beads) | Existing Beads task editing interface. | Review later. It expects a project `.beads` directory and exposes mutations; it does not provide the required authority fence or the current explicitly configured read-only source contract. |
| [pi-ext Session Snap](https://github.com/tomsej/pi-ext#session-snap) | Session archive browsing and restoration. | The driver adapts its archive browser and reads the existing SQLite format. |

An isolated Pi 1.4.0 session loaded `@tintinweb/pi-subagents@0.26.2` alongside the foundation and successfully answered `ping` and `list`. It advertised protocol 2 with owned lifecycle, steering, stop settlement, settling and pending-notification features. The native acceptance fixture exercises model and tool selection, persistent sessions and exact checkout binding against a deterministic local provider.

The driver loads the pinned plugin’s child runner without registering its standalone launch tools, workflows, schedules or mention handlers. The preparation script supplies an exact tool list and private session directory to that runner. Each child executes in the path returned by the native worktree manager. The lead awaits the tool result, so Pi’s pending tool turn and the private attempt record both protect against compaction. The standalone plugin’s event bus is not needed for this path.

The archive picker previews finalized lead transcripts and reads Session Snap’s SQLite format through a read-only connection. The borrowed format and picker design are credited in [LICENSE.session-snap](LICENSE.session-snap). Finalization is invoked by the operator after an Octo-confirmed merge.

## Lead and delegated roles

Use the configured profile throughout an attempt. Work uses explicitly configured Bedrock Mantle endpoints; personal uses Pi's ChatGPT subscription provider. Resolve every role through Pi's registry before launch and retain the resolved model and reasoning in the attempt record. Missing models or authentication fail visibly; never fall back across profiles.

| Role | Default model and reasoning | Responsibility |
| --- | --- | --- |
| Lead | Sol, high | Interpret the request, decompose work, own integration and acceptance, and request authorized GitHub effects. |
| Worker | Sol, medium | Implement a bounded assignment in its own managed checkout. |
| Reviewer | Sol, medium | Inspect a specified source revision and return findings through read-only tools. |
| Explorer | Terra, low | Answer a focused repository question through read-only tools. |

Start with two concurrent children and one delegation level. Only the lead delegates. Role prompts describe the assignment; explicit tool sets, resource loading and execution guards enforce the boundary. Read-only roles receive no arbitrary shell, edit, write, or delegation tools. Writable roles need an enforced path and effect boundary before admission.

The selected plugin owns child execution through Pi's native sessions. Use Pi's [official SDK](https://github.com/earendil-works/pi/blob/v1.4.0/packages/coding-agent/docs/sdk.md) for the remaining host integration. Each child has a bounded brief containing its objective, source revision, owned paths, expected result, constraints and relevant evidence. Return findings, artifacts, verification and unresolved questions with attempt/session identifiers. Preserve detailed history in the native transcript rather than expanding every child transcript into the lead's context. Validate the effective role definition before launch, including project overrides and inherited-model fallback.

## Attempt and worktree binding

The controller persists an attempt ID before allocation or launch. Its runtime journal lives outside disposable worktrees and stores execution intent, plugin-owned run/session IDs, operation outcomes and receipts. Reuse the plugin's native session and result records; add only the task/allocation/effect bindings and reconciliation state they lack. It is not another editable task backlog. Store the canonical Beads reference and the accepted brief/control revision when task-bound; distinguish that binding from an explicitly requested local read-only analysis.

Every child needing a separate source snapshot uses the native [worktree manager](https://github.com/lanej/dotfiles/blob/master/docs/worktree-manager.md). A writable worker always gets a separate branch and checkout. Reuse an assigned lead checkout without acquiring another task lease. Persist allocation intent, then call `worktree create` with `--agent pi`, the real attempt ID as owner, a fresh branch and an explicit resolved base commit. Record the returned full allocation ID, owner, path, branch and lifecycle before starting Pi. A native session ID is recorded after session creation, not invented in advance.

Reuse the allocation and lost-response reconciliation behavior in the [existing worktree adapter](vendor/task-runtime/worktrees.ts) without making the standalone Pi path depend on the Paseo service. A timeout or hook failure can leave an allocation behind: inspect the manager by the recorded owner before retrying. An uncertain allocation or launch blocks a second attempt. Keep allocation, execution, input delivery and cleanup outcomes separate and use enums for their states.

The runtime tracks actual child activity, cancellation and settled results. Idle compaction remains blocked while a child is active or uncertain. Resuming the lead reconstructs these guards from durable attempts; it does not clear them because a timer, view or model context was replaced.

## Delivery sequence

| Increment | Concrete outcome | Gate before enabling |
| --- | --- | --- |
| Plugin delegation and allocation | A lead launches Explorer/Reviewer work on a specified revision through the selected plugin, manager-owned checkouts and persistent Pi child sessions, and receives structured results. | Demonstrate real execution, restricted tools, exact allocation binding, cancellation and lost-response recovery. No Beads claim, task completion or GitHub mutation. |
| Task-bound coding delegation | A lead admits a Worker under an accepted Beads brief, integrates its branch and obtains an independent review. | Prove the current per-task brief/control fence, one admitted writer, and recovery of uncertain effects under [#353](https://github.com/lanej/dotfiles/issues/353)/[#354](https://github.com/lanej/dotfiles/issues/354). |
| Octo review round trip | A Pi-owned delivery binding publishes a PR and routes native GitHub feedback back to the responsible task/attempt. | Add native Pi ownership/delivery support and prove that legacy Octo dispatch cannot launch a competing writer for that binding. |
| Merge cleanup and archive | A verified outcome and settled PR obligation lead to recoverable worktree removal and an archived runtime record. | Verify retained transcripts/refs/artifacts, quiescence and exact manager cleanup receipts under [#361](https://github.com/lanej/dotfiles/issues/361). |

The first increment covers read-only delegation and worktree integration. The task-execution gate still applies to coding delegation.

## Current integration gaps

The [native capability probe](acceptance/beads-control.ts) shows that the pinned Beads 1.3.4 CLI accepts an update from the same owner after the brief changes. The HTTP service on that version rejects stale revision, owner, and status on the guarded write itself. The probe confirms that edits from both the CLI and HTTP advance the revision and that stale closure attempts leave the bead open. Managed lead planning and completion use that HTTP guard. Writable child delegation still needs an end-to-end trial of guarded child admission, a distinct worktree and writer, and recovery before accepting or integrating its result.

The Pi lead enrolls the PR as a local Pi session target in Octo. Octo retains review and Ready notices in its pull inbox. The lead exposes `/octo-inbox`, explicit exact-head owner assessment, and a one-shot merge command tied to the current Ready notice for its own PR.

Register one responsible delivery binding containing the Beads task/revisions, lead attempt, native Pi session, repository/PR and source head. Persist incoming event identity and delivery intent before acknowledging Octo. Reconcile duplicate, edited, stale and uncertain inputs before delivering through the sole native session writer. GitHub feedback does not authorize broader work or merge. An offline lead leaves input pending; it does not authorize a replacement worker. Tasks without GitHub obligations continue with Octo stopped.

## Merge, removal and archival

For a task with a PR delivery obligation, confirm that PR's merge through Octo and verify the accepted task criteria. A merged PR alone is not task acceptance. Local-only work uses its accepted outcome without inventing a PR requirement.

1. Settle children, queued input and applicable external operations. Retain the checkout while any execution or effect is uncertain.
2. Write and verify a private recovery manifest with task/attempt lineage, source and merge refs, full worktree allocation identity, native session/transcript locators, retained artifacts and relevant Octo receipts. Verify durable Git reachability before removing files.
3. Preserve the native transcripts and stop the sessions that own the checkout. Finish only the exact owned manager allocation, then preview and apply safe pruning from outside that checkout. Preserve branches and inspect tracked, untracked and valuable ignored content.
4. Confirm the exact registration and directory were removed before marking the runtime attempt archived. If pruning is refused, show the concrete retention reason and keep cleanup pending.

The manager's normal minimum commit age is 24 hours. Immediate cleanup after merge needs the narrowly scoped `--accept-recent` policy; keep the other safety checks. Test squash/rebase integration through the manager's `--integrated` behavior, including a base that advances afterward. A merge receipt does not justify `--force`, discarding local work or bypassing manager protection.

Pi 1.4.0's public [session interface](https://github.com/earendil-works/pi/blob/v1.4.0/packages/coding-agent/docs/sessions.md) provides persistent JSONL, resume and export, without an archive operation. Finalization retains a private recovery manifest and copies native transcripts before pruning. The harness records the archived state after confirming removal and exposes the retained lead transcript in its session browser. This distinguishes recoverability from the user's visible completion order: merged PR, removed worktree, archived session.

## Acceptance path

The first increment must run through the real Pi extension entrypoint and actual worktree manager in an isolated repository. Verify selected role/model/reasoning, allowed tools, source revision, parent/child identity, returned findings and retained native history. Exercise cancellation, parent restart, lost allocation/launch responses and compaction while child work is active. Controlled provider tests establish wiring; authenticated model execution is required before calling the workflow usable with a configured provider.

The complete v1 additionally needs a real coding assignment, independent review, Octo publication, native GitHub review, correction on the same PR, authorized merge, safe cleanup and historical inspection. Interrupt it after an admitted effect and after pruning to prove recovery without a second writer or repeated external effect. These are the delivery criteria for [#358](https://github.com/lanej/dotfiles/issues/358), not capabilities established by this plan.
