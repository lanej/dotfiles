# Worktree runtime verification

### Dependencies in a fresh worktree

A fresh worktree may resolve missing workspace dependencies from a parent checkout. Use the repository’s selected package manager and lockfile in the target worktree before trusting tests or dev-server output. Verify which dependency paths are actually resolved.
