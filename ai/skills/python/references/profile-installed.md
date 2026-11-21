# Verification

Run `python3 scripts/check-source-code.py python` for the installed lifecycle gate. The selected stage entrypoint controls required checks; standalone modes describe available tools and do not add another stage’s gates. Preserve stronger repository requirements. Missing tools and failed checks require resolution or a reported limit, never a silent skip.

Read [the strict profile](strict-profile.md) when provisioning tools or changing profile configuration. It provides pinned Ruff, strict ty and annotation checks, project tests, and dependency auditing with lifecycle-selected commands. Enforcement is strict; there is no diagnostic baseline. Preserve root configuration and existing repository gates.
