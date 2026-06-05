# DORA Identity and Team Attribution Reference

## unified_identity

`DORA.unified_identity` is a **view** — it returns one row per person filtered to `is_current_assignment = TRUE`. The underlying table is `DORA.unified_identity_history` (full temporal record, one row per person per assignment period).

**Do not** add `WHERE is_current_assignment = TRUE` to a join against `unified_identity` — the column exists only in `unified_identity_history`; the view has already applied the filter. Adding the guard will produce an error or zero rows.

Refresh:
```bash
just download-unified-identity && just upload-unified-identity
# upload-unified-identity automatically runs verify-attribution
```

## Primary Join Key: email_prefix

```sql
ON ui.email_prefix = LOWER(REGEXP_EXTRACT(email_column, r'^[^@+]+'))
```

The `+` in `[^@+]+` strips email tags: `user+tag@example.com` → `user`. Using `r'^[^@]+'` silently drops tagged addresses. This pattern is critical for ADO joins (EPS engineers often use tagged addresses).

`email_prefix` is a pre-computed column in `unified_identity` — no REGEXP needed on the identity side.

## Department Taxonomy (Critical)

`DORA.unified_identity` uses **resolved display names**, not HR cost-center codes.

| Wrong (HR codes) | Correct (display names) |
|-----------------|------------------------|
| `department LIKE 'Engineering%'` | `ui.team IN ('Carriers', 'Applications', ...)` |
| `'200 - Infra Eng'` | `'Platform'` |
| `'236 - Enterprise'` | `'Enterprise'` |

Canonical team display names (as of 2026): `Carriers`, `Applications`, `Foundations`, `Platform`, `Security`, `Enterprise`, `USPS`, `WeSupply`

To exclude org-container rows (director spans, not leaf teams):
```sql
WHERE ui.team NOT LIKE '260 -%'
```

Use `COALESCE(ui.team_display_name, ui.team)` for the final display value — `team_display_name` is pre-resolved.

## Anti-Patterns

1. **`is_current_assignment` guard on `unified_identity`** — column does not exist on the view; only on `unified_identity_history`. The 13 guards that existed before commit 28142a9 were all removed.

2. **`department LIKE 'Engineering%'`** — returns 0 rows in DORA.unified_identity. Always filter on `team` (display name) or use `team NOT LIKE '260 -%'` to include all engineering leaf teams.

3. **Querying `unified_identity_history` for current state** — always use the `unified_identity` view for current-assignment queries; only go to `unified_identity_history` when you need point-in-time or historical data.

## PHAB_USERNAME_OVERRIDES

Location: `scripts/build-team-members.py`, dict `PHAB_USERNAME_OVERRIDES`

When Phabricator `real_name` doesn't match the XLSX preferred name (display name mismatch or surname omission), add an entry:

```python
PHAB_USERNAME_OVERRIDES: dict[str, str] = {
    "XLSX Full Name": "phab_username",
    # Examples:
    "Christopher Duncan": "cduncan",   # Phab says "Chris Duncan"
    "Steven Alfonso Hernandez": "salfonso",  # Phab omits surname
}
```

Verify the correct username: `phab user search --output jsonl | grep -i '<name>'`

After editing, re-run `just download-unified-identity && just upload-unified-identity`.

## team_membership_changelog

Point-in-time team membership events (joins and leaves), keyed by Phabricator username. Use when you need "which team was this person on when they shipped this change" rather than their current team.

```bash
just download-team-membership-changelog && just upload-team-membership-changelog
```

`team_name` = canonical DORA team name (NULL for non-DORA Phab projects).

## verify-attribution

Runs a suite of sanity checks: unresolved team codes, zero-row roster checks, IC attribution coverage. Exits 1 on hard failures.

Run after any identity or team data refresh:
```bash
just verify-attribution
```

Also auto-runs after `just upload-unified-identity`.

## Team Registry Refresh

Edit team definitions in `scripts/download-team-registry.py` (hardcoded `TEAMS`, `ALIASES`, `INCIDENT_TEAM_MAPPING`, `PAGERDUTY_TEAM_MAPPING` lists). Then:

```bash
just download-team-registry && just upload-teams && just upload-team-code-aliases
# Also update mapping tables if changed:
just download-team-registry && just upload-incident-team-mapping && just upload-pagerduty-team-mapping
```

Monitoring for unmapped team codes:
```sql
SELECT DISTINCT team_name FROM DORA.team_members
WHERE team_name NOT IN (SELECT code FROM DORA.team_code_aliases)
```
Should return 0 rows after refresh.
