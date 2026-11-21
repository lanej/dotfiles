# Go rollout: ratchet

Preserve the adopted baseline. New files have no allowance; new findings in old files fail, including untouched consumers affected by changed declarations. Do not use changed-line filters or enlarge the baseline. After repairs, run `bash scripts/check-go.sh ratchet` and commit the reduction with the fix. Normal lint requires resolved allowances to be removed.

Baseline initialization belongs only to authorized adoption against committed existing Go source. It rejects dirty, untracked, or ignored Go source, compilation errors, and an existing baseline. Never reinitialize it for ordinary feature work. Use explicit paths with `fmt`; ratchets reject unscoped formatting. A signature budget is gradual adoption, not proof that all legacy code complies. Read [the adoption mechanics](correctness.md) when installing or changing the profile.
