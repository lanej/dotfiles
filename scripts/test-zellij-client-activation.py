#!/usr/bin/env python3
"""Prove native managed TTY continuity, focus and private input across replacement."""

import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
fixture = runpy.run_path(str(ROOT / "scripts/test-zellij-managed-activation.py"))
command, wait, Terminal, API = (fixture[key] for key in ("command", "wait", "Terminal", "API"))


def native_client(client, action="inventory", **arguments):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(client["socket"])
        connection.sendall((json.dumps({"action": action, **arguments}) + "\n").encode())
        reply = bytearray()
        while b"\n" not in reply:
            reply.extend(connection.recv(4096))
    result = json.loads(reply.split(b"\n", 1)[0])
    if not result.get("error"):
        assert result["process"] == client["process"], result
    return result


def ingress_settled(client):
    value = native_client(client)
    authority = value["input_authority"]
    return (value if authority["reader_verified"] and not authority["parser_partial"]
            and all(authority[key] == 0 for key in
                    ("reader_pending", "queued_input", "parser_busy", "pending_input")) else None)


def checkpoint_request(client, server, directory, runtime):
    return {
        "expected_process": client["process"], "run_id": directory.name,
        "server_identity": json.loads(server["process"]["native_id"]),
        "server_process": server["process"], "baseline_display": client["display"],
        "operation_directory": str(directory), "replacement_path": str(runtime),
        "replacement_sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
        "focus": client["focus"], "defer_to_parent": False,
    }


def challenge_parser(terminal, client, server, base, runtime):
    """Challenge actual parser state, including the empty-buffer open-paste case."""
    terminal.send(b"\x1b")
    wait(lambda: ingress_settled(client))
    for prefix, suffix in ((b"", b""), (b"\x1b[97;", b"2u"),
                           (b"\x1b[200~", b"\x1b[201~")):
        directory = base / str(uuid.uuid4())
        directory.mkdir(mode=0o700)
        request = checkpoint_request(client, server, directory, runtime)
        if prefix:
            terminal.send(prefix)
            wait(lambda: native_client(client)["input_authority"]["parser_partial"])
            refused = native_client(client, "checkpoint", **request)
            assert "unsettled" in refused.get("error", ""), refused
            assert os.waitpid(terminal.pid, os.WNOHANG)[0] == 0
            terminal.send(suffix)
            wait(lambda: ingress_settled(client))
        confirmed = native_client(client, "checkpoint", **request)
        assert confirmed["checkpoint"] == {"state": "confirmed", "run_id": directory.name}, confirmed
        released = native_client(client, "release_original",
                                 expected_process=client["process"], run_id=directory.name)
        assert released["checkpoint"] is None, released
    print("Real lone Escape settles; split Kitty CSI and open bracketed paste refuse checkpoint until natural completion.", flush=True)


def challenge_retention_failure(mode, terminal, client, original, operation, activation):
    path = operation / f"zellij-client-{client['process']['native_id']}.json"
    if mode == "--durability-failure":
        path.rename(path.with_suffix(".retained-original"))
        path.mkdir(mode=0o700)  # Force the real private atomic checkpoint rename to fail.
        terminal.send(b"durability-error-owned-input")
        failed = wait(lambda: (value if (value := native_client(client)).get("input_retention_error") else None))
        candidates = [json.loads(file.read_text()) for file in operation.glob(".client-*")]
        assert any(b"durability-error-owned-input" in b"".join(bytes(chunk) for chunk in value.get("recoverable_input", []))
                   for value in candidates), "Already-read bytes must survive the failed final rename in the private durable temporary"
    else:
        written = 0
        payload = b"\xff" * 65536
        os.set_blocking(terminal.fd, False)
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline:
                failed = native_client(client)
                if failed.get("input_retention_error"):
                    break
                try:
                    written += os.write(terminal.fd, payload)
                except BlockingIOError:
                    pass
                terminal.drain(0.01)
            else:
                raise AssertionError("Large real paste did not reach the bounded durable-ingress refusal")
        finally:
            os.set_blocking(terminal.fd, True)
        retained = json.loads(path.read_text())
        consumed = sum(len(chunk) for chunk in retained["recoverable_input"])
        assert written > consumed > 0, (written, consumed)
        assert path.stat().st_size <= 3 * 1024 * 1024 + 1
    assert failed["process"] == client["process"] and os.waitpid(terminal.pid, os.WNOHANG)[0] == 0
    assert failed["input_authority"]["reader_pending"] == failed["input_authority"]["queued_input"] == 0
    time.sleep(0.1)
    assert native_client(client)["input_retention_error"] == failed["input_retention_error"]
    refused = json.loads(command([sys.executable, str(API), "restart"], activation, code=3))["targets"][0]
    assert refused["process"] == original["process"], refused
    assert not list(operation.glob("zellij-stop-*.json")) and not list(operation.glob("zellij-client-exec-*.json"))
    print(f"{mode[2:]}: real input durability refusal preserves the original server/client and submits no stop or exec.", flush=True)


