# Legacy Go rollout selection

For an older directory-linked installation, read the consuming repository's `.go-quality.json`. Load [strict enforcement](rollout-strict.md) for `rollout = "strict"`, or [ratchet enforcement](rollout-ratchet.md) for `rollout = "ratchet"`. If settings are missing, retain the installed runner's existing behavior; report invalid settings without changing enforcement. Neither case permits a new baseline, weaker gates, or expanded task authority. Setup or upgrade replaces this selector with the selected rollout.
