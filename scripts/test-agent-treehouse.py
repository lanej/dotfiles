#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets==15.0.1", "psutil==7.2.2"]
# ///
"""Exercise each shell entrypoint against native Treehouse, real Git, and lsof."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import select
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
    treehouse = shutil.which("treehouse")
    assert treehouse, "install Treehouse before running this detector"
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
               "TREEHOUSE_TEST_REAL": treehouse, "AGENT_TEST_LOG": str(folder / "agent.json"),
               "TREEHOUSE_TEST_LOG": str(folder / "treehouse.jsonl"),
               "UV_CACHE_DIR": subprocess.check_output(["uv", "cache", "dir"], text=True).strip()}
        for key in tuple(env):
            if key.startswith(("TREEHOUSE_", "AGENT_TREEHOUSE_", "CLAUDE_CODE_", "FM_")) and not key.startswith("TREEHOUSE_TEST_"):
                env.pop(key)
        env["TREEHOUSE_NO_UPDATE_CHECK"] = "1"
        wrapper = bins / "treehouse"
        wrapper.write_text("#!" + sys.executable + "\n" + '''
import json, os, sys
with open(os.environ["TREEHOUSE_TEST_LOG"], "a") as out:
    out.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1] == "get" and os.environ.get("AGENT_TEST_MODE") == "failure":
    print("requested allocation failure", file=sys.stderr)
    sys.exit(23)
args = [os.environ["TREEHOUSE_TEST_REAL"], *sys.argv[1:]]
if sys.argv[1] == "get":
    args.append("--no-fetch")
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
        subprocess.run([sys.executable, str(ROOT / "bin/agent-treehouse"), "reap", path.stem],
                       env=env, cwd="/", check=True, timeout=45)


def codex_workflow():
    with fixture("codex") as (folder, project, env, git, sessions):
        args = ["exec", "--worktree", "--cd", str(project / "subdirectory"),
                "-c", 'custom="space and $dollar"', "--json", "quoted prompt ; $(false)"]
        result = launch("codex", project, env, args)
        assert result.returncode == 7, result.stderr
        observed = json.loads((folder / "agent.json").read_text())
        root = Path(observed["cwd"]).parent
        assert root != project and ".treehouse" in root.parts
        assert observed["args"][2:] == ["exec", "-c", 'custom="space and $dollar"',
                                        "--json", "quoted prompt ; $(false)"], observed
        wait_for(lambda: records(env))
        assert records(env)[-1]["action"] == "returned", records(env)
        branch = git("for-each-ref", "--format=%(refname)", "refs/heads/feature/")
        assert git("rev-parse", branch) == observed["head"]
        assert root.is_dir(), "native Treehouse pool directory was deleted"

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
        assert records(env)[-1]["action"] == "returned", records(env)

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
            assert records(env, session)[-1]["action"] == "returned", records(env)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)

        env["AGENT_TEST_MODE"] = "assigned"
        (folder / "bin/treehouse").unlink()
        native_bins = folder / "native"
        native_bins.mkdir()
        for name in ("python3", "git", "bash", "uname", "dirname"):
            (native_bins / name).symlink_to(shutil.which(name))
        (native_bins / "codex").symlink_to(folder / "bin/codex")
        env["PATH"] = str(native_bins)
        result = launch("codex", project, env, ["exec", "--worktree", "native fallback"])
        assert result.returncode == 7, result
        assert json.loads((folder / "agent.json").read_text())["args"] == ["exec", "--worktree", "native fallback"]
    print("PASS: Codex shell request uses Treehouse, preserves arguments/branches, fails closed, and retains shared work.")


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
        assert root != project and ".treehouse" in root.parts
        wait_for(lambda: records(env))
        assert records(env)[-1]["action"] == "returned", records(env)
        branch = git("for-each-ref", "--format=%(refname)", "refs/heads/feature/")
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
        assert records(env)[-1]["action"] == "returned", records(env)

        env["AGENT_TEST_MODE"] = "subagent"
        result = launch("claude", project, env, args)
        assert result.returncode == 7, result
        observed = json.loads((folder / "agent.json").read_text())
        assert observed["subagent"] != observed["cwd"], observed
        wait_for(lambda: len(records(env, observed["session"])) == 2)
        assert all(row["action"] == "returned" for row in records(env, observed["session"])), records(env)

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
        assert result.returncode == 7, result
        assert json.loads((folder / "agent.json").read_text())["args"] == ["--worktree", "-p", "native fallback"]
    print("PASS: Claude factory hooks preserve settings, return clean leases, and retain concurrent work.")


if __name__ == "__main__":
    codex_workflow()
    claude_workflow()
