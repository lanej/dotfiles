# Legacy authority selection

For an older directory-linked installation, read `authority` from the consuming repository's installed `.source-code.json`, then load only the matching [owned](authority-owned.md), [shared](authority-shared.md), or [upstream](authority-upstream.md) policy. Missing or invalid authority preserves established conventions and gates; it does not permit applying the catalog or expanding the task's authority. Report the missing selection when it affects the work. Setup or upgrade replaces this selector with the selected policy.
