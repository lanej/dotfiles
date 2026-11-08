# Pi governance steel thread (experimental)

This is an **opt-in vertical slice**, not a trusted autonomous government. It uses existing Pi, Treehouse, and Paseo. It does not modify their running processes, install a service, or grant any agent merge rights.

## Run

From the dotfiles checkout, launch three separate Pi processes (each in its own terminal or Paseo agent invocation):

```sh
PI_GOVERNANCE_ROLE=legislative pi --extension "$HOME/.files/pi/extensions/governance.mjs"
PI_GOVERNANCE_ROLE=judicial pi --extension "$HOME/.files/pi/extensions/governance.mjs"
PI_GOVERNANCE_ROLE=executive pi --extension "$HOME/.files/pi/extensions/governance.mjs"
```

In the legislative session, use `governance_propose` to describe a real change to this dotfiles/Pi system. In the judicial session, call `governance_status` to find its ID and `governance_review` with an evidence-based verdict. In the executive session, inspect the reviewed proposal, implement it in a Treehouse-isolated branch using existing tools, and open a **draft** GitHub PR for human review. No proposal should automatically merge or deploy.

Proposal snapshots are stored under `$XDG_STATE_HOME/pi-governance/proposals` (or `~/.local/state/pi-governance/proposals`). Use the same state directory across sessions on the **same host**. Different hosts do not share proposals without a deliberate synchronization mechanism.

The branch budgets in [budgets.json](../pi/governance/budgets.json) are **informational only** in this slice. No tokens or dollars are metered or stopped. The role is supplied by an environment variable and can be spoofed. Pi's tools and process have full host permissions; the proposal store is not tamper resistant. Do not treat this as an authorization boundary or deploy it unattended.

## Constitution and deliberate sessions

The governing principles are in [constitution.md](../pi/governance/constitution.md). Each role receives this text at Pi agent start. This is guidance, **not a security boundary**. Adoption of the constitution and protected changes requires explicit human authorization.

Keep evidence collection continuous but batch changes to reduce oscillation:

| Activity | V1 cadence | Meaning |
| --- | --- | --- |
| Executive task work | As requested | Ordinary implementation, fixes and rework continue without waiting for sessions |
| Judicial case review | As needed | A failing task can be reviewed immediately; recorded findings remain visible |
| Judicial session | Weekly | Summarize findings and identify recurring patterns; do not revise policy |
| Legislative session | Monthly | Consider accumulated judicial findings, select **at most one** ordinary systemic amendment for advancement |
| Post-adoption observation | At least 14 days | Compare outcomes against a pinned baseline before proposing further systemic promotion |

A **session** is a bounded decision window, not a permanently running Pi agent or mandatory new process. Snapshot the evidence and approved policy version at the start of each session. Capture a dated docket and decisions; carry unselected ideas into the next session without repeatedly respawning agents.

In V1 these are **manual scheduling conventions** from [budgets.json](../pi/governance/budgets.json), not implemented timers, immutable snapshots, or automatic gates. An approved PR does not deploy itself. Any emergency deviation requires explicit human authorization and documented evidence. Avoid running simultaneous amendments to the same subsystem during the observation period.

The weekly budget accounting period and the judicial session cadence are separate concepts even if both happen weekly.

## Acceptance

1. Three Pi sessions start using their respective role, each with the configured budget visible in `governance_status`.
2. Legislative proposal is persisted and visible to the other roles.
3. Judicial reviewer records evidence and one verdict.
4. Executive uses an existing Treehouse lease to build a candidate and creates a draft PR.
5. Human approval is required before any merge or promotion.
6. No role is granted the ability to change production configuration or budgets through the extension.

Run the deterministic adapter test with `node --test scripts/test-pi-governance.mjs`.

## Follow-ups before autonomy

Implement budget accounting with verified provider usage and real spend enforcement; isolate agent credentials and writable filesystems; move role authentication and immutable audit storage into a trusted controller; make reviews concurrency-safe and track exact proposal/commit hashes; link proposals to durable Paseo task evidence. Until then, this is a **manual proof of the legislative → judicial → executive handoff**, not the secured system.
