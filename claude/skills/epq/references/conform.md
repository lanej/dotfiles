# EPQ Conform Extraction Pattern

Conform batch jobs take hours. They cannot run at render time. Use the three-phase
extract script pattern: cache hit → job in flight → job succeeded/submit new.

**The QMD never calls Conform.** It reads `cache.read_cache()` with a long TTL.

## QMD Data-Load Cell (pending-safe)

```python
try:
    cached = cache.read_cache("name", ttl_hours=168)
except cache.StaleCache:
    cached = None

if cached is None:
    if cache.is_conform_pending("name"):
        print("  conform: name job in progress — using placeholder")
    data["name"] = None   # figure modules handle None → placeholder
else:
    data["name"] = cached["records"]
```

## Figure Module (handles None)

```python
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class Data:
    records: Optional[list[dict[str, Any]]]  # None while Conform job is running

def render(data: Data) -> None:
    import matplotlib.pyplot as plt
    import pandas as pd
    style.apply_style()
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    if data.records is None:
        style.render_pending_placeholder(ax, "Conform extraction in progress")
        return
    df = pd.DataFrame(data.records)
    # ... viz ...
    plt.tight_layout()
```

`style.render_pending_placeholder(ax, message)` — draws a `LIGHT_BG`-filled panel
with centered `SLATE` text, no ticks, no spines.

## Extract Script

Copy from `scaffold/scripts/data/_extract_conform_example.py`. It manages three phases:

- **Phase 1**: cache fresh → exit 0
- **Phase 2**: job running → print status, exit 0 (non-blocking)
- **Phase 3a**: job SUCCEEDED → download, `write_cache(ttl_hours=168)`, clear state
- **Phase 3b**: no job → `conform batch submit`, write `data/conform/<name>_job.json`

Write TTL at write time for observability (`epq check-cache` shows intended TTL):
```python
cache.write_cache(_NAME, records, ttl_hours=168)
```

## Key Details

`cache.is_conform_pending(name, *, project_root=None)` — returns `True` if
`data/conform/<name>_job.json` exists (job submitted, not yet downloaded).

**Job state file** (`data/conform/<name>_job.json`) — gitignored, ephemeral.
Cleared after successful download.

**Input hash invalidation**: schema + source file hashes are stored in job state.
If either changes, old job is discarded and a new submission is triggered.

**Schemas**: `schemas/<name>.json` — add alongside the extract script.

## Polling Recipe (add to project justfile)

```just
wait-conform name:
    #!/usr/bin/env bash
    while true; do
        uv run python scripts/data/extract_{{name}}.py
        python -c "from epq import cache; cache.read_cache('{{name}}', ttl_hours=168)" 2>/dev/null && break
        echo "Still running, sleeping 5m..."; sleep 300
    done
```
