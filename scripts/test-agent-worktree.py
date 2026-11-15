#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets==15.0.1", "psutil==7.2.2"]
# ///
"""Exercise agent worktree launchers against the native manager, real Git, and lsof."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import select
import runpy
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

from websockets.sync.server import unix_serve


ROOT = Path(__file__).resolve().parents[1]


def wait_for(predicate):
    deadline = time.monotonic() + 45
    while not predicate():
        assert time.monotonic() < deadline, "deferred return did not finish"
        time.sleep(0.1)


@contextmanager
def fixture(client):
    manager = os.environ.get("WORKTREE_MANAGER_BINARY") or shutil.which("worktree")
    assert manager, "install the worktree manager before running this detector"
    with tempfile.TemporaryDirectory(prefix="agent-treehouse-", dir="/tmp") as name:
        folder = Path(name).resolve()
        home, bins, project = folder / "home", folder / "bin", folder / "project"
        for path in (home, bins, project):
            path.mkdir()
        (home / ".files").symlink_to(ROOT)
        config = home / ".config/treehouse"
        config.mkdir(parents=True)
        (config / "config.toml").write_text('root = ".worktrees"\nunique_leaf = true\n')
        env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_STATE_HOME": str(home / ".local/state"), "CLAUDE_CONFIG_DIR": str(home / ".claude"),
               "CODEX_HOME": str(home / ".codex"), "PASEO_HOME": str(home / ".paseo"),
               "PATH": str(bins) + os.pathsep + os.environ["PATH"],
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
               "WORKTREE_TEST_REAL": manager, "AGENT_TEST_LOG": str(folder / "agent.json"),
               "WORKTREE_TEST_LOG": str(folder / "treehouse.jsonl"),
               "UV_CACHE_DIR": subprocess.check_output(["uv", "cache", "dir"], text=True).strip()}
        for key in tuple(env):
            if key.startswith(("TREEHOUSE_", "AGENT_TREEHOUSE_", "CLAUDE_CODE_", "FM_")) and not key.startswith("TREEHOUSE_TEST_"):
                env.pop(key)
        env["TREEHOUSE_NO_UPDATE_CHECK"] = "1"
        wrapper = bins / "worktree"
        wrapper.write_text("#!" + sys.executable + "\n" + '''
import json, os, sys
with open(os.environ["WORKTREE_TEST_LOG"], "a") as out:
    out.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1] == "create" and os.environ.get("AGENT_TEST_MODE") == "failure":
    print("requested allocation failure", file=sys.stderr)
    sys.exit(23)
args = [os.environ["WORKTREE_TEST_REAL"], *sys.argv[1:]]
if sys.argv[1] == "create" and os.environ.get("AGENT_TEST_MODE") == "lost":
    import subprocess
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
    sys.exit(0)
os.execv(args[0], args)
''')
        wrapper.chmod(0o755)
        paseo = bins / "paseo"
        paseo.write_text("#!/bin/sh\nprintf '[]\\n'\n")
        paseo.chmod(0o755)
        agent = bins / client
        agent.write_text("#!" + sys.executable + "\n" + '''
import json, os
from pathlib import Path
import shlex, signal, subprocess, sys, time
args = sys.argv[1:]
client = Path(sys.argv[0]).name
if client == "claude" and args == ["agents", "--json"]:
    print("[]")
    sys.exit(0)
original = list(args)
settings = {}
if client == "codex" and "--cd" in args:
    os.chdir(args[args.index("--cd") + 1])
if client == "claude":
    values = [args[i+1] for i, arg in enumerate(args[:-1]) if arg == "--settings"]
    settings = (json.loads(values[-1]) if values[-1].startswith("{") else
                json.loads(Path(values[-1]).read_text())) if values else {}
hooks = settings.get("hooks", {})
session_id = "test-session"
def event(event_name, **fields):
    payload = dict(hook_event_name=event_name, session_id=session_id, cwd=os.getcwd(), **fields)
    result = None
    for group in hooks.get(event_name, []):
        for handler in group["hooks"]:
            result = subprocess.run(["/bin/sh", "-c", handler["command"]],
                                    input=json.dumps(payload), text=True, capture_output=True)
            if result.returncode:
                if event_name != "WorktreeRemove":
                    print(result.stderr, file=sys.stderr)
                    sys.exit(result.returncode)
    return result
if hooks:
    result = event("WorktreeCreate", name="quoted task")
    if result is not None:
        os.chdir(result.stdout.strip())
    session_id = "actual-session"
    event("SessionStart")
mode = os.environ.get("AGENT_TEST_MODE", "clean")
root = Path.cwd()
subagent = None
if hooks and mode == "subagent":
    result = event("WorktreeCreate", name="child task")
    subagent = result.stdout.strip()
if (client == "codex" and "--worktree" not in original) or (client == "claude" and hooks):
    if mode == "dirty":
        (root/"valuable.txt").write_text("Keep this unsaved work.\\n")
    elif mode == "ignored":
        (root/"private.log").write_text("Keep this ignored evidence.\\n")
    elif mode == "busy":
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"],
                                cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        (Path(os.environ["AGENT_TEST_LOG"]).parent/"busy.pid").write_text(str(proc.pid))
    elif mode == "clean":
        (root/"completed.txt").write_text("Preserve the completed task.\\n")
        subprocess.run(["git","add","completed.txt"], check=True)
        subprocess.run(["git","-c","user.name=Agent test","-c","user.email=test@example.invalid",
                        "-c","commit.gpgsign=false","commit","-qm","Complete task"], check=True)
record = dict(args=original, cwd=str(root), settings=settings,
              session=os.environ.get("AGENT_TREEHOUSE_SESSION"), subagent=subagent,
              head=subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip())
Path(os.environ["AGENT_TEST_LOG"]).write_text(json.dumps(record))
if hooks:
    event("WorktreeRemove", worktree_path=str(root))
    event("SessionEnd")
if mode == "signal":
    print("READY", flush=True)
    time.sleep(120)
sys.exit(7)
''')
        agent.chmod(0o755)
        if client == "codex":
            claude = bins / "claude"
            claude.write_text("#!/bin/sh\nprintf '[]\\n'\n")
            claude.chmod(0o755)

        def git(*args, cwd=project):
            return subprocess.check_output(
                ["git", "-c", "user.name=Treehouse test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "-C", str(cwd), *args], env=env,
                text=True, stderr=subprocess.PIPE).strip()

        git("init", "-q", "--initial-branch", "main")
        (project / ".gitignore").write_text(".worktrees/\nprivate.log\n.codex/\n")
        (project / "subdirectory").mkdir()
        (project / "subdirectory/file.txt").write_text("Subdirectory work root.\n")
        git("add", ".")
        git("commit", "-qm", "Initialize fixture")
        stale = folder / "stale-repository"
        git("clone", "-q", str(project), str(stale))
        subprocess.run([manager, "backfill", str(stale), "--json"], env=env,
                       check=True, capture_output=True, text=True)
        shutil.rmtree(stale)
        socket = home / ".codex/app-server-control/app-server-control.sock"
        socket.parent.mkdir(parents=True)
        sessions = {}

        def handler(connection):
            for raw in connection:
                message = json.loads(raw)
                if "id" not in message:
                    continue
                method = message["method"]
                if method == "initialize":
                    result = {}
                elif method == "thread/loaded/list":
                    result = {"data": list(sessions), "nextCursor": None}
                elif method == "thread/read":
                    result = {"thread": sessions[message["params"]["threadId"]]}
                else:
                    raise AssertionError("unexpected RPC " + method)
                connection.send(json.dumps({"id": message["id"], "result": result}))

        with unix_serve(handler, str(socket), ping_interval=None) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                yield folder, project, env, git, sessions
            finally:
                server.shutdown()
                thread.join(timeout=5)
                busy_pid = folder / "busy.pid"
                if busy_pid.exists():
                    try:
                        os.kill(int(busy_pid.read_text()), signal.SIGTERM)
                    except ProcessLookupError:
                        pass


def launch(client, project, env, args):
    shell = shutil.which("zsh")
    return subprocess.run(
        [shell, "-f", "-c", 'source "$HOME/.files/sh/alias"; ' + client + ' "$@"', "--", *args],
        cwd=project, env=env, text=True, capture_output=True, timeout=30)


def records(env, session=None):
    path = Path(env["XDG_STATE_HOME"]) / "agent-treehouse/returns.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    return [row for row in rows if row["session"] == session] if session else rows


def retry(env):
    state = Path(env["XDG_STATE_HOME"]) / "agent-treehouse"
    for path in state.glob("*.json"):
        if not json.loads(path.read_text())["leases"]:
            continue
        subprocess.run([sys.executable, str(ROOT / "bin/agent-worktree"), "reap", path.stem],
                       env=env, cwd="/", check=True, timeout=45)


def codex_workflow():
    with fixture("codex") as (folder, project, env, git, sessions):
        args = ["exec", "--worktree", "--cd", str(project / "subdirectory"),
                "-c", 'custom="space and $dollar"', "--json", "quoted prompt ; $(false)"]
        result = launch("codex", project, env, args)
        assert result.returncode == 7, result.stderr
        observed = json.loads((folder / "agent.json").read_text())
        root = Path(observed["cwd"]).parent
        assert root.parent == project / ".worktrees" and root.name.startswith("codex-")
        assert observed["args"][2:] == ["exec", "-c", 'custom="space and $dollar"',
                                        "--json", "quoted prompt ; $(false)"], observed
        wait_for(lambda: records(env))
        assert records(env)[-1]["action"] == "finished", records(env)
        branch = git("for-each-ref", "--format=%(refname)", "refs/heads/worktree/")
        assert git("rev-parse", branch) == observed["head"]
        assert root.is_dir(), "finished checkout was deleted"

        env["AGENT_TEST_MODE"] = "failure"
        result = launch("codex", project, env, args)
        assert result.returncode == 1 and "allocation failed" in result.stderr, result
        env["AGENT_TEST_MODE"] = "dirty"
        result = launch("codex", project, env, ["--worktree", "keep my work"])
        assert result.returncode == 7, result
        session = json.loads((folder / "agent.json").read_text())["session"]
        wait_for(lambda: records(env, session))
        retained = records(env, session)[-1]
        assert retained["reason"] == "dirty checkout", retained
        assert (Path(retained["path"]) / "valuable.txt").exists()
        (Path(retained["path"]) / "valuable.txt").unlink()
        sessions["other"] = {"id": "other", "cwd": retained["path"], "status": {"type": "idle"}}
        retry(env)
        assert records(env)[-1]["reason"] == "Codex session references checkout", records(env)
        sessions.clear()
        retry(env)
        assert records(env)[-1]["action"] == "finished", records(env)

        env["AGENT_TEST_MODE"] = "assigned"
        assigned = Path(retained["path"])
        result = launch("codex", project, env, ["--worktree", "--cd", str(assigned), "reuse assigned"])
        assert result.returncode == 7, result
        observed = json.loads((folder / "agent.json").read_text())
        assert observed["cwd"] == str(assigned) and observed["session"] is None

        env["AGENT_TEST_MODE"] = "signal"
        previous = (folder / "agent.json").read_text()
        process = subprocess.Popen([str(ROOT / "bin/codex-wrapper"), "--worktree", "signal probe"],
                                   cwd=project, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            wait_for(lambda: (folder / "agent.json").read_text() != previous)
            assert select.select([process.stdout], [], [], 5)[0], "client did not become ready"
            ready = process.stdout.readline()
            process.terminate()
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == -signal.SIGTERM and ready + stdout == "READY\n", (ready, stdout, stderr)
            session = json.loads((folder / "agent.json").read_text())["session"]
            wait_for(lambda: records(env, session))
            assert records(env, session)[-1]["action"] == "finished", records(env)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)

        env["AGENT_TEST_MODE"] = "assigned"
        (folder / "bin/worktree").unlink()
        native_bins = folder / "native"
        native_bins.mkdir()
        for name in ("python3", "git", "bash", "uname", "dirname"):
            (native_bins / name).symlink_to(shutil.which(name))
        (native_bins / "codex").symlink_to(folder / "bin/codex")
        env["PATH"] = str(native_bins)
        result = launch("codex", project, env, ["exec", "--worktree", "native fallback"])
        assert result.returncode == 1 and "manager unavailable" in result.stderr, result
    print("PASS: Codex shell request uses the worktree manager, preserves arguments/branches, fails closed, and retains shared work.")


def claude_workflow():
    with fixture("claude") as (folder, project, env, git, _sessions):
        original = {"custom": "space and $dollar", "hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "existing stop hook"}]}]}}
        private_settings = folder / "private-settings.json"
        private_settings.write_text(json.dumps(original))
        private_settings.chmod(0o600)
        args = ["--worktree", "quoted task", "--settings", '{"unused":true}',
                "--setting-sources", "", "--settings", str(private_settings),
                "-p", "quoted prompt ; $(false)"]
        result = launch("claude", project, env, args)
        assert result.returncode == 7, result.stderr
        observed = json.loads((folder / "agent.json").read_text())
        assert observed["settings"]["custom"] == original["custom"]
        assert observed["settings"]["hooks"]["Stop"] == original["hooks"]["Stop"]
        assert "unused" not in observed["settings"]
        assert observed["args"][-2:] == args[-2:]
        assert original["custom"] not in " ".join(observed["args"])
        root = Path(observed["cwd"])
        assert root.parent == project / ".worktrees" and root.name.startswith("claude-")
        wait_for(lambda: records(env))
        assert records(env)[-1]["action"] == "finished", records(env)
        branch = git("for-each-ref", "--format=%(refname)", "refs/heads/worktree/")
        assert git("rev-parse", branch) == observed["head"]
        assert root.is_dir()

        env["AGENT_TEST_MODE"] = "busy"
        result = launch("claude", project, env, args)
        assert result.returncode == 7, result
        session = json.loads((folder / "agent.json").read_text())["session"]
        wait_for(lambda: records(env, session))
        assert records(env, session)[-1]["action"] == "retained", records(env)
        assert "active process" in records(env, session)[-1]["reason"], records(env)
        os.kill(int((folder / "busy.pid").read_text()), signal.SIGTERM)
        wait_for(lambda: subprocess.run(["ps", "-p", (folder / "busy.pid").read_text()],
                                        capture_output=True).returncode == 1)
        retry(env)
        assert records(env)[-1]["action"] == "finished", records(env)

        env["AGENT_TEST_MODE"] = "subagent"
        result = launch("claude", project, env, args)
        assert result.returncode == 7, result
        observed = json.loads((folder / "agent.json").read_text())
        assert observed["subagent"] != observed["cwd"], observed
        wait_for(lambda: len(records(env, observed["session"])) == 2)
        assert all(row["action"] == "finished" for row in records(env, observed["session"])), records(env)

        env["AGENT_TEST_MODE"] = "failure"
        result = launch("claude", project, env, args)
        assert result.returncode == 1 and "allocation failed" in result.stderr, result
        result = launch("claude", project, env, ["--worktree", "--bare"])
        assert result.returncode == 7, result
        assert json.loads((folder / "agent.json").read_text())["args"] == ["--worktree", "--bare"]
        conflict = {"hooks": {"WorktreeCreate": [{"hooks": [{"type": "command", "command": "custom factory"}]}]}}
        result = launch("claude", project, env, ["--worktree", "--settings", json.dumps(conflict)])
        assert result.returncode == 1 and "conflicting" in result.stderr, result

        native_bins = folder / "native"
        native_bins.mkdir()
        for name in ("python3", "git", "bash", "uname"):
            (native_bins / name).symlink_to(shutil.which(name))
        (native_bins / "claude").symlink_to(folder / "bin/claude")
        env["PATH"] = str(native_bins)
        result = launch("claude", project, env, ["--worktree", "-p", "native fallback"])
        assert result.returncode == 1 and "manager unavailable" in result.stderr, result
    print("PASS: Claude factory hooks preserve settings, finish clean tasks, and retain concurrent work.")


def lost_response_workflow(uncertain=False):
    with fixture("claude") as (folder, project, env, _git, _sessions):
        record_env = {key: os.environ.get(key) for key in ("HOME", "XDG_STATE_HOME")}
        try:
            os.environ.update({key: env[key] for key in record_env})
            adapter = runpy.run_path(str(ROOT / "bin/agent-worktree"))
            token = adapter["new_session"]("claude", project, str(folder / "bin/worktree"), str(folder / "bin/claude"))
        finally:
            for key, value in record_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        if uncertain:
            hook = project / ".git/hooks/post-checkout"
            primary = shlex.quote(str(project))
            hook.write_text("#!/bin/sh\nunset GIT_DIR GIT_COMMON_DIR GIT_WORK_TREE GIT_INDEX_FILE\n"
                            + "target=$(git -C " + primary + " worktree list --porcelain | sed -n 's/^worktree //p' | tail -n 1)\n"
                            + "git -C " + primary + ' worktree remove --force --force "$target"\n')
            hook.chmod(0o755)
        else:
            env["AGENT_TEST_MODE"] = "lost"
        event = json.dumps({"hook_event_name": "WorktreeCreate", "session_id": "native-session", "cwd": str(project)})
        for attempt in range(2):
            result = subprocess.run([sys.executable, str(ROOT / "bin/agent-worktree"), "hook", token],
                                    input=event, env=env, text=True, capture_output=True, timeout=30)
            assert result.returncode == 1, result
            if attempt:
                assert "outcome remains unknown" in result.stderr, result.stderr
        calls = [json.loads(line) for line in (folder / "treehouse.jsonl").read_text().splitlines()]
        assert sum(call[0] == "create" for call in calls) == 1, calls
        record = json.loads((Path(env["XDG_STATE_HOME"]) / "agent-treehouse" / (token + ".json")).read_text())
        assert len(record["pending"]) == 1 and record["pending"][0]["owner_id"]
        status = subprocess.run([env["WORKTREE_TEST_REAL"], "status", "--json"], env=env,
                                text=True, capture_output=True)
        assert status.returncode == 1 and not json.loads(status.stdout)["result"]["complete"]
        tasks = json.loads(status.stdout)["result"]["tasks"]
        assert len(tasks) == 1 and tasks[0]["owner_id"] == record["pending"][0]["owner_id"]
        if uncertain:
            assert tasks[0]["state"] == "uncertain" and len(record["leases"]) == 1
    print("PASS: A lost or uncertain allocation response retains durable intent and prevents a second checkout.")


def legacy_workflow():
    treehouse = shutil.which("treehouse")
    assert treehouse, "install Treehouse to verify outstanding legacy returns"
    with fixture("codex") as (_folder, project, env, git, _sessions):
        result = subprocess.run([treehouse, "get", "--lease", "--json", "--no-fetch",
                                 "--branch", "legacy/preserve", "--lease-holder", "legacy-holder"],
                                cwd=project, env=env, capture_output=True, text=True, check=True)
        lease = json.loads(result.stdout)
        lease.update(primary=str(project), branch="legacy/preserve")
        state = Path(env["XDG_STATE_HOME"]) / "agent-treehouse"
        state.mkdir(parents=True, mode=0o700)
        token = "e" * 32
        record = {"client": "codex", "primary": str(project), "treehouse": treehouse,
                  "executable": str(Path(env["PATH"].split(os.pathsep)[0]) / "codex"),
                  "pid": 99999999, "started": "ended legacy process", "ended": True,
                  "sessions": {}, "leases": [lease], "pending": []}
        path = state / (token + ".json")
        path.write_text(json.dumps(record))
        path.chmod(0o600)
        subprocess.run(["uv", "run", "--script", str(ROOT / "bin/agent-treehouse"), "reap", token],
                       cwd="/", env=env, check=True, timeout=60)
        assert records(env, token)[-1]["action"] == "returned", records(env, token)
        assert Path(lease["path"]).is_dir()
        assert git("show-ref", "--verify", "refs/heads/legacy/preserve")
    print("PASS: Outstanding Treehouse records retain their original guarded return handler.")


if __name__ == "__main__":
    codex_workflow()
    claude_workflow()
    if os.environ.get("AGENT_WORKTREE_TEST_LEGACY") == "1":
        legacy_workflow()
    lost_response_workflow()
    lost_response_workflow(uncertain=True)
