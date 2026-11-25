# Zellij session replacement is deferred

Routine [`project-update update --all`](../bin/project-update) defers Zellij builds and session replacement. Its JSON row reports `activation: "deferred"` and `activation_verified: false`, alongside the read-only session inventory. A successful routine update does not claim that deferred sessions use the selected installation. `project-update verify --all` still returns 3 when a running identity is unknown or differs from the installation.

`project-update build zellij` and `project-update update zellij` can install the curated runtime, helpers, plugins and configuration for future sessions. The normal [installer](../scripts/install-zellij) builds the unchanged curated base, `8fa36ac97bad1cf598bd38432b87301f81f1b962`, into an immutable runtime path. It does not select the unfinished native activation patch or stop running servers.

Session replacement requires explicit `--restart-zellij` intent with `update` or `restart`. The current [adapter](../scripts/zellij-activation.py) reports `session_replacement_supported: false` and rejects checkpoint, restart and restore requests with `zellij-session-restoration-not-supported` and exit 3 before native mutation. The driver rejects unsupported replacement before checkpointing dependent applications. Apps needing restoration through a deferred terminal also remain intact before checkpointing.

Native restoration work is retained for later development. Enabling it requires exact layout/focus restoration and authoritative per-client current and base input modes restored before input admission, plus successful real TTY, application and nested-session tests. Installation receipts and partial fixture success do not establish safe session replacement.
