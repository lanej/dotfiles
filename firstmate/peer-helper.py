#!/usr/bin/env python3
"""Durable messages to existing peers; never creates or owns an agent."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path.home() / ".local/share/firstmate-peer"
ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$")


def run(argv, text=None, env=None, strip=True):
    result = subprocess.run(argv, input=text, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=20)
    if result.returncode:
        raise RuntimeError("{} failed: {}".format(argv[0], result.stderr[-1000:]))
    return result.stdout.strip() if strip else result.stdout


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(value, output)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, str(path))
        directory = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def api(request):
    paths = [str(Path.home() / ".local/bin")]
    versions = list((Path.home() / ".nvm/versions/node").glob("v*/bin"))
    versions.sort(key=lambda path: tuple(int(part) for part in path.parent.name.lstrip("v").split(".") if part.isdigit()), reverse=True)
    paths += [str(path) for path in versions]
    environment = dict(os.environ, PATH=os.pathsep.join(paths + [os.environ.get("PATH", "")]))
    if not shutil.which("paseo", path=environment["PATH"]):
        raise RuntimeError("Paseo CLI is unavailable on this boat; terminal peers remain available")
    node = shutil.which("node", path=environment["PATH"])
    if not node:
        raise RuntimeError("Node is unavailable for this boat's Paseo API")
    return json.loads(run([node, str(ROOT / "paseo.mjs")], json.dumps(request), environment))


def process_rows():
    rows = {}
    for line in run(["ps", "-axo", "pid=,ppid=,stat=,tty=,lstart=,args="]).splitlines():
        fields = line.strip().split(None, 9)
        if len(fields) == 10:
            rows[int(fields[0])] = {"parent": int(fields[1]), "foreground": "+" in fields[2],
                                   "tty": fields[3], "started": " ".join(fields[4:9]), "command": fields[9]}
    return rows


def harness(command):
    try:
        args = shlex.split(command)
    except ValueError:
        return None
    if not args:
        return None
    binary = Path(args[0]).name
    if binary in ("claude", "codex", "pi"):
        return binary
    if binary == "node" and len(args) > 1:
        script = str(Path(args[1]).resolve())
        if "/pi-coding-agent/" in script or script.endswith("/pi/dist/cli.js"):
            return "pi"
        if script.endswith("/@openai/codex/bin/codex.js"):
            return "codex"
        if script.endswith("/@anthropic-ai/claude-code/cli.js"):
            return "claude"
    return None


def tmux_inventory():
    if not shutil.which("tmux"):
        return []
    try:
        panes = run(["tmux", "list-panes", "-a", "-F", "#{session_id}\t#{session_name}\t#{pane_id}\t#{pane_pid}\t#{pane_current_path}\t#{pane_current_command}"])
    except RuntimeError as error:
        if "no server running" in str(error) or "No such file" in str(error):
            return []
        raise
    processes = process_rows()
    peers = []
    for line in panes.splitlines():
        session, name, pane, pid, cwd, foreground_command = line.split("\t", 5)
        descendants = {int(pid)}
        for _ in range(len(processes)):
            additions = {child for child, row in processes.items() if row["parent"] in descendants}
            if additions <= descendants:
                break
            descendants |= additions
        agents = [(child, harness(processes[child]["command"])) for child in descendants if child in processes
                  and processes[child]["foreground"] and processes[child]["tty"] not in ("?", "??")
                  and processes[child]["tty"] == processes.get(int(pid), {}).get("tty")
                  and harness(processes[child]["command"])]
        # WHY: A launcher and its native child may name the same harness; bind the deepest process.
        agents = [(child, kind) for child, kind in agents if not any(processes[other]["parent"] == child and kind == other_kind for other, other_kind in agents)]
        supported = len(agents) == 1
        agent_pid, kind = agents[0] if supported else (None, None)
        launcher_pid = None
        if supported:
            binary = Path(shlex.split(processes[agent_pid]["command"])[0]).name
            supported = foreground_command in (kind, binary)
            # WHY: npm's foreground Node launcher can delegate input to its native harness child.
            parent = processes[agent_pid]["parent"]
            if not supported and parent in descendants and parent in processes:
                launcher = processes[parent]
                if (harness(launcher["command"]) == kind and launcher["foreground"]
                        and launcher["tty"] == processes[agent_pid]["tty"]
                        and foreground_command == Path(shlex.split(launcher["command"])[0]).name):
                    supported, launcher_pid = True, parent
        identity = {"session": session, "pane": pane, "pid": int(pid), "cwd": cwd,
                    "process": processes.get(int(pid)), "agentPid": agent_pid,
                    "agent": processes.get(agent_pid), "foregroundCommand": foreground_command,
                    "launcherPid": launcher_pid, "launcher": processes.get(launcher_pid)}
        peers.append({"endpoint": "tmux:{}:{}".format(session, pane), "identity": identity,
                      "title": name, "harness": kind, "supported": supported,
                      "parentProcess": processes.get(processes.get(agent_pid, {}).get("parent")),
                      "reason": None if supported else "No unambiguous supported live harness"})
    return peers


def zellij_inventory():
    if not shutil.which("zellij"):
        return []
    result = []
    for line in run(["zellij", "list-sessions", "--short", "--no-formatting"]).splitlines():
        if "EXITED" in line or not re.match(r"^[a-zA-Z0-9_.-]+$", line):
            continue
        panes = json.loads(run(["zellij", "--session", line, "action", "list-panes", "--json"]))
        for pane in panes:
            if pane.get("is_plugin"):
                continue
            result.append({"endpoint": "zellij:{}:{}".format(line, pane["id"]), "identity": pane,
                           "title": pane.get("pane_title"), "supported": False,
                           "reason": "Zellij inventory lacks a verified live harness PID; messaging is unavailable"})
    return result


def inventory():
    peers, errors = [], []
    for name, adapter in (("tmux", tmux_inventory), ("zellij", zellij_inventory), ("paseo", lambda: api({"action": "list"}))):
        try:
            peers.extend(adapter())
        except Exception as error:
            errors.append({"transport": name, "error": str(error)})
    return {"peers": peers, "errors": errors}


def screen(endpoint):
    pane = endpoint.split(":")[-1]
    rendered = run(["tmux", "capture-pane", "-ep", "-t", pane], strip=False)
    cursor = run(["tmux", "display-message", "-p", "-t", pane, "#{cursor_x}\t#{cursor_y}"])
    return {"rendered": rendered, "cursor": cursor}


def empty_prompt(view, kind):
    text = re.sub(r"\x1b\[[0-9;]*m", "", view["rendered"])
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    # FIX: Require an empty supported input prompt and reject active-turn indicators.
    recent = "\n".join(lines[-12:])
    if re.search(r"esc to (interrupt|cancel)|Thinking|Working|ctrl.c to interrupt", recent, re.I):
        return False
    patterns = {"claude": r"^[❯>] ?$", "codex": r"^[›>] ?$", "pi": r"^[❯>] ?$"}
    prompts = [(at, line) for at, line in enumerate(lines) if re.match(r"^[❯›>]", line)]
    if not prompts:
        return False
    at, prompt = prompts[-1]
    footer = lines[at + 1:]
    if kind == "codex" and prompt == "› Ask Codex to do anything":
        rows = text.splitlines()
        row = next((number for number in range(len(rows) - 1, -1, -1)
                    if rows[number].strip() == prompt), None)
        ansi_row = view["rendered"].splitlines()[row] if row is not None else ""
        # WHY: Codex's dim placeholder is empty only with the input cursor at its start.
        known_footer = (
            len(footer) == 2 and bool(re.match(r"^← for agents · \? for shortcuts(?:\s+⚠ \d+ warnings? · f2 to view)?$", footer[-1]))
            or len(footer) == 1 and bool(re.match(r"^.+ · Main \[default\] · ← for agents(?:\s+⚠ \d+ warnings? · f2 to view)?$", footer[0]))
        )
        return (view["cursor"] == "2\t{}".format(row)
                and "\x1b[2mAsk Codex to do anything" in ansi_row and known_footer)
    return bool(re.match(patterns.get(kind, r"(?!)"), prompt)) and all(
        re.match(r"^[─━│└┘╰╯]+$|^\? for shortcuts$|^\d+% context left(?: · \? for shortcuts)?$", line)
        for line in footer)


def same_identity(left, right):
    # COMPAT: An early inventory included this diagnostic in the identity; all binding fields still match.
    return ({key: value for key, value in left.items() if key != "parentProcess"}
            == {key: value for key, value in right.items() if key != "parentProcess"})


def advance(record, path):
    if record["state"] in ("replied", "failed"):
        return record
    if record["endpoint"].startswith("paseo:"):
        action = "submit" if record["state"] == "queued" else "status"
        if action == "submit":
            record["state"] = "unknown"
            save(path, record)
        try:
            observed = api(dict(record, action=action))
            record.update(observed)
        except Exception as error:
            record["error"] = str(error)
        save(path, record)
        return record
    if record["state"] != "queued":
        return record
    peers = tmux_inventory()
    matches = [peer for peer in peers if peer["endpoint"] == record["endpoint"]]
    if len(matches) != 1 or not same_identity(matches[0]["identity"], record["identity"]) or not matches[0]["supported"]:
        record.update(state="failed", error="Terminal identity changed before submission")
        save(path, record)
        return record
    peer = matches[0]
    view = screen(record["endpoint"])
    fingerprint = hashlib.sha256(json.dumps(view, sort_keys=True).encode()).hexdigest()
    if not empty_prompt(view, peer["harness"]) or record.get("idleScreen") != fingerprint:
        record["idleScreen"] = fingerprint if empty_prompt(view, peer["harness"]) else None
        save(path, record)
        return record
    # WHY: Persist uncertainty before either terminal write. An interrupted paste must never be replayed.
    record["state"] = "unknown"
    save(path, record)
    try:
        current = [item for item in tmux_inventory() if item["endpoint"] == record["endpoint"]]
        if len(current) != 1 or not same_identity(current[0]["identity"], record["identity"]) or screen(record["endpoint"]) != view:
            record.update(state="failed", error="Terminal changed during submission preflight")
        else:
            buffer_name = "firstmate-peer-" + record["id"]
            run(["tmux", "load-buffer", "-b", buffer_name, "-"], record["prompt"])
            run(["tmux", "paste-buffer", "-p", "-d", "-b", buffer_name, "-t", record["identity"]["pane"]])
            run(["tmux", "send-keys", "-t", record["identity"]["pane"], "Enter"])
            record["state"] = "submitted"
    except Exception as error:
        record["error"] = str(error)
    save(path, record)
    return record


def handle(request):
    action = request["action"]
    if action == "list":
        return inventory()
    identifier = request.get("id", "")
    if not ID.match(identifier):
        raise ValueError("Invalid peer request ID")
    path = ROOT / "requests" / (identifier + ".json")
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(str(ROOT / "requests.lock"), "a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        previous = json.loads(path.read_text()) if path.exists() else None
        if action == "reply":
            if previous is None:
                raise ValueError("Unknown peer request")
            body = request.get("body", "")
            if not isinstance(body, str) or not body.strip() or len(body) > 60000:
                raise ValueError("Reply requires 1..60000 characters")
            if previous.get("reply") is not None and previous["reply"] != body:
                raise ValueError("A different reply is already recorded")
            previous.update(state="replied", reply=body, repliedAt=time.time())
            save(path, previous)
            return previous
        if action == "send":
            if not isinstance(request.get("prompt"), str) or not request["prompt"].strip() or len(request["prompt"]) > 65000:
                raise ValueError("Invalid peer prompt")
            if any(ord(char) < 32 and char not in "\n\t" or ord(char) == 127 for char in request["prompt"]):
                raise ValueError("Terminal control characters are not allowed in peer messages")
            if previous is not None:
                for key in ("endpoint", "identity", "prompt"):
                    if previous[key] != request[key]:
                        raise ValueError("Request ID already has different delivery intent")
            else:
                matches = [peer for peer in inventory()["peers"] if peer["endpoint"] == request["endpoint"]]
                if len(matches) != 1 or not same_identity(matches[0]["identity"], request["identity"]) or not matches[0]["supported"]:
                    raise ValueError("Peer endpoint is unsupported, ambiguous, or changed")
                previous = dict(request, state="queued", createdAt=time.time())
                save(path, previous)
        elif action != "status":
            raise ValueError("Unknown peer operation")
        if previous is None:
            return {"id": identifier, "state": "missing"}
        return advance(previous, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("rpc", "reply", "serve"))
    parser.add_argument("id", nargs="?")
    parser.add_argument("--file", help="Read reply body from this UTF-8 file; otherwise stdin")
    args = parser.parse_args()
    os.umask(0o077)
    if args.command == "serve":
        print('{"ready": true}', flush=True)
        for line in sys.stdin:
            try:
                print(json.dumps(handle(json.loads(line))), flush=True)
            except Exception as error:
                print(json.dumps({"error": str(error)}), flush=True)
        sys.exit(0)
    try:
        request = json.load(sys.stdin) if args.command == "rpc" else {
            "action": "reply", "id": args.id, "body": Path(args.file).read_text() if args.file else sys.stdin.read()}
        print(json.dumps(handle(request)))
    except Exception as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        sys.exit(1)
