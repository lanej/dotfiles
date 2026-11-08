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
