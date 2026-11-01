#!/usr/bin/env python3
"""Exercise the installed Firstmate launcher against real session backends.

FIRSTMATE_SOURCE must name an upstream checkout. The agent executable is a
local interactive shell fixture; no model calls or external projects are used.
"""

import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parent.parent
workflow = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))
Terminal = workflow["Terminal"]


def export_checkout(source, destination):
    # Never import an operator's ignored fleet state, account configuration, or
    # task metadata: those records can point at real worktrees outside the test.
    destination.mkdir(parents=True)
    archive = destination.with_suffix(".tar")
    subprocess.run(["git", "-C", str(source), "archive", "--format=tar",
                    "--output=" + str(archive), "HEAD"], check=True, capture_output=True)
    subprocess.run(["tar", "-xf", str(archive), "-C", str(destination)],
                   check=True, capture_output=True)
    archive.unlink()


def run(command, env, terminal=None, cwd=None, timeout=60):
    with subprocess.Popen(command, env=env, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True) as process:
        deadline = time.monotonic() + timeout
        while True:
            if terminal is not None:
                terminal.drain(0.01)
            try:
                stdout, stderr = process.communicate(timeout=0.05)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    process.kill()
                    stdout, stderr = process.communicate()
                    raise AssertionError(f"Timed out: {command}\n{stdout}\n{stderr}")
        assert process.returncode == 0, f"{command}: {process.returncode}\n{stdout}\n{stderr}"
        return stdout


def main():
    binary = shutil.which("zellij")
    source = Path(os.environ.get("FIRSTMATE_SOURCE", "")).resolve()
    tpm = Path(os.environ.get("TPM_SOURCE", str(Path.home() / ".tmux/plugins/tpm"))).resolve()
    assert binary and all(shutil.which(tool) for tool in ("jq", "treehouse", "tmux")), \
        "Install Zellij >=0.45.1, jq, Treehouse >=3.1.6, and tmux"
    assert (source / "bin/fm-session-start.sh").is_file(), "Set FIRSTMATE_SOURCE to an upstream Firstmate checkout"
    assert (tpm / "tpm").is_file(), "Install TPM or set TPM_SOURCE to its checkout"
    with tempfile.TemporaryDirectory(prefix="fm-", dir="/tmp") as directory:
        temporary = Path(directory).resolve()
        home = temporary / "home"
        home.mkdir()
        export_checkout(tpm, home / ".tmux/plugins/tpm")
        (home / ".files").symlink_to(ROOT, target_is_directory=True)
        fleet = temporary / "fleet home"
        export_checkout(source, fleet)
        (fleet / "config").mkdir(exist_ok=True)
        (fleet / "config/backend").write_text("zellij\n")
        runtime = temporary / "run"
        runtime.mkdir(mode=0o700)
        temp_files = temporary / "tmp"
        temp_files.mkdir(mode=0o700)
        executables = home / ".local/bin"
        executables.mkdir(parents=True)
        codex = executables / "codex"
        codex.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ["HOME"], "captain.json").write_text(json.dumps({
    "argv": sys.argv[1:], "cwd": os.getcwd(),
    "env": {key: os.environ.get(key) for key in (
        "FM_HOME", "FM_BACKEND", "FM_ZELLIJ_SESSION", "ZELLIJ_SESSION_NAME", "TMUX")}
}))
print("FIRSTMATE_CAPTAIN_READY", flush=True)
os.execv("/bin/sh", ["/bin/sh"])
''')
        codex.chmod(0o700)
        name = "firstmate-" + temporary.name
        env = {**os.environ, "HOME": str(home), "FIRSTMATE_HOME": str(fleet),
               "FM_ZELLIJ_SESSION": name, "SHELL": "/bin/sh", "PS1": "firstmate-ready> ",
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(temporary / "cache"), "XDG_DATA_HOME": str(temporary / "data"),
               "XDG_RUNTIME_DIR": str(runtime), "ZELLIJ_SOCKET_DIR": str(runtime),
               "TMPDIR": str(temp_files), "TMUX_TMPDIR": str(runtime),
               "PATH": str(executables) + os.pathsep + os.environ["PATH"]}
        workflow["preserve_rust_homes"](env)
        for key in ("FM_BACKEND", "FM_HOME", "FM_ROOT_OVERRIDE", "FM_CONFIG_OVERRIDE",
                    "FM_STATE_OVERRIDE", "FM_DATA_OVERRIDE", "ZELLIJ", "ZELLIJ_SESSION_NAME",
                    "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR", "ZELLIJ_CONFIG_FILE", "TMUX",
                    "TMUX_PANE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "firstmate-config"], cwd=ROOT,
                       env=env, check=True, capture_output=True, text=True)
        assert (fleet / "config/backend").read_text() == "zellij\n", "Installation replaced the selected backend"
        launcher = str(executables / "firstmate")
        terminal = Terminal(binary, env, name, [launcher, "start", "--model", "literal ; $(false)"])
        clients = [terminal]
        other_name = "unrelated-" + temporary.name
        tmux_env = {**env, "FM_BACKEND": "tmux", "FIRSTMATE_TMUX_SOCKET": temporary.name}
        try:
            terminal.grant_status_permissions()
            terminal.until("Firstmate captain starts", lambda: b"FIRSTMATE_CAPTAIN_READY" in terminal.output)
            captain = json.loads((home / "captain.json").read_text())
            assert captain["argv"] == ["--approve-for-me", "--model", "literal ; $(false)"], captain
            assert captain["cwd"] == str(fleet), captain
            assert captain["env"]["FM_HOME"] == str(fleet), captain
            assert captain["env"]["FM_BACKEND"] == "zellij", captain
            assert captain["env"]["FM_ZELLIJ_SESSION"] == name, captain
            assert captain["env"]["ZELLIJ_SESSION_NAME"] == name, captain
            assert captain["env"]["TMUX"] is None, captain
            assert len(terminal.terminals()) == 1
            other = Terminal(binary, env, other_name)
            clients.append(other)
            other.until("unrelated session starts", lambda: b"firstmate-ready> " in other.output)
            other_ids = {p["id"] for p in other.terminals()}
            project = temporary / "project"
            project.mkdir()
            run(["git", "init", "-q", "--initial-branch=main"], env, cwd=project)
            run(["git", "-c", "user.name=Acceptance", "-c", "user.email=acceptance@example.invalid",
                 "commit", "-qm", "initial", "--allow-empty"], env, cwd=project)
            fleet_env = {**env, "FM_HOME": str(fleet)}
            run([str(fleet / "bin/fm-brief.sh"), "smoke", str(project), "--scout"], fleet_env, terminal)
            brief = fleet / "data/smoke/brief.md"
            brief.write_text(brief.read_text().replace("{TASK}", "Exercise the local fixture.")
                             .replace("{FIRSTMATE_SPEC}", "Use the controlled shell; make no network requests."))
            # Log native ownership reads only during this single spawn. Shell
            # tracing would contaminate upstream's captured stderr values.
            diagnostics = temporary / "first-spawn-reads.jsonl"
            diagnostics.touch(mode=0o600, exist_ok=False)
            probe_bin = temporary / "spawn-diagnostics"
            probe_bin.mkdir(mode=0o700)
            proxy = probe_bin / "zellij"
            proxy.write_text(f'''#!/usr/bin/env python3