def native_server(action, original, operation, binary, environment, code=0):
    path = operation / f"server-{action}.json"
    path.write_text(json.dumps({"schema_version": 1, "action": action, "run_id": operation.name,
                               "expected_process": original["process"]}))
    path.chmod(0o600)
    return json.loads(command([binary, "--activation-server-control", str(path),
                               "--session", original["target"]], environment, code=code, timeout=10))


def challenge_late_output(terminals, original, operation, runtime, binary, environment, trigger, marker):
    for client in original["connections"]:
        result = native_client(client, "checkpoint", **checkpoint_request(client, original, operation, runtime))
        assert result["checkpoint"]["state"] == "confirmed", result
    native_server("checkpoint", original, operation, binary, environment)
    confirmed = wait(lambda: (reply if (reply := native_server("inventory", original, operation, binary, environment))
                             ["checkpoint"]["state"] == "confirmed" else None))
    assert confirmed["pending_authority"] == 0
    with trigger.open("w") as producer:
        producer.write("emit\n")
    held = wait(lambda: (reply if (reply := native_server("inventory", original, operation, binary, environment))
                        ["held_output_bytes"] > 0 else None))
    assert held["checkpoint"]["state"] == "pending" and held["process"] == original["process"]
    before = json.loads(command([binary, "--session", original["target"], "action", "list-panes", "--json"], environment))
    assert marker not in json.dumps(before)
    refused = native_server("stop", original, operation, binary, environment, code=3)
    assert refused.get("error"), refused
    resumed = native_server("release_original", original, operation, binary, environment)
    assert not resumed["fenced"] and resumed["process"] == original["process"]
    for client in original["connections"]:
        result = native_client(client, "release_original", expected_process=client["process"], run_id=operation.name)
        assert result["checkpoint"] is None
    wait(lambda: marker in command([binary, "--session", original["target"], "action", "list-panes", "--json"], environment))
    settled = wait(lambda: (reply if (reply := native_server("inventory", original, operation, binary, environment))
                           ["held_output_bytes"] == 0 else None))
    assert not settled["stop_accepted"]
    assert all(os.waitpid(terminal.pid, os.WNOHANG)[0] == 0 for terminal in terminals)
    print("Actual late OSC title bytes remain unparsed after checkpoint, block native stop, and resume only on the exact original server release.", flush=True)


