# Looker CI + Deploy Webhook: First-Time Setup Checklist

For a Looker instance/repo pair that has never had the official "Looker Continuous
Integration" GitHub App or a native deploy webhook configured. Every identifier below
(`<instance>`, `<project>`, `<repo>`) is a placeholder — substitute the real values, and don't
assume this instance uses the same project/connection names as any other instance.

## Prerequisites

- A LookML project git-connected to the target GitHub repo (Develop → Manage LookML Projects
  → configure git for the project, or Admin's project git-connection screen).
- A Looker user with the Admin permission set (covers `manage_ci`, `develop`, `deploy` — the
  three permissions this checklist actually needs; a custom role could grant just those three
  instead of full Admin).

## Step 1 — Install the GitHub App

1. Admin → Platform → Continuous Integration (naming may vary by Looker version) → enable the
   instance-wide CI feature if not already on.
2. Connect to GitHub / install the "Looker Continuous Integration" GitHub App, scoped to the
   org containing the target repo.
3. On the same admin page, confirm the target repo shows status "Installed". This only grants
   Looker permission to receive webhooks for repos in that org — it does **not** link any
   specific Looker project to any specific repo. That mapping is the project's own git
   connection (prerequisite above), not this page.

## Step 2 — Create a CI Suite (IDE-only, no API)

1. Develop → open the target LookML project (or navigate directly to `<instance>/projects` →
   the project name).
2. Continuous Integration icon (left nav rail inside the project) → Suites tab → Create suite.
3. Enable **"Trigger on pull requests from Looker"** — optionally restrict to a target branch
   (usually the production branch).
4. Enable at least LookML Validator. Add Content/SQL/Assert Validator as appropriate — disable
   Assert Validator up front if the project has zero `test:` blocks (`grep -rn "^test:" .`
   returns nothing); it errors rather than skipping cleanly on an empty suite, which otherwise
   reads as a false regression on every PR.
5. Save.

No REST/API endpoint exists to create or edit a suite as of this writing — this step requires a
human with IDE access (`develop` + `manage_ci`).

## Step 3 — Verify the trigger actually fires

- Open a PR touching a path the project's git connection watches.
- If no check appears within a minute or two: confirm the toggle from step 2.3 is genuinely on,
  and that the PR was opened or synchronized *after* the suite was configured — webhooks don't
  fire retroactively on an already-open PR. Push a new commit, or close and reopen the PR, to
  force a fresh trigger event.

## Step 4 — One-time production deploy (manual, blocking)

Before any deploy webhook will function: Looker IDE → Git Actions panel on the project's
production branch → **Deploy to Production**, once. Looker's own webhook-secret config screen
states this prerequisite directly. Skipping it can make the deploy webhook endpoint hang or
error even on a trivial `ping` delivery.

## Step 5 — Configure the deploy webhook

1. On the project's git configuration screen, find **Webhook Deploy Secret** → generate or set
   a secret, then save. Looker shows the secret once — copy it immediately; refreshing loses it.
2. On the GitHub repo: Settings → Webhooks → Add webhook.
   - **Payload URL**: use the project-specific deploy webhook URL as shown on Looker's git
     configuration screen. Do not hand-construct a generic
     `<instance>/webhooks/projects/<project>/deploy` URL from documentation — the real URL may
     include a unique per-project token suffix (the CI webhook URL does, in the pattern
     `.../ci/<token>`; the deploy webhook likely follows the same convention).
   - **Content type**: `application/x-www-form-urlencoded` (GitHub's default) — not
     `application/json`.
   - **Secret**: the value from step 5.1.
   - **Which events**: "Just the push event" — deploy triggers on push to the production
     branch (i.e. after merge), not on `pull_request`.
3. Send a test `ping` delivery. Expect GitHub to report it as failed/timed-out even when it
   actually succeeds — see the main SKILL.md's "Deploy webhook" section. Confirm real success
   via Looker's Deployment Manager / deploy history, not GitHub's delivery log.

## Step 6 — Merge-strategy hygiene

Looker's production-branch tracking assumes merge commits. In the GitHub repo's merge-button
settings, disable "Allow squash merging" and "Allow rebase merging", leaving only "Allow merge
commits" — squash/rebase can desync Looker's git-state tracking from GitHub's actual commit
history.
