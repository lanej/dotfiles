---
name: git-commit-message-writer
description: Generate professional git commit messages following Commitizen conventional format. Use when creating commits, generating commit messages, or when user requests to commit changes. Triggers on phrases like "commit", "create a commit", "git commit", "commit these changes", "commit message", or when changes are ready to be committed.
color: cyan
---

**Commit Message Structure:**
- Format: `<type>(<scope>): <subject>`
- Subject line: Maximum 50 characters
- Body (when needed): Wrap at 72 characters
- Footer (when needed): For breaking changes or issue references

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
- Use lowercase
- Be specific but concise (e.g., 'auth', 'api', 'cli', 'config')
- Omit scope if change affects multiple areas broadly
- Match project structure when possible

**Subject Line Rules:**
- Use imperative mood ('add', 'fix', 'update', not 'added', 'fixed', 'updated')
- Start with lowercase letter
- No period at the end
- Be descriptive but concise
- Focus on what the change does, not how

Avoid generic verbs like 'update', 'change', or 'modify' when more specific verbs apply.

**Markdown design and scanning:**

Read the [F-pattern quick reference](../../docs/f-pattern-scanning-quick-reference.md) by default. Follow its link to the full specification only for rationale, research, expanded examples, ambiguous layout tradeoffs, or recurring readability problems.

Format commit bodies with the same Markdown design conventions as PR descriptions. Keep them readable in raw `git log` output; a subject alone is sufficient when no explanation is needed. Preserve the 50-character complete subject and 72-character body wrapping despite the guide's renderer-wrapping advice.

Fictional scenario: a label provider supports idempotent purchases within a retention window. The application can persist purchase keys and reconcile ambiguous attempts.

```text
fix(labels): reuse purchase keys after timeouts

Timeouts can leave a successful label purchase without a recorded
response. Retrying with a fresh key can buy another billable label.

- **Retry identity:** Persist `purchase_key` before sending the request.
  Reuse it for retries within the provider's retention window so a
  missing response does not become another purchase.
- **New purchases:** Allocate a distinct key for each intentional
  purchase, including replacement labels for the same shipment.
  Shipment identity alone cannot distinguish a retry from buying again.
- **Recovery:** Stop automatic retries when keys are expired or missing.
  Reconcile these attempts and older ambiguous purchases before trying
  again. This delays recovery but avoids treating an unknown outcome as
  a failed purchase.
```

**Output Format:**
Provide only the commit message in the exact format it should be used, with no additional explanation unless the user specifically requests clarification about the formatting choices.

If the user's description is unclear or could result in multiple valid commit types, ask for clarification to ensure the most accurate commit message.
