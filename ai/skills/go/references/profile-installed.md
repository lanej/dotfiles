# go: installed check profile

Run `python3 scripts/check-source-code.py go` for the installed lifecycle gate. The selected stage entrypoint controls required checks; standalone modes describe available tools and do not add another stage’s gates. Preserve stronger repository requirements. Missing tools and failed checks require resolution or a reported limit, never a silent skip.

Read `rollout` from the installed `.go-quality.json`, then load only [strict enforcement](rollout-strict.md) for `strict` or [ratcheted enforcement](rollout-ratchet.md) for `ratchet`. Do not infer rollout from project age or lifecycle stage. Resolve missing or unknown rollout before changing enforcement or claiming a baseline allowance.

The runner supports `lint`, `fmt` with explicit paths, `fix` for scoped cuddling repairs, `test`, and `vuln`. Inspect source-writing changes. Pinned tools are cached outside the project, and the linter release checksum is verified. Initial tool setup and vulnerability analysis need network access. Keep tool dependencies out of the application’s `go.mod`.

The supplied runner covers one root module on its host platform. Adapt checks to actual nested modules, workspaces, build tags, platform-specific code, and native dependencies. Read [the correctness guide](correctness.md) when adopting, tuning, or explaining the profile.
