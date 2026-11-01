#!/usr/bin/env python3
"""Exercise installed hooks, broker ownership, bar and triage in real Zellij.

The named Claude/Codex fixtures are local hook producers, not model clients.
No account, prompts or model calls are used. Requires the Zellij-enabled broker
source checkout in AGENT_STATUS_SOURCE and Go, Rust, Zellij and fzf on PATH.
"""

import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time

workflow = importlib.import_module("test-zellij")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT

CLIENT = r'''
package main
import ("bufio"; "bytes"; "encoding/json"; "fmt"; "os"; "os/exec"; "path/filepath"; "strings"; "time")
func main() {
    provider := filepath.Base(os.Args[0]); session := os.Args[1]
    fmt.Printf("\033]2;%s | %s\007", provider, session)
    send := func(kind string) {
        if kind == "UserPromptSubmit" { fmt.Printf("\033]2;%s | %s\007", provider, session) }
        hook := "codex-tmux-state-hook"
        if provider == "claude" { hook = "claude-tmux-state-hook"; if kind == "SessionStart" { hook = "claude-session-start-hook" } }
        cwd, _ := os.Getwd()
        data, _ := json.Marshal(map[string]string{"session_id":session, "hook_event_name":kind,
            "source":"startup", "cwd":cwd, "tool_name":"AskUserQuestion", "tool_use_id":"question"})
        cmd := exec.Command(filepath.Join(os.Getenv("HOME"), ".files", "bin", hook)); cmd.Stdin = bytes.NewReader(data)
        if provider == "codex" {
            // A shared app-server can predate the terminal client and carry no
            // current mux hints. Native pane identity must choose the sink.
            for _, entry := range os.Environ() {
                key := strings.SplitN(entry, "=", 2)[0]
                if key != "ZELLIJ" && key != "ZELLIJ_SESSION_NAME" && key != "ZELLIJ_PANE_ID" && key != "TMUX" && key != "TMUX_PANE" {
                    cmd.Env = append(cmd.Env, entry)
                }
            }
        }
        start := time.Now(); _ = cmd.Run()
        _ = os.WriteFile(filepath.Join(os.Getenv("HOME"), session+"-hook"), []byte(fmt.Sprint(time.Since(start).Milliseconds())), 0600)
    }
    send("SessionStart"); fmt.Println("agent-ready")
    reader := bufio.NewScanner(os.Stdin)
    for reader.Scan() {
        kind := strings.TrimSpace(reader.Text()); if kind == "exit" { send("SessionEnd"); return }
        if kind == "NativeApproval" {
            fmt.Printf("\033]2;[ ! ] Action Required | %s | %s\007", provider, session)
            fmt.Println("title-updated"); continue
        }
        send(kind); fmt.Println("hook-done:"+kind)
    }
}
'''