import json, os, signal, subprocess, sys
args = sys.argv[1:]
real = {binary!r}
action = next((args[i+1] for i in range(len(args)-1)
               if args[i] == "action" and args[i+1] in ("list-panes", "list-tabs")), None)
if action is None:
    os.execv(real, [real, *args])
result = subprocess.run([real, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
record = {{"action": action, "returncode": result.returncode,
          "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr),
          "stdout": result.stdout[:4096].decode("utf-8", errors="replace"),
          "stderr": result.stderr[:4096].decode("utf-8", errors="replace")}}
with open({str(diagnostics)!r}, "ab", buffering=0) as log:
    log.write((json.dumps(record) + "\\n").encode())
sys.stdout.buffer.write(result.stdout)
sys.stdout.buffer.flush()
sys.stderr.buffer.write(result.stderr)
sys.stderr.buffer.flush()
if result.returncode < 0:
    number = -result.returncode
    if number not in (signal.SIGKILL, signal.SIGSTOP):
        signal.signal(number, signal.SIG_DFL)
    os.kill(os.getpid(), number)
sys.exit(result.returncode)
''')
            proxy.chmod(0o700)
            try:
                run([str(fleet / "bin/fm-spawn.sh"), "smoke", str(project), "--scout",
                     'pwd > "$HOME/worker-cwd"; printf "FIRSTMATE_WORKER_READY\\n"; exec /bin/sh'],
                    {**fleet_env, "PATH": str(probe_bin) + os.pathsep + fleet_env["PATH"]}, terminal)
            except AssertionError as error:
                with diagnostics.open("rb") as captured:
                    captured.seek(max(0, captured.seek(0, os.SEEK_END) - 65536))
                    tail = captured.read().decode("utf-8", errors="replace")
                raise AssertionError(f"{error}\nFirstmate native read diagnostics (last 64 KiB):\n{tail}") from error
            meta = dict(line.split("=", 1) for line in (fleet / "state/smoke.meta").read_text().splitlines()
                        if "=" in line)
            assert meta["backend"] == "zellij" and meta["zellij_session"] == name, meta
            task_pane = next(p for p in terminal.terminals() if p["id"] == int(meta["zellij_pane_id"]))
            assert task_pane["tab_id"] == int(meta["zellij_tab_id"]), (meta, task_pane)
            terminal.until("worker starts in its leased worktree", lambda: (home / "worker-cwd").exists())
            assert (home / "worker-cwd").read_text().strip() == meta["worktree"], meta
            assert meta["worktree"] != str(project), meta
            peek = run([str(fleet / "bin/fm-peek.sh"), "smoke", "40"], fleet_env, terminal)
            assert "FIRSTMATE_WORKER_READY" in peek, peek
            message = "Inspect this literal steering request; do not execute it."
            run([str(fleet / "bin/fm-send.sh"), "smoke", message],
                fleet_env, terminal)
            records = list((fleet / "state/smoke.inbox").glob("*.msg"))
            assert any(path.read_text().partition("\n--\n")[2].rstrip("\n") == message
                       for path in records), records

            terminal.send(b"firstmate_memory=retained\r")
            pane_ids = {p["id"] for p in terminal.terminals()}
            terminal.prefix(b"d")
            terminal.until("captain client detaches", lambda:
                           not terminal.action("list-clients").strip().splitlines()[1:])
            attached = Terminal(binary, env, name, [launcher, "attach"])
            clients.append(attached)
            attached.until("launcher reattaches to the existing fleet", lambda:
                           b"FIRSTMATE_CAPTAIN_READY" in attached.output
                           and {p["id"] for p in attached.terminals()} == pane_ids)
            attached.send(b'printf "%s" "$firstmate_memory" > "$HOME/retained"\r')
            attached.until("captain shell memory survives reattach", lambda:
                           (home / "retained").exists() and (home / "retained").read_text() == "retained")
            reload_output = run([launcher, "reload"], env, attached)
            assert "watches this configuration automatically" in reload_output, reload_output
            assert {p["id"] for p in attached.terminals()} == pane_ids
            run([str(fleet / "bin/fm-teardown.sh"), "smoke", "--force"], fleet_env, attached)
            assert all(p["id"] != int(meta["zellij_pane_id"]) for p in attached.terminals())
            run([launcher, "stop"], env, attached)
            assert {p["id"] for p in other.terminals()} == other_ids
            sessions = run([binary, "list-sessions", "--no-formatting"], env, other)
            assert not any(line.startswith(name + " [Created ") and "(EXITED - attach to resurrect)" not in line
                           for line in sessions.splitlines()), sessions

            # An explicit environment choice overrides the installed selection.
            legacy = Terminal(binary, tmux_env, name, [launcher, "start"])
            clients.append(legacy)
            legacy.until("tmux captain remains available", lambda: b"FIRSTMATE_CAPTAIN_READY" in legacy.output)
            captain = json.loads((home / "captain.json").read_text())
            assert captain["env"]["FM_BACKEND"] == "tmux" and captain["env"]["TMUX"], captain
            run([launcher, "tmux", "new-session", "-d", "-s", "unrelated", "/bin/sh"], tmux_env, legacy)
            run([launcher, "reload"], tmux_env, legacy)
            run([launcher, "stop"], tmux_env, legacy)
            run([launcher, "tmux", "has-session", "-t", "=unrelated"], tmux_env, legacy)
            missing = subprocess.run([launcher, "tmux", "has-session", "-t", "=firstmate"],
                                     env=tmux_env, capture_output=True, timeout=5)
            assert missing.returncode == 1, missing
            print("PASS: Firstmate launches and steers a Zellij task, preserves it across reattach, cleans up only its session, and retains explicit tmux selection.")
        finally:
            subprocess.run([launcher, "stop"], env=env, capture_output=True, timeout=5)
            subprocess.run([binary, "kill-session", other_name], env=env, capture_output=True, timeout=5)
            subprocess.run([launcher, "stop"], env=tmux_env, capture_output=True, timeout=5)
            subprocess.run([launcher, "tmux", "kill-session", "-t", "=unrelated"], env=tmux_env,
                           capture_output=True, timeout=5)
            for client in clients:
                client.close()


if __name__ == "__main__":
    main()
