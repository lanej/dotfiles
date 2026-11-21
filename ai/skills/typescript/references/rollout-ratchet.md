# Enforcement: ratchet

Preserve the adopted diagnostic baseline. New diagnostics fail even in unchanged consumers. Original compilation, parser/configuration failures, missing modules, suppression-policy violations, original project checks, tests, audits, and Biome findings cannot be baselined when their checks run at the selected stage. Never add an allowance to unblock a feature or filter to changed lines.

After repairing old findings, run `node scripts/check-typescript.mjs ratchet` and commit the reduced baseline with the fix; it can only shrink the budget. One-time baseline creation requires committed source and an authorized adoption task. A signature budget can reuse indistinguishable findings and formatting is file-granular; do not claim individual defect identity or full legacy compliance. Read [the adoption mechanics](correctness.md) when installing or changing the profile.
