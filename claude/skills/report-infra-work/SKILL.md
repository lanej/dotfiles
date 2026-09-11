---
name: report-infra-work
description: Report an infrastructure change need in easypost-enterprise-platform-infra or enterprise-platform-bootstrap to the infra-dispatcher session instead of working around it inline or building/opening a PR yourself. Use when you hit a need for a new GCP resource, IAM grant, DNS record, GitHub org/repo setting, or Jira config change in either of those two repos, and building it isn't part of your current task.
---

# Report an Infra Change Need to the Dispatcher

If you hit a need for a change in `easypost-enterprise-platform-infra` or `enterprise-platform-bootstrap` — a new GCP resource, an IAM grant, a DNS record, a GitHub org/repo setting, a Jira config change — and building or proposing it isn't your job right now, don't work around it silently and don't drop it. Report it to the `infra-dispatcher` session.

## When to use this

- You need something to exist or change in either of those two repos (e.g. a bucket, a service account grant, a DNS record, a label policy) to unblock your actual task.
- Building it yourself is out of scope for what you're currently doing, or you don't have (and shouldn't need) direct write access to production GCP/GitHub-org/Jira infrastructure.

## When NOT to use this

- The repo isn't one of the two named above — the dispatcher only acts on that exact allowlist and will reject anything else.
- You're already the one building it as your actual task — just do it directly (or if you're unsure of the repo's conventions, read that repo's own README/CLAUDE.md first).
- It requires an addition to `policy-exceptions.yaml` (a security-relaxation decision) or touches Rego policy source, CODEOWNERS, branch protection, or Atlantis's own server config — those always require Josh's own direct decision; the dispatcher will refuse to act on them autonomously too, so raise those with Josh directly instead of routing them through this path.
- The change is large, ambiguous, or needs product/design judgment beyond "here's the resource/setting I need" — this path has no design-review step; it's for scoped, mechanically-verifiable infra changes only.

## How to report

Call `SendMessage` addressed to the session named `infra-dispatcher`:

```
SendMessage({
  to: "infra-dispatcher",
  summary: "<repo>: <one-line title>",
  message: "Infra change request.\n\nRepo: <easypost-enterprise-platform-infra|enterprise-platform-bootstrap>\nTarget: <root/dir under live/, or the relevant path>\n\nDesired change: <what should exist or change, concretely>\n\nWhy: <context/motivation — what this unblocks for you>"
})
```

Be concrete about the desired end state (exact resource type, name, settings) — this becomes the committed request record the change is built against, so a vague report produces a vague result or an unnecessary back-and-forth.

## After reporting

Don't block your own task waiting for a reply. The dispatcher works asynchronously: it builds the change, has a separate reviewer independently verify it, and — for `easypost-enterprise-platform-infra` only — that reviewer can trigger the actual Atlantis apply itself once its gates pass. For `enterprise-platform-bootstrap`, no dispatched agent can ever complete an apply (branch protection blocks agent self-approval, and a separate protected-environment gate requires Josh's own click) — so a bootstrap request always ends with Josh needing to take two manual actions himself, not a clean auto-applied outcome. Either way, you'll get a `SendMessage` reply stating the outcome (applied, PR open, or escalated) whenever it's done — often well after you've moved on. If the `infra-dispatcher` session isn't currently running, the message simply won't be delivered; there's no queue. That's a known, accepted limitation — retry later or mention it to Josh directly if it's urgent.
