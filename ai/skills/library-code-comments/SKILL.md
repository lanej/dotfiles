---
name: library-code-comments
description: Use when writing or reviewing documentation comments for a library public API, or when project instructions select the library comment policy for a directory.
---

# Library code comments

Read the installed [code comment guidance](../code-comments/SKILL.md) for the configured lifecycle depth, then apply the library caller perspective below. The shared comment format does not add another stage’s documentation obligations. Read the [canonical standard](../code-comments/references/standard.md#library-caller-perspective) only when resolving a convention detail or changing the policy.

Use this policy for library public APIs within the scope selected by project instructions or the current task. For mixed repositories, honor directory-specific scope; installation alone does not classify every directory as a library. Preserve repository and language documentation requirements.

Review from the caller's perspective: can someone use the API and understand its consequential behavior without opening the implementation? Identify missing information and its effect on usage, then propose a concrete improvement. Clear names and types can carry obvious details; do not add comments that merely repeat them. Keep implementation reasoning local and leave unrelated comments alone.
