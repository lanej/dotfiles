#!/usr/bin/env python3
"""Native Pi submission acceptance; invoked by local-run.ts, never a live service."""

from __future__ import annotations

import json
import signal
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import FrameType

from local_fixture import Fixture, Report, RunOptions, make_fixture
from local_provider import ADMITTED_MODEL, Provider
from local_scenarios import SCENARIOS, launch
from zellij_terminal import Terminal


def run_cases(fixture: Fixture, terminal: Terminal, report: Report) -> None:
    terminal.until("fixture shell", lambda: b"local-run-ready> " in terminal.output)
    shell = terminal.terminals()
    assert len(shell) == 1, shell
    launcher = shell[0]["id"]
    panes = terminal.pane_listing()
    tab_id = next(p["tab_id"] for p in panes if p["id"] == launcher)
    selected = fixture.options.scenario
    for scenario in SCENARIOS if selected is None else (selected,):
        case = launch(fixture, terminal, launcher, tab_id, scenario)
        snapshot = SCENARIOS[scenario](case, report)
        report["cases"].append({"scenario": scenario.value, "bead": case.bead, "evidence": snapshot})
    assert not Provider.alternate_requests, "Managed Pi sent data to an alternate provider"
    assert all(request["model"] == ADMITTED_MODEL.id for request in Provider.requests)
    fixture.check_sentinels()


def run_terminal(fixture: Fixture) -> None:
    report: Report = {
        "runtime": "real Pi TUI, native worktree manager, Beads HTTP and Dolt",
        "submission": "task_submit_result and native /task-submit; deterministic loopback provider, no external inference",
        "paseo": "unreachable endpoint and failing executable sentinel",
        "session": fixture.name,
        "cases": [],
        "artifacts": str(fixture.artifacts),
        "outcome": "failed",
        "cleanup": "pending",
    }
    report_file = fixture.artifacts / "report.json"
    terminal = fixture.start_terminal()
    try:
        run_cases(fixture, terminal, report)
        report["outcome"] = "passed"
    finally:
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        (fixture.artifacts / "provider-requests.json").write_text(json.dumps(Provider.requests, indent=2) + "\n")
        (fixture.artifacts / "terminal.ansi").write_bytes(terminal.output)
        try:
            subprocess.run([fixture.binary, "--session=" + fixture.name, "kill-session"],
                           env=fixture.env, capture_output=True, timeout=10)
        finally:
            terminal.close()
        fixture.prune_worktrees()
        report["cleanup"] = "confirmed"
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def terminate(_signal: int, _frame: FrameType | None) -> None:
    raise SystemExit("Native acceptance interrupted")


def main() -> None:
    signal.signal(signal.SIGTERM, terminate)
    options = RunOptions.read(Path(sys.argv[1]))
    with tempfile.TemporaryDirectory(prefix="pi-zj-", dir="/tmp") as runtime:
        fixture = make_fixture(options, Path(runtime))
        with ThreadingHTTPServer(("127.0.0.1", 0), Provider) as provider:
            provider.daemon_threads = True
            fixture.paths.configure_pi(options, provider.server_port)
            fixture.initialize_repository()
            thread = threading.Thread(target=provider.serve_forever, daemon=True)
            thread.start()
            try:
                run_terminal(fixture)
            finally:
                provider.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    main()
