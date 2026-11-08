# Conventional Code Comments

Draft 0.1

Help readers understand and safely change code with minimum unnecessary reading. A comment earns its place when it materially reduces the effort needed to understand intent, behavior, constraints, or structure.

## Format

Use the language's normal comment syntax. Special annotations borrow the shape of Conventional Commits, with types that describe the purpose of a comment rather than a change:

```text
<type>[(<scope>)]: <explanation>
```

Square brackets indicate an optional element; they are not literal characters. Ordinary explanations, useful phase labels, documentation comments, and docstrings remain valid without an annotation.

```python
# rationale(cache): Leave misses uncached so newly created accounts appear immediately.
# warning(retries): A timeout does not establish whether the payment was accepted.
# workaround(parser): Strip the BOM until upstream/repo#123 is fixed.
# todo(exports): Support cancellation.
# fixme(auth): Expired credentials currently bypass refresh.
```

## Specification

MUST and MUST NOT express requirements and prohibitions. SHOULD and SHOULD NOT express recommended and discouraged defaults; MAY expresses permission.

1. Comments SHOULD materially improve reader understanding. Authors SHOULD explain non-obvious domain reasoning, constraints, surprising behavior, algorithms, or hazards when clearer code alone cannot adequately carry that information. Explaining what code does MAY be useful; merely paraphrasing visible operations SHOULD be avoided.
2. Authors SHOULD consider clearer names, expressions, types, and structure before using a comment to compensate for avoidable complexity. Function extraction is an option, not a prerequisite for a useful comment; it SHOULD NOT obscure control flow or introduce unnecessary indirection merely to eliminate prose.
3. Comments MAY identify meaningful phases when that helps readers navigate a function. Obvious labels, decorative separators, and repetitive narration SHOULD be omitted. No comment density, function length, or per-function comment quota applies.
4. Comments MUST accurately describe their subject and distinguish current behavior, intended behavior, known defects, and assumptions when that distinction affects understanding. They MUST NOT present an intention or unverified assumption as an established guarantee.
5. Authors SHOULD update or remove comments affected by their code changes. Unrelated comments SHOULD be left alone. Historical accounts and commented-out obsolete code SHOULD give way to version history unless a specific present constraint makes them useful.
6. Caller-facing contracts SHOULD live in the language's documentation comments or docstrings. Local reasoning SHOULD be placed beside the relevant code; broad decisions SHOULD live in design documentation, with concise local context and a reference where needed. Tests protect behavior but do not automatically explain its rationale.
7. Special annotations SHOULD use `<type>[(<scope>)]: <explanation>` with a type from the table below. The type MUST be lowercase and immediately followed by the optional scope or colon. The colon MUST be followed by a space and a nonempty explanation. Commit-style `!` markers have no meaning in this convention.
8. An optional scope MUST name the affected concept or component. It SHOULD be short and familiar to the project. Use lowercase letters, digits, dots, underscores, slashes, or hyphens, starting with a letter or digit; omit parentheses when there is no useful scope.
9. An annotation's explanation MUST carry the useful information; a type or scope alone is insufficient. Ownership and references MAY appear in the explanation when they help a maintainer act. A reference SHOULD accompany enough local context to understand its relevance without opening it.
10. A `workaround` annotation SHOULD explain the constraint that requires the accommodation and the condition under which it can be removed. A `fixme` SHOULD identify the actual defect; a `todo` SHOULD identify concrete future work. Owners, issues, and deadlines are not universally required.
11. Existing language syntax, repository conventions, and tool directives MUST be respected. This convention MUST NOT be used to rewrite required directives, generated content, or native documentation syntax merely to make them resemble annotations.

## Annotation types

| Type | Use |
| --- | --- |
| `rationale` | Explain a decision or otherwise surprising behavior. |
| `warning` | Identify a hazard and its consequence for callers or maintainers. |
| `workaround` | Explain a temporary accommodation, its cause, and its removal condition. |
| `todo` | Identify intended future work. |
| `fixme` | Describe a known defect in current behavior. |

Use these annotations when their purpose or searchability helps. They are not a taxonomy for every comment. General context, algorithm explanations, performance descriptions, and references can use ordinary prose; a performance decision may warrant `rationale`, and a performance hazard may warrant `warning`.

