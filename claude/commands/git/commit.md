---
description: Create a focused git commit from the staged changes and user context
argument-hint: [optional context or focus]
tags:
  - git
  - commit
  - workflow
---

Create a commit for the requested work. Optional context: $ARGUMENTS

1. Inspect `git status`, the staged diff, and recent commit conventions. If staging is
   needed, stage only files belonging to the authorized task. Ask only when ownership
   or intended scope is unclear; leave unrelated work alone.
2. Write the message directly from the staged change. Follow the repository's conventions;
   otherwise use `<type>(<scope>): <subject>`, omitting unnecessary scope. Keep the subject
   within 50 characters and use an optional body to explain why.
3. Commit only the reviewed staged snapshot. Verify the complete staged diff contains
   only authorized changes; if unrelated staged work is present, resolve ownership and
   scope before proceeding. Do not use a path-based commit to bypass the index: that can
   include unstaged hunks from partially staged files. Use a message file for a multiline body.
4. Verify the resulting commit and report its ID and any remaining task changes.