def main():
    source = os.environ.get("AGENT_STATUS_SOURCE")
    assert source and (Path(source) / "go.mod").exists(), "Set AGENT_STATUS_SOURCE to the Zellij-enabled broker checkout"
    for name in ("zellij", "fzf", "go", "cargo"):
        assert shutil.which(name), f"Install {name} before the broker workflow"
    with tempfile.TemporaryDirectory(prefix="zj-status-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / "home", work / "run", work / "tmp"
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temporary),
               "AGENT_STATUS_SOCKET": str(home / ".local/state/agent-status/broker.sock"),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        # Keep build caches outside the disposable HOME; application state and
        # all running sessions still remain private to this one workflow.
        for cache in ("GOCACHE", "GOMODCACHE"):
            env[cache] = subprocess.check_output(["go", "env", cache], text=True).strip()
        workflow.preserve_rust_homes(env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR", "ZELLIJ_CONFIG_FILE",
                    "TMUX", "TMUX_PANE", "AGENT_STATUS_BIN", "FZF_DEFAULT_OPTS", "FZF_DEFAULT_OPTS_FILE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        (home / ".files").symlink_to(ROOT)
        subprocess.run(["make", "--no-print-directory", "zellij", "agent-status-broker"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        client = work / "client.go"
        client.write_text(CLIENT)
        executable = work / "claude"
        subprocess.run(["go", "build", "-o", str(executable), str(client)], env=env, check=True,
                       capture_output=True, text=True)
        shutil.copyfile(executable, work / "codex")
        (work / "codex").chmod(0o755)
        broker_path = home / ".local/lib/agent-status/agent-status-broker"
        broker_log = (work / "broker.log").open("w+")
        broker = subprocess.Popen([str(broker_path), "serve", "--codex-socket", ""], env=env,
                                  stdout=broker_log, stderr=broker_log)
        first, second = "status-" + work.name, "other-" + work.name
        clients = []
        try:
            terminal = Terminal(shutil.which("zellij"), env, first)
            clients.append(terminal)
            terminal.grant_status_permissions()
            terminal.until("shell ready", lambda: PROMPT in terminal.output and len(terminal.terminals()) == 1)
            claude_id = "11111111-1111-1111-1111-111111111111"
            codex_id = "22222222-2222-2222-2222-222222222222"
            replacement_id = "33333333-3333-3333-3333-333333333333"
            terminal.send((shlex.join([str(executable), claude_id]) + "\r").encode())
            terminal.until("Claude hook producer ready", lambda: "agent-ready" in terminal.action("dump-screen"))

            def records():
                result = subprocess.run([str(broker_path), "zellij-view"], env=env, check=True,
                                        capture_output=True, text=True, timeout=3)
                return json.loads(result.stdout)["records"]

            terminal.until("Claude is bound by the installed SessionStart hook", lambda:
                           any(r["session_id"] == claude_id for r in records()))
            claude_pane = terminal.terminals()[0]["id"]
            terminal.send(b"PreToolUse\r")
            terminal.until("Claude needs an answer", lambda:
                           any(r["session_id"] == claude_id and r["state"] == "question" for r in records()))
            other = Terminal(shutil.which("zellij"), env, second)
            clients.append(other)
            other.until("second session shell ready", lambda: PROMPT in other.output and len(other.terminals()) == 1)
            other.send((shlex.join([str(work / "codex"), codex_id]) + "\r").encode())
            other.until("Codex hook producer ready", lambda: "agent-ready" in other.action("dump-screen"))
            other.send(b"UserPromptSubmit\r")
            other.until("concurrent identities in separate sessions", lambda:
                        len(records()) == 2 and any(r["session_id"] == codex_id and r["state"] == "thinking" for r in records()))
            codex_pane = other.terminals()[0]["id"]
            # Keep a second native tab ready before the session is detached;
            # stable 0.45.1 cannot size a brand-new tab with zero clients.
            other.prefix(b"c")
            other.until("spare tab opens", lambda: len(other.tabs()) == 2)
            spare_tab = str(next(t["tab_id"] for t in other.tabs() if t["active"]))
            spare_pane = next(p["id"] for p in other.terminals() if p["tab_id"] == int(spare_tab))
            other.send(b'touch "$HOME/spare-ready"\r')
            other.until("spare tab shell accepts input", lambda: (home / "spare-ready").exists())
            other.send((shlex.join([str(work / "codex"), replacement_id]) + "\r").encode())
            other.until("a second tab has its own live agent", lambda:
                        any(r["session_id"] == replacement_id for r in records()))
            other.prefix(b"0")
            assert all(int((home / (identity + "-hook")).read_text()) < 500 for identity in (claude_id, codex_id))
            before = {r["session_id"]: (r["root_pid"], r["client_pid"]) for r in records()}
            # A fresh query from another session must include an unfocused
            # Claude question and the separate Codex work record.
            other.until("bar shows cross-session attention", lambda:
                        b"!1" in other.output and b"\xe2\x97\x8f1" in other.output)
            if capture := os.environ.get("ZELLIJ_STATUS_CAPTURE"):
                Path(capture).write_bytes(other.output)
            broker.terminate()
            broker.wait(timeout=5)
            unavailable = subprocess.run([str(home / ".local/bin/zellij-status"), "records"], env=env,
                                         capture_output=True, text=True, timeout=4)
            assert unavailable.returncode != 0, "Stopped broker must not advertise old records as healthy"
            broker = subprocess.Popen([str(broker_path), "serve", "--codex-socket", ""], env=env,
                                      stdout=broker_log, stderr=broker_log)
            other.until("restart discards old reduced activity", lambda: records() == [])
            # Keep both clients alive. Ordinary hooks must recover their status
            # without a new Claude SessionStart or replaying the idle spare tab.
            terminal.send(b"UserPromptSubmit\rPreToolUse\r")
            other.send(b"UserPromptSubmit\r")
            other.until("fresh hooks restore the live Claude question and Codex work", lambda:
                        {r["session_id"]: r["state"] for r in records()}
                        == {claude_id: "question", codex_id: "thinking"})
            recovered = {r["session_id"]: (r["root_pid"], r["client_pid"]) for r in records()}
            assert recovered == {identity: before[identity] for identity in (claude_id, codex_id)}
            before = recovered
            other.prefix(b"\x01")
            def triage_ready():
                pane = next((p for p in other.terminals() if p["is_floating"]), None)
                return pane and "Attention" in other.action("dump-screen", "--pane-id", f"terminal_{pane['id']}")
            other.until("attention picker renders", triage_ready)
            other.send(b"\r")
            other.until("triage switches to the question's session", lambda:
                        len(other.action("list-clients", session=first).strip().splitlines()) >= 3)
            other.until("triage focuses the original Claude pane", lambda:
                        any(not p["is_plugin"] and p["id"] == claude_pane and p["is_focused"] for p in other.panes(session=first)))
            assert {r["session_id"]: (r["root_pid"], r["client_pid"]) for r in records()} == before
            # Exit clears only the departed conversation; an unchanged shell
            # root and pane ID must not keep its former client's status alive.
            other.send(b"exit\r")
            other.until("Claude exit clears its record", lambda:
                        {r["session_id"] for r in records()} == {codex_id})
            stale = json.dumps({"hook_event_name": "SessionStart", "session_id": claude_id,
                                "source": "startup", "cwd": str(home)})
            other.send(("printf %s " + shlex.quote(stale) + ' | "$HOME/.files/bin/claude-session-start-hook"; touch "$HOME/stale-sent"\r').encode())
            other.until("an abandoned shell cannot claim the old conversation", lambda: (home / "stale-sent").exists())
            assert {r["session_id"] for r in records()} == {codex_id}
            # The Codex session has no attached clients after triage. Its
            # background bar must still publish a changed native title.
            assert not other.action("list-clients", session=second).strip().splitlines()[1:]
            other.action("paste", "--pane-id", f"terminal_{codex_pane}", "PermissionRequest\n", session=second)
            other.until("detached Codex waits for native approval evidence", lambda:
                        len(records()) == 1 and records()[0]["state"] == "waiting")
            other.action("paste", "--pane-id", f"terminal_{codex_pane}", "NativeApproval\n", session=second)
            other.until("a detached session still publishes native approval", lambda:
                        len(records()) == 1 and records()[0]["state"] == "approval")
            old_tab = records()[0]["tab_id"]
            before_panes = {p["id"] for p in other.panes(session=second) if not p["is_plugin"]}
            shell_pid = home / "detached-shell-pid"
            reply = other.action("new-pane", "--tab-id", spare_tab, "--", "/bin/sh", "-c",
                                 'printf "%s\\n" "$$" > "$HOME/detached-shell-pid"; '
                                 f'PS1={shlex.quote(PROMPT.decode())} exec /bin/sh',
                                 session=second).strip()
            # Native 0.45.1 can return success with no ID when its one-second
            # action acknowledgement expires. Require the actual new running
            # pane and shell identity before asking whether the broker found it.
            def new_live_pane():
                panes = [p for p in other.panes(session=second)
                         if not p["is_plugin"] and p["id"] not in before_panes]
                if len(panes) != 1 or panes[0]["tab_id"] != int(spare_tab):
                    return None
                pane = panes[0]
                if pane["exited"] or pane["is_held"] or not shell_pid.exists():
                    return None
                if PROMPT.decode().strip() not in other.action(
                        "dump-screen", "--pane-id", f"terminal_{pane['id']}", session=second):
                    return None
                pid = int(shell_pid.read_text().strip())
                os.kill(pid, 0)
                return pane["id"], pid
            created, created_pid = other.until("one new live pane appears in the detached target tab", new_live_pane)
            assert not reply or reply == f"terminal_{created}", f"Unexpected pane acknowledgement: {reply!r}"
            def discovered():
                state = json.loads((home / ".local/state/agent-status/zellij/state.json").read_text())
                return any(p["pane"] == created and p["root_pid"] == created_pid
                           and p["tab_id"] == int(spare_tab)
                           for manifest in state["manifests"].values() if manifest["session"] == second
                           for p in manifest["panes"])
            other.until("broker discovers a new native pane while detached", discovered)
            other.action("close-tab", "--tab-id", str(old_tab), session=second)
            other.action("paste", "--pane-id", f"terminal_{spare_pane}", "UserPromptSubmit\nPermissionRequest\nNativeApproval\n", session=second)
            other.until("a surviving bar takes over after the detached leader tab closes", lambda:
                        len(records()) == 1 and records()[0]["session_id"] == replacement_id
                        and records()[0]["state"] == "approval")
            print("PASS: installed hooks bind concurrent identities without Codex mux hints, recover live Claude/Codex status after broker restart, triage without restarting processes, clear exited owners, and refresh detached sessions.")
        except Exception:
            broker_log.flush()
            broker_log.seek(0)
            print("Broker log:", broker_log.read())
            state = home / ".local/state/agent-status/zellij/state.json"
            if state.exists():
                print("Fixture status state:", state.read_text())
            raise
        finally:
            for name in (first, second):
                subprocess.run(["zellij", "kill-session", name], env=env, capture_output=True, timeout=5)
            for terminal in clients:
                terminal.close()
            broker.terminate()
            broker.wait(timeout=5)
            broker_log.close()


if __name__ == "__main__":
    main()