## When to comment

Ask what a reader needs to understand or safely change the code. If a comment only translates nearby syntax into English, omit it. If a straightforward code improvement carries the information better, make that improvement. If useful information remains, place it where the reader needs it and use an annotation only when its purpose warrants one.

| Situation | Guidance |
| --- | --- |
| Intent or behavior is already clear | Leave it uncommented. |
| Domain meaning or an algorithm takes substantial inference | Explain the relevant model or behavior, even when that explains what the code does. |
| A decision prevents an apparently simpler implementation | Preserve the reason with `rationale`. |
| A safe change depends on a hidden constraint or hazard | Explain the condition and consequence, using `warning` when appropriate. |
| Distinct phases are hard to locate | Consider short phase labels or clearer structure; choose what improves reading. |
| A temporary accommodation or known defect remains | Describe it with `workaround` or `fixme`; distinguish future work with `todo`. |
| A caller needs a contract | Put it in documentation comments, docstrings, or types; keep local implementation reasoning beside the code. |
| A decision spans components | Keep the full decision in design documentation and leave useful local context with a reference. |

## Examples

### Explanation versus narration

The first comment repeats the assignment; the second explains the business meaning of the calculation.

```python
# Redundant: Set the cutoff to the current time minus the retention period.
cutoff = now - retention

# Shipments created before this cutoff are outside the customer's retention window.
cutoff = now - retention
```

An algorithm explanation can earn its place even when it describes what happens:

```python
# Merge overlapping windows so each instant contributes to the total only once.
windows = merge_overlaps(windows)
```

### Navigation versus decoration

A heading like `# Set variables` before straightforward assignments adds little. A short phase label can help a reader locate a meaningful boundary in a longer operation:

```python
# Resolve eligibility before reserving any inventory.
eligible = resolve_eligibility(order, policy)
if not eligible:
    return Rejected()

# Reserve inventory before collecting payment.
reservation = reserve_inventory(order)
```

Keep a label only if it helps readers follow the operation; do not require headings before each step or extract functions solely to remove headings.

### Constraints versus unsupported claims

```python
# Misleading: Retrying is safe.
# warning(payments): After a timeout, reconcile using the idempotency key before retrying.
```

The warning identifies a consequence that must be handled rather than claiming a guarantee the local code cannot establish.

### Workarounds versus unexplained instructions

```python
# Unhelpful: Remove this later.
# workaround(parser): Strip the BOM until the parser accepts BOM-prefixed input; see upstream/repo#123.
payload = payload.removeprefix("\ufeff")
```

### Caller contracts versus implementation reasoning

```python
def first_match(rules, shipment):
    """Return the first matching rule, or None when no rule matches."""
    # rationale(rules): Configuration order expresses customer priority; do not sort by specificity.
    for rule in rules:
        if rule.matches(shipment):
            return rule
    return None
```

The docstring supplies the caller's contract; the local annotation explains a decision a maintainer might otherwise reverse. A design document can hold the broader policy without making the local reader reconstruct this constraint from a link alone.

## Adoption and editor support

The [code-comments skill](../ai/skills/code-comments/SKILL.md) provides compact guidance for routine comment-writing and review tasks. Load this full specification when changing the convention, resolving details outside that guide, or needing extended examples or editor-compatibility guidance. The skill's reference links back here to the canonical standard.

Use the new syntax for new or meaningfully revised annotations. Existing uppercase annotations and legacy tags need no bulk migration. There is no snippet requirement or lint enforcement.

Neovim retains the existing `Comment.nvim` editing commands and `todo-comments.nvim` highlighting and search. New scoped and unscoped annotations are recognized alongside plugin default tags and legacy `WHY`, `SEE`, `REF`, `WTF`, `DAFUQ`, and `GAH`. `<leader>an` opens annotations in FzfLua; `:TodoQuickFix` populates quickfix, where `]q` and `[q` navigate matches. Highlighting recognizes comments through the existing syntax integration, and quickfix filters search candidates through the annotation matcher. The picker uses permissive text search to preserve legacy recognition; it can include malformed annotations and annotation-shaped text in examples or strings. Search is not syntax validation.
