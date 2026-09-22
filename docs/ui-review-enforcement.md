# Detection and enforcement

Viewrule owns the checker and its
[detection and enforcement manual](https://github.com/lanej/viewrule/blob/main/docs/ui-review-enforcement.md).
That document maps each DR ID to scoped measurements and their limitations, and
ships inside the package alongside the canonical policy.

Dotfiles owns the version pin, preferences, and CLI wrapper; see
[Viewrule integration](ui-review.md). Existing `.ui-review` configuration remains
compatible. Stop enforcement is retired; use explicit verification, optional Git
gates, and application CI for delivery.
