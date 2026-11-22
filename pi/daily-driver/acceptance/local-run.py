#!/usr/bin/env python3
"""Native Pi submission acceptance; invoked by local-run.ts, never a live service."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading


class Provider(BaseHTTPRequestHandler):
    """The real Pi SDK consumes this deterministic, loopback-only completion stream."""

    requests = []

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.requests.append(request)
        message = request["messages"][-1]["content"]
        if isinstance(message, list):
            message = "".join(item.get("text", "") for item in message if isinstance(item, dict))
        token = re.search(r"GUIDANCE_[a-z_]+", str(message))
        content = "ACK_" + (token.group(0) if token else "ACCEPTED_CONTEXT")
        tool = request["messages"][-1]["role"] == "user" and "SUBMIT_WITH_TOOL_accepted" in str(message)
        planning = request["messages"][-1]["role"] == "user" and str(message).startswith("Draft a plan for ")
        spec = request["messages"][-1]["role"] == "user" and str(message).startswith("Begin Socrates discovery")
        planning = planning or (request["messages"][-1]["role"] == "user" and str(message).startswith("The operator froze"))
        if spec:
            delta = {"role": "assistant", "tool_calls": [{"index": 0, "id": "fixture-spec",
                     "type": "function", "function": {"name": "draft_socrates_specification",
                     "arguments": json.dumps({
                         "objective": "Verify the native lead handoff",
                         "scope": ["Disposable Beads checkout"],
                         "requirements": [{"id": "R1", "outcome": "Preserve approval evidence", "acceptance": "Verify the Beads graph"}],
                         "decisions": [{"decision": "Use the fixture verifier", "basis": "observed", "evidence": "Beads acceptance criteria"}],
                         "blockingQuestions": [],
                     })}}]}
        elif planning:
            names = {item["function"]["name"] for item in request["tools"]}
            assert "draft_implementation_plan" in names and not names.intersection({"write", "edit", "bash"}), names
            tasks = [
                {"key": "inspect", "title": "Inspect requirements", "description": "Read fixture", "acceptance": "Find marker", "requirements": ["R1"], "owns": ["README.md"]},
                {"key": "verify", "title": "Verify result", "description": "Run fixture check",
                 "acceptance": "Fixture passes", "blockedBy": ["inspect"], "requirements": ["R1"]},
            ]
            delta = {"role": "assistant", "tool_calls": [{"index": 0, "id": "fixture-draft-plan",
                     "type": "function", "function": {"name": "draft_implementation_plan",
                     "arguments": json.dumps({"summary": "Plan native fixture delivery", "tasks": tasks})}}]}
        elif tool:
            assert any(item["function"]["name"] == "task_submit_result" for item in request["tools"]), request
            delta = {"role": "assistant", "tool_calls": [{"index": 0, "id": "fixture-task-submit",
                     "type": "function", "function": {"name": "task_submit_result",
                     "arguments": json.dumps({"summary": "Acceptance accepted evidence"})}}]}
        else:
            delta = {"role": "assistant", "content": "ACK_TOOL_SUBMITTED" if
                     request["messages"][-1]["role"] == "tool" else content}
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        for delta, finish in ((delta, None), ({}, "tool_calls" if tool or planning or spec else "stop")):
            self.wfile.write(("data: " + json.dumps({
                "id": "fixture-completion", "object": "chat.completion.chunk", "created": 1,
                "model": "gpt-6.1-sol", "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
            }) + "\n\n").encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True

    def log_message(self, *_args):
        pass


def main():
    def terminate(_signal, _frame):
        raise SystemExit("Native acceptance interrupted")

    signal.signal(signal.SIGTERM, terminate)
    fixture = json.loads(Path(sys.argv[1]).read_text())
    root = Path(fixture["root"])
    work = Path(fixture["directory"])
    repository = Path(fixture["workspace"])
    binary = shutil.which("zellij")
    manager = shutil.which("worktree")
    assert binary and manager, "Install native zellij and worktree before acceptance"
    home = work / "pi-home"
    runtime = Path(tempfile.mkdtemp(prefix="pi-zj-", dir="/tmp"))
    temporary = work / "tmp"
    agent = work / "agent"
    guard = work / "guard"
    for directory in (home, temporary, agent, guard):
        directory.mkdir(mode=0o700)
    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    provider.daemon_threads = True
    provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    (agent / "models.json").write_text(json.dumps({"providers": {"openai-codex": {
        "baseUrl": f"http://127.0.0.1:{provider.server_port}/v1",
        "api": "openai-completions", "apiKey": "fixture",
        "models": [{"id": "gpt-6.1-sol", "name": "Local native acceptance fixture",
                    "reasoning": False, "input": ["text"], "contextWindow": 32768, "maxTokens": 2048,
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}],
    }}}))
    config_dir = home / ".config/zellij"
    config_dir.mkdir(parents=True)
    (config_dir / "config.kdl").write_text(
        'default_shell "/bin/sh"\nshow_startup_tips false\non_force_close "quit"\n'
    )
    sentinel = work / "unexpected-paseo"
    (guard / "paseo").write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {shlex.quote(str(sentinel))}\nexit 99\n"
    )
    (guard / "paseo").chmod(0o755)
    zellij_sentinel = work / "unexpected-zellij-subprocess"
    (guard / "zellij").write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {shlex.quote(str(zellij_sentinel))}\nexit 99\n"
    )
    (guard / "zellij").chmod(0o755)
    env = {
        **{key: value for key, value in os.environ.items() if key in (
            "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "DOLT_ROOT_PATH",
            "DOLT_CLI_NO_UPDATE_CHECK", "BD_DISABLE_METRICS", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM",
        )},
        "HOME": str(home),
        "SHELL": "/bin/sh",
        "PS1": "local-run-ready> ",
        "TERM": "xterm-256color",
        "COLORTERM": "truecolor",
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "XDG_RUNTIME_DIR": str(runtime),
        "ZELLIJ_SOCKET_DIR": str(runtime),
        "TMPDIR": str(temporary),
        "PATH": str(guard) + os.pathsep + os.environ["PATH"],
        "PI_CODING_AGENT_DIR": str(agent),
        "PI_DRIVER_CONFIG": str(work / "driver.json"),
        "PI_DRIVER_STATE_DIR": str(work / "journal"),
        "PI_SKIP_VERSION_CHECK": "1",
        "PI_TELEMETRY": "0",
        "PASEO_HOME": str(work / "paseo-unavailable"),
        "PASEO_URL": "http://127.0.0.1:9",
        "PASEO_ENDPOINT": "ws://127.0.0.1:9",
    }
    for key in (
        "ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
        "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV",
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AWS_PROFILE", "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    ):
        env.pop(key, None)
    role = {"provider": "openai-codex", "model": "gpt-6.1-sol", "reasoning": "off"}
    Path(env["PI_DRIVER_CONFIG"]).write_text(json.dumps({
        "beadsService": fixture["beadsService"],
        "profiles": {"personal": {name: role for name in ("lead", "worker", "reviewer", "explorer")}},
    }))

    def execute(args, *, cwd=repository, check=True):
        result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
        assert not check or result.returncode == 0, {
            "argv": args, "code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
        }
        return result

    driver = str(root / "bin/pi-driver")
    (repository / ".gitignore").write_text(".beads/\n.worktrees/\n")
    (repository / "README.md").write_text("Disposable native Pi acceptance repository.\n")
    execute(["git", "add", ".gitignore", "README.md"])
    execute(["git", "-c", "user.name=Acceptance", "-c", "user.email=acceptance@example.invalid",
             "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Initialize fixture"])
    execute(["git", "branch", "-M", "main"])
    workflow = runpy.run_path(str(root / "scripts/test-zellij.py"))
    Terminal = workflow["Terminal"]
    name = "pi-local-" + work.name
    terminal = Terminal(binary, env, name, install_navigation=False)
    report = {
        "runtime": "real Pi TUI, native worktree manager, Beads HTTP and Dolt",
        "submission": "task_submit_result and native /task-submit; deterministic loopback provider, no external inference",
        "paseo": "unreachable endpoint and failing executable sentinel",
        "session": name,
        "cases": [],
    }
    allocations = []
    artifacts = Path(fixture["output"]) / work.name if fixture.get("output") else work / "evidence"
    artifacts.mkdir(parents=True, exist_ok=True)
    report["artifacts"] = str(artifacts)
    report["outcome"] = "running"
    report["cleanup"] = "pending"

    def fresh(bead):
        return json.loads(execute([driver, "tasks", bead, "--json"]).stdout)

    def pane_text(pane):
        return terminal.action("dump-screen", "--full", "--pane-id", f"terminal_{pane}")

    try:
        terminal.until("fixture shell", lambda: b"local-run-ready> " in terminal.output)
        shell = terminal.terminals()
        assert len(shell) == 1, shell
        launcher_pane = shell[0]["id"]
        tab_id = next(p["tab_id"] for p in json.loads(
            terminal.action("list-panes", "--all", "--json")) if p["id"] == launcher_pane)
        scenarios = ("accepted", "failed-check", "changed-brief", "lead-plan", "socrates")
        selected = fixture.get("scenario")
        assert selected is None or selected in scenarios, selected
        for scenario in scenarios if selected is None else (selected,):
            created = json.loads(execute([
                fixture["bd"], "--sandbox", "create", "--title", f"Native Pi {scenario}",
                "--description", "Original bounded acceptance brief", "--type", "task", "--json",
                "--acceptance", "The agreed verifier must pass and preserve the accepted Git state",
            ]).stdout)
            bead = created["id"]
            exit_file = work / f"{scenario}.exit"
            verifier = ["/bin/sh", "-c", "printf 'native-check-evidence\\n'; exit " +
                        ("7" if scenario == "failed-check" else "0")]
            placement = ["--tab-id", str(tab_id)] if scenario == "accepted" else []
            worker_flag = [] if scenario in ("lead-plan", "socrates") else ["--worker"]
            start_command = shlex.join([driver, "start", bead, "--profile", "personal", *worker_flag,
                                        *placement, "--", *verifier])
            command = f"cd {shlex.quote(str(repository))} && {start_command}; printf '%s' $? > {shlex.quote(str(exit_file))}"
            assert any(p["id"] == launcher_pane for p in terminal.terminals()), "Owned launcher disappeared"
            terminal.action("write-chars", "--pane-id", f"terminal_{launcher_pane}", command + "\r")
            terminal.until("start dispatch completes", exit_file.exists)
            assert exit_file.read_text() == "0", pane_text(launcher_pane)
            assert any(p["id"] == launcher_pane and p["is_focused"]
                       for p in terminal.terminals()), terminal.terminals()
            before = fresh(bead)
            assert before["attempt"]["phase"] == "running", before
            assert before["attempt"]["session"] == name, before
            assert Path(before["attempt"]["checkout"]["path"]).resolve().is_relative_to(
                repository.resolve() / ".worktrees"), before
            allocations.append(before["attempt"]["checkout"])
            pane = before["attempt"]["pane"]
            assert pane != launcher_pane, before
            if scenario not in ("lead-plan", "socrates"):
                terminal.until("interactive Pi startup", lambda: "ctrl+c" in pane_text(pane).lower())
            if scenario in ("lead-plan", "socrates"):
                terminal.until("read-only lead drafts plan", lambda:
                               fresh(bead)["attempt"].get("leadPlan", {}).get("draft") is not None)
                assert "pi.plan" not in fresh(bead)["task"]["metadata"], fresh(bead)
                terminal.action("focus-pane-id", f"terminal_{pane}")
                if scenario == "socrates":
                    terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "/socrates\r")
                    terminal.until("Socrates draft saved", lambda:
                                   fresh(bead)["attempt"].get("specification", {}).get("draft") is not None)
                    assert "pi.plan" not in fresh(bead)["task"]["metadata"]
                    terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "/spec-freeze\r")
                    terminal.until("specification review opens", lambda: "Freeze specification for " + bead in pane_text(pane))
                    terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "\r")
                    terminal.until("frozen specification has a plan", lambda:
                                   fresh(bead)["attempt"]["specification"]["status"] == "frozen" and
                                   fresh(bead)["attempt"]["leadPlan"]["draft"] is not None)
                terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "/diff\r")
                terminal.until("review extension renders", lambda: "Git diff" in pane_text(pane))
                terminal.action("write", "--pane-id", f"terminal_{pane}", "27")
                terminal.until("review viewer closes", lambda: "Git diff" not in
                               terminal.action("dump-screen", "--pane-id", f"terminal_{pane}"))
                terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "/plan-approve\r")
                terminal.until("operator approval prompt", lambda: "Approve the plan for " + bead in pane_text(pane))
                for _ in range(8):
                    if "Enter start implementation" in terminal.action("dump-screen", "--pane-id", f"terminal_{pane}"):
                        break
                    terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "\r")
                else:
                    raise AssertionError(pane_text(pane))
                terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "\r")
                terminal.until("approved task breakdown persisted", lambda:
                               fresh(bead)["attempt"]["leadPlan"]["mode"] == "implementing")
                approved = fresh(bead)
                plan = approved["attempt"]["leadPlan"]
                assert approved["task"]["metadata"]["pi.plan"] == plan["digest"], approved
                assert len(set(plan["children"].values())) == 2, approved
                for key, child in plan["children"].items():
                    task = fresh(child)["task"]
                    assert task["metadata"]["pi.plan_key"] == key, task
                    assert task["metadata"]["pi.plan"] == plan["digest"], task
                tree = json.loads(execute([driver, "tasks", "--json"]).stdout)["tasks"]
                views = {task["id"]: task for task in tree}
                for child in plan["children"].values():
                    assert any(edge["id"] == bead and edge["dependency_type"] == "parent-child"
                               for edge in views[child]["dependencies"]), views[child]
                assert any(edge["id"] == plan["children"]["inspect"] and edge["dependency_type"] == "blocks"
                           for edge in views[plan["children"]["verify"]]["dependencies"])
                terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "/plan-approve\r")
                terminal.until("second approval refused", lambda: "No draft to approve" in pane_text(pane))
                assert fresh(bead)["attempt"]["leadPlan"] == plan
                terminal.action("write-chars", "--pane-id", f"terminal_{pane}",
                                "/task-submit Acceptance lead verification\r")
                terminal.until("lead verification persisted", lambda:
                               fresh(bead)["attempt"]["phase"] == "verified")
                verified = fresh(bead)
                assert verified["task"]["status"] == "in_progress", verified
                assert verified["attempt"]["verification"]["exitCode"] == 0, verified
                terminal.action("write", "--pane-id", f"terminal_{pane}", "4")
                terminal.until("lead Pi exit", lambda: all(p["id"] != pane or p["exited"] for p in terminal.terminals()))
                if scenario == "socrates":
                    original = fresh(bead)["attempt"]
                    resume_exit = work / "socrates-resume.exit"
                    resume_command = shlex.join([driver, "resume", bead])
                    terminal.action("focus-pane-id", f"terminal_{launcher_pane}")
                    terminal.action("write-chars", "--pane-id", f"terminal_{launcher_pane}",
                                    f"{resume_command}; printf '%s' $? > {shlex.quote(str(resume_exit))}\r")
                    terminal.until("resume returns", resume_exit.exists)
                    assert resume_exit.read_text() == "0", pane_text(launcher_pane)
                    reopened = fresh(bead)["attempt"]
                    for key in ("id", "checkout", "transcript", "phase", "specification", "leadPlan"):
                        assert reopened[key] == original[key], reopened
                    assert reopened["pid"] != original["pid"] and reopened["live"], reopened
                    pane = reopened["pane"]

                    # Exercise transport at the Octo CLI boundary. Octo's real CLI runs its own
                    # coordinator/receipt acceptance against a controlled GitHub provider.
                    checkout = reopened["checkout"]
                    head = reopened["verification"]["gitHead"]
                    receipt_id = "00000000-0000-4000-8000-000000000171"
                    url = "https://github.com/fixture/repo/pull/1"
                    reference = work / "origin.git"
                    execute(["git", "init", "--bare", str(reference)])
                    execute(["git", "remote", "add", "origin", str(reference)])
                    execute(["git", "push", "origin", "main"])
                    description = work / "description.md"
                    description.write_text("Deliver the fixture.\n")
                    binding = {
                        "id": "fixture-submission", "state": "published",
                        "tracking": "active", "url": url,
                    }
                    octo = guard / "octo-manager"
                    octo.write_text(
                        "#!/usr/bin/env python3\nimport json, sys\n"
                        "args=sys.argv[1:]\n"
                        "answers=" + repr({
                            ("submit-pr",): binding,
                            ("submission",): binding,
                            ("agent", "register"): {
                                "agent": {"id": "fixture-agent", "harness": "pi",
                                          "endpoint": "local", "sessionId": reopened["id"]},
                            },
                            ("pr", "show"): {
                                "pr": {"id": "fixture-pr", "url": url, "ownerAgentId": "fixture-agent",
                                       "observation": {"headSha": head, "lifecycle": "merged",
                                                       "targetBase": {"ref": "main"}}},
                            },
                            ("agent", "inbox"): {
                                "messages": [{"id": receipt_id, "recipientAgentId": "fixture-agent",
                                              "workflowPrId": "fixture-pr", "actionId": "",
                                              "applicable": True, "body": "Fixture ready", "readyHead": head}],
                                "nextSequence": 1, "hasMore": False,
                            },
                            ("acknowledge-message",): {"message": receipt_id, "applicable": True},
                            ("merge",): {"state": "merged", "pr": url, "entry": "fixture-entry", "chain": "fixture-chain"},
                            ("chain", "show"): {"entries": [{
                                "id": "fixture-entry", "chainId": "fixture-chain", "prId": "fixture-pr",
                                "state": "merged", "mergeCommit": head, "ready": {"head": head},
                                "receiptId": f"pi-inbox:{receipt_id}:{head}",
                            }]},
                        }) + "\n"
                        "if args[0] in ('submit-pr', 'merge'):\n"
                        " assert args[args.index('--expected-head')+1] == " + repr(head) + "\n"
                        "print(json.dumps(answers.get(tuple(args[:2])) or answers[(args[0],)]))\n"
                    )
                    octo.chmod(0o755)
                    execute([driver, "publish", bead, "--title", "feat: deliver fixture",
                             "--body-file", str(description), "--base", "main"])
                    terminal.action("focus-pane-id", f"terminal_{pane}")
                    terminal.action("write-chars", "--pane-id", f"terminal_{pane}", "/octo-inbox\r")
                    terminal.until("Octo notice reaches native Pi inbox", lambda: "Fixture ready" in pane_text(pane))
                    terminal.action("write", "--pane-id", f"terminal_{pane}", "27")
                    terminal.until("Octo inbox closes", lambda: "Fixture ready" not in
                                   terminal.action("dump-screen", "--pane-id", f"terminal_{pane}"))
                    terminal.action("write", "--pane-id", f"terminal_{pane}", "4")
                    terminal.until("resumed Pi exits", lambda: all(p["id"] != pane or p["exited"] for p in terminal.terminals()))
                    execute([driver, "merge", bead, "--head", head, "--notice", receipt_id])
                    pending = execute([driver, "archive", bead], check=False)
                    assert pending.returncode != 0 and "Settle child beads" in pending.stderr, pending
                    assert Path(checkout["path"]).exists() and fresh(bead)["task"]["status"] == "in_progress"
                    for child in (plan["children"]["inspect"], plan["children"]["verify"]):
                        execute([fixture["bd"], "--sandbox", "close", child])
                    archived = json.loads(execute([driver, "archive", bead]).stdout)
                    assert archived["phase"] == "archived", archived
                    assert not Path(checkout["path"]).exists(), archived
                    assert fresh(bead)["task"]["status"] == "closed"
                    manifest = Path(archived["archiveManifest"])
                    assert manifest.is_file() and manifest.with_name(reopened["id"] + ".jsonl").is_file()
                    assert json.loads(execute([driver, "archive", bead]).stdout) == archived
                    shutil.copytree(manifest.parent, artifacts / "archive")
                    allocations.remove(checkout)
                report["cases"].append({"scenario": scenario, "bead": bead, "evidence": fresh(bead)})
                continue
            if scenario == "accepted":
                report["registered_process"] = execute(["ps", "-p", str(before["attempt"]["pid"]),
                                                        "-o", "command="]).stdout.strip()
                report["registered_pane"] = next(p for p in
                    json.loads(terminal.action("list-panes", "--all", "--json")) if p["id"] == pane)
                terminal.action("focus-pane-id", f"terminal_{launcher_pane}")
                repeat_exit = work / "repeated-start.exit"
                repeat_command = f"{start_command}; printf '%s' $? > {shlex.quote(str(repeat_exit))}"
                terminal.action("write-chars", "--pane-id", f"terminal_{launcher_pane}", repeat_command + "\r")
                terminal.until("identical start focuses existing worker", repeat_exit.exists)
                assert repeat_exit.read_text() == "0", pane_text(launcher_pane)
                repeated = fresh(bead)
                for key in ("id", "checkout", "pane", "pid", "transcript", "zellijSocket"):
                    assert repeated["attempt"][key] == before["attempt"][key], repeated
                assert any(p["id"] == pane and p["is_focused"] for p in terminal.terminals()), terminal.terminals()
                inventory = json.loads(execute([manager, "status", "--json"]).stdout)
                assert len(inventory["result"]["tasks"]) == 1, inventory
            guidance = f"GUIDANCE_{scenario.replace('-', '_')} for accepted bead {bead}"
            terminal.action("write-chars", "--pane-id", f"terminal_{pane}", guidance + "\r")
            terminal.until("Pi responds to guidance in its original pane", lambda:
                           "ACK_GUIDANCE_" + scenario.replace("-", "_") in pane_text(pane))
            observed = json.dumps(Provider.requests)
            assert bead in observed and "Original bounded acceptance brief" in observed and guidance in observed, observed
            if scenario == "changed-brief":
                execute([fixture["bd"], "--sandbox", "update", bead, "--description",
                         "Changed acceptance scope while Pi owns the old brief"])
            # Both native submission surfaces reach the same guarded verification path.
            terminal.action("write-chars", "--pane-id", f"terminal_{pane}",
                            "SUBMIT_WITH_TOOL_accepted\r" if scenario == "accepted" else
                            f"/task-submit Acceptance {scenario} evidence\r")
            terminal.until("submission persisted", lambda:
                           fresh(bead)["attempt"]["phase"] not in ("running", "checking"))
            submitted = fresh(bead)
            expected = {"accepted": "closed", "failed-check": "check_failed", "changed-brief": "needs_review"}
            assert submitted["projectId"] == fixture["beadsService"]["projectId"], submitted
            assert submitted["task"]["id"] == bead == submitted["attempt"]["bead"]["id"], submitted
            assert submitted["attempt"]["phase"] == expected[scenario], submitted
            assert (submitted["task"]["status"] == "closed") == (scenario == "accepted"), submitted
            verification = submitted["attempt"]["verification"]
            if scenario == "changed-brief":
                assert any(word in submitted["attempt"]["message"].lower()
                           for word in ("brief", "revision", "changed")), submitted
                assert submitted["task"]["description"] != submitted["attempt"]["bead"]["description"], submitted
            if scenario != "changed-brief":
                assert verification["exitCode"] == (7 if scenario == "failed-check" else 0), verification
                assert "native-check-evidence" in verification["output"], verification
                assert verification["gitHead"], verification
            if scenario == "accepted":
                assert submitted["task"]["metadata"]["pi.result"] == verification, submitted
                assert submitted["task"]["metadata"]["pi.result_attempt"] == submitted["attempt"]["id"], submitted
                terminal.until("Pi receives native tool result", lambda: "ACK_TOOL_SUBMITTED" in pane_text(pane))
            else:
                assert "pi.result" not in submitted["task"]["metadata"], submitted
            (artifacts / f"{scenario}.screen.txt").write_text(pane_text(pane))
            (artifacts / f"{scenario}.screen.ansi").write_text(
                terminal.action("dump-screen", "--full", "--ansi", "--pane-id", f"terminal_{pane}"))
            # Empty-editor Ctrl-D exits Pi; retain its caller shell for the next independent bead.
            terminal.action("write", "--pane-id", f"terminal_{pane}", "4")
            terminal.until("Pi exit", lambda: all(p["id"] != pane or p["exited"] for p in terminal.terminals()))
            after_exit = fresh(bead)
            assert after_exit["attempt"]["verification"] == verification, after_exit
            assert after_exit["attempt"]["phase"] == expected[scenario], after_exit
            if scenario == "failed-check":
                stale_exit = work / "stale-start.exit"
                stale_start = f"{start_command}; printf '%s' $? > {shlex.quote(str(stale_exit))}"
                terminal.action("write-chars", "--pane-id", f"terminal_{launcher_pane}",
                                stale_start + "\r")
                terminal.until("exited worker rejects refocus", stale_exit.exists)
                assert stale_exit.read_text() != "0", pane_text(launcher_pane)
                assert "registered Pi process or pane has exited or changed" in pane_text(launcher_pane)
                assert fresh(bead)["attempt"] == after_exit["attempt"]
            report["cases"].append({"scenario": scenario, "bead": bead, "evidence": after_exit})
        assert not sentinel.exists(), sentinel.read_text() if sentinel.exists() else ""
        assert not zellij_sentinel.exists(), (
            zellij_sentinel.read_text() if zellij_sentinel.exists() else ""
        )
        report["outcome"] = "passed"
        (artifacts / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        (artifacts / "provider-requests.json").write_text(json.dumps(Provider.requests, indent=2) + "\n")
    finally:
        if report["outcome"] == "running":
            report["outcome"] = "failed"
        (artifacts / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        (artifacts / "provider-requests.json").write_text(json.dumps(Provider.requests, indent=2) + "\n")
        (artifacts / "terminal.ansi").write_bytes(terminal.output)
        subprocess.run([binary, "--session=" + name, "kill-session"], env=env,
                       capture_output=True, timeout=10)
        terminal.close()
        inventory = execute([manager, "status", "--json"], check=False)
        known = {checkout["task_id"] for checkout in allocations}
        for task in json.loads(inventory.stdout)["result"]["tasks"]:
            if (task["id"] not in known and Path(task["path"]).exists() and Path(task["path"]).resolve().is_relative_to(
                    repository.resolve() / ".worktrees")):
                allocations.append({"task_id": task["id"], "path": task["path"]})
        for checkout in allocations:
            execute([manager, "finish", checkout["task_id"], "--json"])
            assert not execute(["git", "status", "--porcelain", "--untracked-files=all"],
                               cwd=checkout["path"]).stdout, checkout
            assert not execute(["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
                               cwd=checkout["path"]).stdout, checkout
            prune = [manager, "prune", "--worktree", checkout["path"], "--accept-recent"]
            execute(prune)
            execute([*prune, "-y"])
            assert not Path(checkout["path"]).exists(), checkout
        provider.shutdown()
        provider.server_close()
        provider_thread.join(timeout=5)
        shutil.rmtree(runtime)
        report["cleanup"] = "confirmed"
        (artifacts / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
