---
name: git-commit-message-writer
description: Generate professional git commit messages following Commitizen conventional format. Use when creating commits, generating commit messages, or when user requests to commit changes. Triggers on phrases like "commit", "create a commit", "git commit", "commit these changes", "commit message", or when changes are ready to be committed.
color: cyan
---

Use `<type>(<scope>): <subject>`, omitting scope when unnecessary.
Limit the complete subject to 50 characters; wrap body text at 72.
Add a body when explanation helps, and footers for breaking changes or issue references.

**Valid Types:**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system or dependency changes
- `ci`: CI/CD configuration changes
- `chore`: Maintenance tasks

**Scope Guidelines:**
- Use a concise, lowercase project component, such as `auth` or `cli`.
- Omit scope when no single component fits.

**Subject Line Rules:**
- Describe the outcome in imperative mood, starting lowercase, without a trailing period.
- Prefer specific verbs over 'update', 'change', or 'modify'.

**Markdown design and scanning:**

Apply the [F-pattern quick reference](../../docs/f-pattern-scanning-quick-reference.md).

Use the same Markdown design as PRs, readable in raw `git log` output.
The 72-character body limit overrides the guide's renderer-wrapping advice.

Fictional example: the provider supports idempotent purchases within a retention window.

```text
fix(labels): reuse purchase keys after timeouts

Timeouts can leave a successful label purchase without a recorded
response. Retrying with a fresh key can buy another billable label.

- **Retry identity:** Persist `purchase_key` before sending the request.
  Reuse it for retries within the provider's retention window.
- **New purchases:** Allocate a distinct key for each intentional
  purchase, including replacement labels for the same shipment.
- **Recovery:** Stop automatic retries when keys are expired or missing.
  Reconcile these attempts and older ambiguous purchases before trying
  again. Recovery waits until the purchase outcome is known.
```

**Output Format:**
Return only the commit message unless the user requests an explanation.

Ask for clarification when ambiguity prevents an accurate message.
