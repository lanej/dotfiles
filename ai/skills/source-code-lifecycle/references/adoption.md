# Legacy adoption selection

For an older directory-linked installation, read `adoption` from the consuming repository's installed `.source-code.json`, then load only the matching [hold](adoption-hold.md), [new](adoption-new.md), or [backfill](adoption-backfill.md) policy. Missing or invalid adoption preserves established conventions and gates; it does not authorize applying the catalog or migrating existing code. Report the missing selection when it affects the work. Setup or upgrade replaces this selector with the selected policy.
