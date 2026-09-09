# /handoff vs /delegate — routing discrimination eval

A/B test of the command rewrite (commit `d1206a2`). Same 19 scenarios, two arms:
**OLD** = docs at `d1206a2~1`, **NEW** = docs at `d1206a2`. Judge: `claude -p`,
haiku-4.5, one scenario per call, forced single-token answer.

## Result: no measurable routing improvement

| arm | mean | sd | per-trial (n=6) |
|---|---|---|---|
| OLD | 17.17/19 (90.4%) | 0.98 | 17, 17, 17, 16, 17, 19 |
| NEW | 17.50/19 (92.1%) | 1.22 | 19, 18, 18, 18, 16, 16 |

Paired diff +0.33 scenarios/trial. **Exact paired permutation p = 0.42 — not significant.**

The OLD docs already routed correctly ~90% of the time. The rewrite does not
measurably change that. Anyone claiming the rewrite "improved routing" is
overreading noise.

### One durable difference
`d4` (large task, fresh context) — OLD majority `SELF`, NEW majority `DELEGATE`.
Explainable: NEW states that context health, not task size, is the trigger.
Single scenario; not sufficient on its own.

### Known weaknesses of this eval
- **Ceiling effect.** A 90% baseline leaves ~2 scenarios of headroom, so the set
  cannot resolve small effects. Harder scenarios are needed for a real test.
- **Author bias.** The same person wrote the NEW docs and these scenarios.
- **`d9` ground truth is arguable.** Labeled DELEGATE; "find where the config
  lives" is defensibly a needle query (SELF). Both arms answer SELF.
- Judged on haiku-4.5 only. Behavior on the model that actually runs these
  commands is untested.

## What the rewrite did verifiably deliver
- `/delegate` 409 → 56 lines (86% less text) at no measured accuracy cost
- Corrected stale facts: tool is `Agent` not `Task`; no `thoroughness` parameter
- `/handoff` jq digest verified on a live 335KB transcript → 10KB (97% reduction),
  session goal preserved

## Reproduce
```bash
./run.sh <old|new> <trial-n> <outdir>   # keep concurrency low; see note below
```
`run.sh` redirects stdin from `/dev/null` — without it, parallel `claude`
processes race on the shared xargs pipe and return empty (`PARSE_FAIL`).
Running >~40 concurrent judge processes also triggers failures; `xargs -P 4`
with arms run sequentially is reliable. **Discard any trial with a non-zero
PARSE_FAIL count rather than scoring it** — an early version of this eval
scored those as routing misses and reported a fictitious 65% → 82% gain.
