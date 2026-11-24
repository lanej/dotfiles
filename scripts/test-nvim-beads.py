#!/usr/bin/env python3
"""Run the Beads editor journey against a controlled, disposable HTTP boundary."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import argparse
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "11111111-1111-4111-8111-111111111111"


def task(identity, title, **fields):
    return dict(id=identity, title=title, status="open", priority=2,
                created_at="2026-11-23T00:00:00Z", updated_at="2026-11-23T00:00:00Z",
                revision="1", description="", acceptance_criteria="", dependency_count=0, dependent_count=0, comment_count=0, **fields)


class Boundary:
    def __init__(self):
        self.tasks = {"trial-root": task("trial-root", "Parent"),
                      "trial-child": task("trial-child", "Child"),
                      "trial-blocker": task("trial-blocker", "Blocker"),
                      "trial-long": task("trial-long", "A task title that expands with the pane")}
        self.tasks["trial-child"]["metadata"] = {"pi.attempt": "owner-attempt", "arbitrary": {"keep": [1, True]}}
        self.tasks["trial-child"]["assignee"] = "pi:owner-attempt"
        self.tasks["trial-child"]["status"] = "in_progress"
        self.edges = [dict(issue_id="trial-child", depends_on_id="trial-root", type="parent-child", created_at="2026-11-23T00:00:00Z"),
                      dict(issue_id="trial-child", depends_on_id="trial-blocker", type="blocks", created_at="2026-11-23T00:00:00Z")]
        self.creates = 0
        self.writes = 0
        self.next_mode = None
        self.list_fail = False
        self.unavailable = set()
        self.lock = threading.RLock()

    def handler(self):
        state = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, body, status=200):
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def route(self):
                if self.headers.get("Bd-Project-Id") != PROJECT:
                    self.respond(dict(code="project_mismatch"), 409)
                    return
                url = urlparse(self.path)
                path, query = unquote(url.path), parse_qs(url.query)
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
                with state.lock:
                    if path == "/control":
                        if body.get("add_task"):
                            identity = body["add_task"]
                            state.tasks[identity] = task(identity, "Uncached explicit task")
                        if body.get("edit"):
                            item = state.tasks[body["edit"]]
                            item["revision"] = str(int(item["revision"]) + 1)
                            item["title"] = body.get("title", "Remote edit")
                        if "mode" in body:
                            state.next_mode = body["mode"]
                        if "list_fail" in body:
                            state.list_fail = body["list_fail"]
                        self.respond(dict(creates=state.creates, writes=state.writes, tasks=state.tasks, edges=state.edges))
                    elif path.endswith("/context"):
                        self.respond(dict(api_version="/v0", bd_version="1.3.4", backend="dolt", dolt_mode="server", schema_version=1, database="trial", project_id=PROJECT,
                                          capabilities=["project.enforce", "issues.list", "issues.get", "issues.create", "issues.update", "issues.batchApply", "issues.close", "issues.reopen", "dependencies.list", "config.get"]))
                    elif path.endswith("/config/issue_prefix"):
                        self.respond(dict(key="issue_prefix", value="trial", redacted=False))
                    elif path.endswith("/dependencies"):
                        ids = query.get("issue_id", [])
                        self.respond(dict(items=[e for e in state.edges if e["issue_id"] in ids], missing=[i for i in ids if i not in state.tasks]))
                    elif path.endswith("/issues"):
                        if state.list_fail:
                            self.respond(dict(code="unavailable"), 503)
                            return
                        # Force paging so a capped first result cannot masquerade as a whole tree.
                        items = list(state.tasks.values())
                        offset = int(query.get("cursor", ["0"])[0])
                        self.respond(dict(items=items[offset:offset+2], has_more=offset+2 < len(items), next_cursor=str(offset+2)))
                    elif path.endswith("/issues:batchApply"):
                        state.creates += 1
                        create = body["items"][0]["create"]
                        if create["id"] in state.tasks:
                            self.respond(dict(code="already_exists"), 409)
                            return
                        item = task(create["id"], create["title"])
                        item.update({k: v for k, v in create.items() if k in ("description", "acceptance_criteria", "metadata")})
                        state.tasks[item["id"]] = item
                        for edge in body["items"][1:]:
                            state.edges.append(dict(issue_id=item["id"], depends_on_id=edge["dep_add"]["target"]["id"], type="parent-child", created_at="2026-11-23T00:00:00Z"))
                        mode, state.next_mode = state.next_mode, None
                        if mode and mode.startswith("lost"):
                            if mode == "lost-missing":
                                del state.tasks[item["id"]]
                            elif mode == "lost-mismatch":
                                item["metadata"] = {}
                            elif mode == "lost-unavailable":
                                state.unavailable.add(item["id"])
                            elif mode == "lost-remote":
                                item["title"], item["revision"] = "Intervening remote edit", "2"
                            self.close_connection = True
                            self.connection.shutdown(2)
                            return
                        self.respond(dict(keys={"draft": item["id"]}, items=[dict(kind="create", issue_id=item["id"], revision=item["revision"], changed=True)]))
                    elif "/issues/" in path:
                        identity = path.rsplit("/", 1)[1]
                        operation = None
                        if ":" in identity:
                            identity, operation = identity.split(":", 1)
                        item = state.tasks.get(identity)
                        if item is None:
                            self.respond(dict(code="not_found"), 404)
                        elif self.command == "GET":
                            if identity in state.unavailable:
                                self.respond(dict(code="unavailable"), 503)
                            else:
                                self.respond(copy.deepcopy(item))
                        elif "expected_version" in body and body["expected_version"] != item["revision"]:
                            self.respond(dict(code="precondition_failed"), 409)
                        else:
                            if state.next_mode == "delay":
                                state.next_mode = None
                                time.sleep(.25)
                            state.writes += 1
                            if operation:
                                item["status"] = "closed" if operation == "close" else "open"
                            else:
                                item.update(body["patch"])
                            item["revision"] = str(int(item["revision"]) + 1)
                            if operation:
                                self.respond(dict(issue=item, revision=item["revision"], already_closed=False, already_open=False, open_children=0))
                            else:
                                self.respond(dict(issue=item, revision=item["revision"], changed=True))
                    else:
                        self.respond(dict(code="unknown_path"), 404)

            do_GET = route
            do_POST = route
            do_PATCH = route
        return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nui', type=Path, default=Path(os.environ.get('NVIM_TEST_NUI', str(Path.home() / '.local/share/nvim/lazy/nui.nvim'))))
    parser.add_argument('--presentation', action='store_true', help='check real Markview rendering instead of the save/recovery journey')
    parser.add_argument('--markview', type=Path, default=Path(os.environ.get('NVIM_TEST_MARKVIEW', str(Path.home() / '.local/share/nvim/lazy/markview.nvim'))))
    args = parser.parse_args()
    pin = json.loads((ROOT / 'nvim/lazy-lock.json').read_text())['nui.nvim']['commit']
    observed = subprocess.check_output(['git', '-C', str(args.nui), 'rev-parse', 'HEAD'], text=True).strip()
    if observed != pin:
        raise SystemExit(f'Use the locked nui.nvim revision {pin}; selected {observed}')
    if args.presentation:
        markview_pin = json.loads((ROOT / 'nvim/lazy-lock.json').read_text())['markview.nvim']['commit']
        markview_observed = subprocess.check_output(['git', '-C', str(args.markview), 'rev-parse', 'HEAD'], text=True).strip()
        if markview_observed != markview_pin:
            raise SystemExit(f'Use the locked Markview revision {markview_pin}; selected {markview_observed}')
    state = Boundary()
    with tempfile.TemporaryDirectory(prefix="nvim-beads-") as directory:
        with ThreadingHTTPServer(("127.0.0.1", 0), state.handler()) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            env = {**os.environ, "NVIM_TEST_NUI": str(args.nui.resolve()), "NVIM_TEST_MARKVIEW": str(args.markview.resolve()), "NVIM_LOG_FILE": str(Path(directory) / "nvim.log"), "BEADS_TEST_SETTINGS": json.dumps(dict(url=f"http://127.0.0.1:{server.server_port}", project_id=PROJECT, state_dir=directory))}
            try:
                scenarios = ['beads-markdown.lua'] if args.presentation else ['beads.lua', 'beads-restart.lua']
                for scenario in scenarios:
                    subprocess.run(["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n", "-l", "nvim/tests/" + scenario], cwd=ROOT, env=env, check=True, timeout=45)
            finally:
                server.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    main()