def main():
    runtime = Path(sys.argv[1]).resolve()
    helper = Path(os.environ.get("ZELLIJ_TEST_HELPER", ROOT / "zellij/target/debug/lane-zellij")).resolve()
    with tempfile.TemporaryDirectory(prefix="z-client-", dir="/private/tmp" if sys.platform == "darwin" else "/tmp") as temporary:
        base = Path(temporary)
        home = base / "home"
        home.mkdir(mode=0o700)
        (base / "sockets").mkdir(mode=0o700)
        environment = {
            "HOME": str(home), "PATH": str(home / ".local/bin") + ":" + os.environ["PATH"],
            "TERM": "xterm-256color", "COLORTERM": "truecolor", "GIT_PAGER": "delta",
            "SHELL": "/bin/sh", "USER": os.environ.get("USER", "fixture"), "LC_ALL": "C", "TZ": "UTC",
            "ZELLIJ_SOCKET_DIR": str(base / "sockets"), "XDG_CACHE_HOME": str(base / "cache"),
            "XDG_STATE_HOME": str(base / "external"), "PROJECT_UPDATE_ALLOW_DISPOSABLE": "1",
        }
        command([sys.executable, str(ROOT / "scripts/zellij-artifacts.py"), "runtime", str(runtime)], environment)
        (home / ".local/.dotfiles-zellij-install").write_text("derived-native-client-fixture\n")
        (home / ".local/bin/zellij-context").symlink_to(helper)
        configuration = home / ".config/zellij"
        configuration.mkdir(parents=True)
        (configuration / "config.kdl").write_text(
            'show_startup_tips false\nshow_release_notes false\ndefault_mode "scroll"\n'
            'keybinds clear_defaults=true { shared {\n bind "Ctrl h" { MoveFocus "Left"; }\n'
            ' bind "Ctrl l" { MoveFocus "Right"; }\n bind "Ctrl z" { Detach; }\n }\n}\n')
        data = home / "Library/Application Support/org.Zellij-Contributors.Zellij" if sys.platform == "darwin" else home / ".local/share/zellij"
        data.mkdir(parents=True)
        (data / "desktop_integration.json").write_text('{"flags":["SetupNeverShow"]}\n')
        session = "clients-" + uuid.uuid4().hex[:8]
        binary = str(home / ".local/bin/zellij")
        layout = ('layout {\n tab name="retained" split_direction="vertical" {\n'
                  ' pane command="/bin/sh" close_on_exit=true {\n args "-c" "exit 0"\n }\n'
                  + ''.join(' pane command="/bin/sh" {\n args "-c" "exit 0"\n start_suspended true\n }\n'
                            for _ in range(2)) + ' }\n}\n')
        trigger, marker = base / "output-trigger", "zellij-owned-late-" + uuid.uuid4().hex
        if "--late-output" in sys.argv[2:]:
            os.mkfifo(trigger, 0o600)
            producer = f"read token < {shlex.quote(str(trigger))}; printf '\\033]2;{marker}\\007'; exit 0"
            layout = layout.removesuffix(' }\n}\n') + (
                f' pane command="/bin/sh" {{\n args "-c" {json.dumps(producer)}\n }}\n }}\n}}\n')
        terminals, broker = [], None
        try:
            terminals.append(Terminal(binary, environment, session, command=[
                binary, "--activation-client", "--layout-string", layout, "attach", "--create", session],
                install_navigation=False))
            terminals[0].drain(1)
            attachment = ([str(helper), "attach", session] if "--helper-attach" in sys.argv[2:]
                          else [binary, "--activation-client", "attach", session])
            terminals.append(Terminal(binary, environment, session, command=attachment, install_navigation=False))
            terminals[1].drain(1)
            command([sys.executable, str(API), "stage"], environment)
            def inventory():
                for terminal in terminals:
                    terminal.drain(0.01)
                return next(row for row in json.loads(command(
                    [sys.executable, str(API), "inventory"], environment))["targets"] if row["target"] == session)
            try:
                original = wait(lambda: (row if (row := inventory())["ready"] and len(row["connections"]) == 2 else None))
            except AssertionError:
                raise AssertionError((inventory(), [terminal.output[-4000:].decode(errors="replace") for terminal in terminals]))
            terminals[0].send(b"\x08")
            terminals[1].send(b"\x0c")
            def distinct_focus():
                row = inventory()
                return row if len({json.dumps(client["focus"], sort_keys=True)
                                   for client in row["connections"]}) == 2 else None
            original = wait(distinct_focus)
            assert all(client["managed"] and client["focus"]["pane_id"][0] > 0 for client in original["connections"])
            for discovery in (binary, str(Path.home() / ".local/bin/zellij")):
                if Path(discovery).is_file():
                    listing = command([discovery, "list-sessions", "--short"], environment, timeout=3)
                    assert session in listing, listing
            selected = (home / ".local/bin/zellij").resolve()
            client = next(value for value in original["connections"] if value["process"]["pid"] == terminals[0].pid)
            def held_authority():
                context = json.loads(command([str(home / ".local/bin/zellij-context"), "inspect",
                                              "--session", session, "--json"], environment))
                native = json.loads(command([binary, "--session", session, "action",
                                             "dump-layout", "--activation-ids"], environment))
                held = [pane for pane in context["panes"] if not pane["is_plugin"] and pane["id"] in (1, 2)]
                assert all(pane["is_held"] and not pane["exited"] and pane["exit_status"] is None
                           and str(pane["id"]) not in native["terminal_processes"] for pane in held), (held, native)
                return [(pane["id"], pane["terminal_command"]) for pane in held]
            suspended = held_authority()
            if "--inspect-held" in sys.argv[2:]:
                print("BEFORE PARSER", command([str(home / ".local/bin/zellij-context"), "inspect", "--session", session, "--json"], environment), flush=True)
                print("BEFORE NATIVE", command([binary, "--session", session, "action", "dump-layout", "--activation-ids"], environment), flush=True)
            challenge_parser(terminals[0], client, original, base, selected)
            original = inventory()
            assert held_authority() == suspended, "Parser challenges must not start or change suspended commands"
            if "--inspect-held" in sys.argv[2:]:
                print("AFTER PARSER", command([str(home / ".local/bin/zellij-context"), "inspect", "--session", session, "--json"], environment), flush=True)
                print("AFTER NATIVE", command([binary, "--session", session, "action", "dump-layout", "--activation-ids"], environment), flush=True)
                return
            if "--late-output" in sys.argv[2:]:
                operation = base / str(uuid.uuid4())
                operation.mkdir(mode=0o700)
                challenge_late_output(terminals, original, operation, selected, binary, environment, trigger, marker)
                return
            broker = Terminal(sys.executable, environment, "baseline", command=[
                sys.executable, str(API), "baseline-serve"], install_navigation=False)
            wait(lambda: (base / "external/dotfiles/zellij-activation/baseline.json").is_file())
            operation = base / str(uuid.uuid4())
            operation.mkdir(mode=0o700)
            checkpoints = operation / "checkpoints"
            checkpoints.mkdir(mode=0o700)
            frozen = operation / "zellij-inventory.json"
            frozen.write_text(json.dumps({"schema_version": 1, "targets": [original]}))
            frozen.chmod(0o600)
            activation = {**environment, "PROJECT_UPDATE_RUN_ID": operation.name,
                          "PROJECT_UPDATE_OPERATION_DIR": str(operation),
                          "PROJECT_UPDATE_CHECKPOINT_DIR": str(checkpoints), "PROJECT_UPDATE_TARGET": session}
            confirmed = json.loads(command([sys.executable, str(API), "checkpoint"], activation))["targets"][0]
            assert confirmed["checkpoint"]["state"] == "confirmed", confirmed
            failure_mode = next((flag for flag in ("--retention-limit", "--durability-failure") if flag in sys.argv[2:]), None)
            if failure_mode:
                challenge_retention_failure(failure_mode, terminals[0], client, original, operation, activation)
                return
            if "--server-fence" in sys.argv[2:]:
                forbidden = base / "forbidden-cli-launch"
                for action in (["write-chars", "forbidden-command-input"],
                               ["focus-next-pane"],
                               ["new-pane", "--", "/bin/sh", "-c", f"touch {forbidden}"]):
                    command([binary, "--session", session, "action", *action], environment, code=3, timeout=10)
                paused = inventory()
                assert paused["process"] == original["process"] and not forbidden.exists()
                assert [value["focus"] for value in paused["connections"]] == [
                    value["focus"] for value in original["connections"]]
                released = json.loads(command([sys.executable, str(API), "restore"],
                    {**activation, "PROJECT_UPDATE_RECOVER_ORIGINAL": "1"}))["targets"][0]
                assert released["process"] == original["process"]
                assert [value["process"] for value in released["connections"]] == [
                    value["process"] for value in original["connections"]]
                command([binary, "--session", session, "action", "focus-next-pane"], environment)
                print("Confirmed native server fence refuses real CLI write/focus/launch; original release resumes admission with both user TTYs intact.", flush=True)
                return
            payloads = (b"held-native-input\x1b[120u\x1b[<0;5;5M",
                        b"held-native-input\x1b[200~open-paste\x1b[97;")
            for terminal, payload in zip(terminals, payloads):
                terminal.send(payload)
            def retained_input():
                values = {client["process"]["pid"]: json.loads(
                    (operation / f"zellij-client-{client['process']['native_id']}.json").read_text())
                    for client in original["connections"]}
                return values if all(payload in b"".join(bytes(chunk) for chunk in values[terminal.pid]["recoverable_input"])
                                     for terminal, payload in zip(terminals, payloads)) else None
            retained = wait(retained_input)
            paused = inventory()
            assert {client["process"]["native_id"]: client["focus"] for client in paused["connections"]} == {
                client["process"]["native_id"]: client["focus"] for client in original["connections"]}
            try:
                restored = json.loads(command([sys.executable, str(API), "restart"], activation, timeout=60))["targets"][0]
            except AssertionError:
                for evidence in operation.glob("zellij-layout-drift-*.json"):
                    print("NATIVE_LAYOUT_DRIFT", evidence.read_text(), flush=True)
                print("NATIVE_LAUNCH_JOURNALS", json.dumps([
                    json.loads(evidence.read_text()) for pattern in
                    ("zellij-launch-*.json", "zellij-stop-*.json") for evidence in operation.glob(pattern)]), flush=True)
                print("ACTUAL_CLIENT_OWNERS", json.dumps([native_client(value) for value in original["connections"]]), flush=True)
                raise
            assert restored["ready"], restored
            assert restored["process"] != original["process"]
            assert restored["persistent_identity"] == original["persistent_identity"]
            assert len(restored["restored_clients"]) == 2
            for before in original["connections"]:
                proof = next(value for value in restored["restored_clients"] if value["original_process"] == before["process"])
                assert proof["process"]["pid"] == before["process"]["pid"]
                assert proof["process"]["start_identity"] == before["process"]["start_identity"]
                assert proof["process"]["native_id"] != before["process"]["native_id"]
                assert proof["tty"] == before["tty"] and proof["focus"] == before["focus"]
            assert all(os.waitpid(terminal.pid, os.WNOHANG)[0] == 0 for terminal in terminals)
            command([sys.executable, str(API), "restart"], activation)
            command([sys.executable, str(API), "verify"], activation)
            assert retained_input(), "Split escape and open paste bytes must remain durably retained after reconnect"
            assert len(list(operation.glob("zellij-client-exec-*.json"))) == 2
            assert not list(operation.glob("zellij-pane-launch-*.json")), "Held panes must remain unlaunched"
            print("Two original TTY/PID connections, distinct focus, gapped pane IDs, persistent UUID, selected image and unreplayed recoverable input passed.")
        finally:
            if "operation" in locals() and "original" in locals():
                try:
                    control = native_server("inventory", original, operation, binary, environment)
                    if control.get("fenced") and not control.get("stop_accepted"):
                        native_server("release_original", original, operation, binary, environment)
                except (AssertionError, OSError, ValueError, subprocess.SubprocessError):
                    pass  # A replaced/exited original cannot be released or retried.
            subprocess.run([binary, "kill-session", session], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for terminal in terminals:
                terminal.close()
            if broker is not None:
                broker.close()


if __name__ == "__main__":
    main()
