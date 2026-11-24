#!/usr/bin/env python3
"""Real two-Pi restoration through the derived native runtime and terminal broker."""

import http.server
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "scripts/zellij-activation.py"
Terminal = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))["Terminal"]


def command(argv, environment, *, timeout=180, code=0):
    result = subprocess.run(argv, env=environment, capture_output=True, text=True, timeout=timeout)
    assert result.returncode == code, (argv, result.returncode, result.stderr[-5000:], result.stdout[-5000:])
    return result.stdout


def wait(predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.03)
    raise AssertionError("Native fixture did not reach the required observable state")


def main():
    native = Path(sys.argv[1]).resolve()
    nested_fixture = "--nested" in sys.argv[2:]
    runtime = native / "target/release/zellij"
    helper = Path(os.environ.get("ZELLIJ_TEST_HELPER", ROOT / "zellij/target/debug/lane-zellij")).resolve()
    studio = Path.home() / "src/studio"
    bun = shutil.which("bun")
    assert runtime.is_file() and helper.is_file() and bun
    calls = []
    settled = threading.Event()

    class Provider(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            calls.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            data = {"id": "fixture", "object": "chat.completion.chunk", "created": 1,
                    "model": "tiny", "choices": [{"index": 0, "delta": {
                        "role": "assistant", "content": "controlled fixture response"}, "finish_reason": None}]}
            self.wfile.write(("data: " + json.dumps(data) + "\n\n").encode())
            self.wfile.flush()
            settled.wait(3600)

        def log_message(self, _format, *_args):
            pass

    provider = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    provider.daemon_threads = True
    thread = threading.Thread(target=provider.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="z-native-", dir="/private/tmp" if sys.platform == "darwin" else "/tmp") as temporary:
            base = Path(temporary)
            home = base / "home"
            home.mkdir(mode=0o700)
            state, agent, work = base / "state", base / "agent", base / "work"
            for path in (state, agent, work, base / "sockets"):
                path.mkdir(mode=0o700)
            environment = {
                "HOME": str(home), "PATH": str(home / ".local/bin") + ":" + os.environ["PATH"],
                "TERM": "xterm-256color", "COLORTERM": "truecolor", "GIT_PAGER": "delta",
                "SHELL": "/bin/sh", "USER": os.environ.get("USER", "fixture"), "LC_ALL": "C", "TZ": "UTC",
                "ZELLIJ_SOCKET_DIR": str(base / "sockets"), "XDG_CACHE_HOME": str(base / "cache"),
                "XDG_STATE_HOME": str(base / "external"), "STUDIO_STATE_DIR": str(state),
                "STUDIO_PREFIX": str(base / "prefix"), "PI_CODING_AGENT_DIR": str(agent),
                "PI_SKIP_VERSION_CHECK": "1", "PI_TELEMETRY": "0", "PROJECT_UPDATE_ALLOW_DISPOSABLE": "1",
                "CARGO_HOME": os.environ.get("CARGO_HOME", str(Path.home() / ".cargo")),
                "RUSTUP_HOME": os.environ.get("RUSTUP_HOME", str(Path.home() / ".rustup")),
            }
            (agent / "models.json").write_text(json.dumps({"providers": {"fixture": {
                "baseUrl": f"http://127.0.0.1:{provider.server_port}/v1",
                "api": "openai-completions", "apiKey": "synthetic-fixture", "models": [{"id": "tiny"}]}}}))
            command([sys.executable, str(ROOT / "scripts/zellij-artifacts.py"), "runtime", str(runtime)], environment)
            (home / ".local/.dotfiles-zellij-install").write_text("derived-native-fixture\n")
            (home / ".local/bin/zellij-context").symlink_to(helper)
            plugin = home / ".config/zellij/plugins/copy-hop.wasm"
            command([sys.executable, str(ROOT / "scripts/zellij-artifacts.py"), "plugin",
                     "dotfiles-copy-hop", str(ROOT / "zellij/copy-hop"),
                     str(ROOT / "zellij/copy-hop/target"), str(plugin)], environment)
            print("Built isolated immutable runtime, plugin and Pi artifacts.", flush=True)
            command([bun, str(studio / "scripts/lifecycle.mjs"), "build"], environment)
            installed = json.loads(command([bun, str(studio / "scripts/lifecycle.mjs"), "status"], environment))
            old = installed["installed_release"]
            config = home / ".config/zellij"
            config.mkdir(parents=True, exist_ok=True)
            (config / "config.kdl").write_text(
                'show_startup_tips false\nshow_release_notes false\n'
                'keybinds { shared {\n bind "Ctrl z" { Detach; }\n }\n}\n'
                f'plugins {{ copy-hop location={json.dumps("file:" + str(plugin))}\n}}\n'
                'load_plugins { copy-hop\n}\n')
            # Two real native Pi hosts; no inherited user shell/config or credentials.
            layout = ('layout {\n tab name="native" split_direction="vertical" {\n'
                      ' pane command="/bin/sh" close_on_exit=true {\n args "-c" "exit 0"\n }\n'
                      + "".join(f' pane cwd={json.dumps(str(work))} command={json.dumps(old + "/scripts/pi")} {{\n'
                                ' args "--offline" "--model" "fixture/tiny" "Start the owned fixture conversation"\n }\n'
                                for _ in range(2)) + ' }\n}\n')
            data = home / "Library/Application Support/org.Zellij-Contributors.Zellij" if sys.platform == "darwin" else home / ".local/share/zellij"
            data.mkdir(parents=True)
            (data / "desktop_integration.json").write_text('{"flags":["SetupNeverShow"]}\n')
            session = "native-" + uuid.uuid4().hex[:10]
            binary = str(home / ".local/bin/zellij")
            child_terminal = None
            child = "child-" + uuid.uuid4().hex[:10]
            if nested_fixture:
                child_terminal = Terminal(binary, environment, child, command=[
                    binary, "--activation-client", "--layout-string", 'layout {\n pane command="/bin/sh" {\n args "-c" "exit 0"\n start_suspended true\n }\n}\n',
                    "attach", "--create", child], install_navigation=False)
                child_terminal.drain(1)
                child_terminal.send(b"y")
                layout = layout.removesuffix(' }\n}\n') + (
                    f' pane command="/usr/bin/env" {{\n args "-u" "ZELLIJ" '
                    f'{json.dumps(binary)} "--activation-client" "attach" {json.dumps(child)}\n }}\n }}\n}}\n')
            terminal = Terminal(binary, environment, session, command=[
                binary, "--activation-client", "--layout-string", layout, "attach", "--create", session],
                install_navigation=False)
            broker = None
            second_client = None
            ordinary_client = None
            try:
                terminal.drain(1)
                terminal.send(b"y")
                def app_inventory():
                    terminal.drain(0.01)
                    value = json.loads(command([bun, str(studio / "scripts/lifecycle.mjs"), "inventory"], environment))
                    return [row for row in value["targets"] if row.get("checkpoint_binding") == "exact-session-v1"]
                before_apps = wait(lambda: (rows if len(rows := app_inventory()) == 2 and len(calls) == 2 else None))
                assert all(row["restoration_owner"]["target"] == session for row in before_apps)
                assert min(row["restoration_owner"]["pane_id"] for row in before_apps) > 0
                print("Two real native Pi conversations are running in the isolated terminal.", flush=True)
                second_client = Terminal(binary, environment, session, command=[
                    binary, "--activation-client", "attach", session], install_navigation=False)
                second_client.drain(1)
                ordinary_client = Terminal(binary, environment, session, install_navigation=False)
                ordinary_client.drain(1)
                command([sys.executable, str(API), "stage"], environment)
                connected = next(row for row in json.loads(command([sys.executable, str(API), "inventory"], environment))["targets"]
                                 if row["target"] == session)
                assert len(connected["connections"]) == 3
                refusal = base / str(uuid.uuid4())
                refusal.mkdir(mode=0o700)
                (refusal / "checkpoints").mkdir(mode=0o700)
                frozen = refusal / "zellij-inventory.json"
                frozen.write_text(json.dumps({"schema_version": 1, "targets": [connected]}))
                frozen.chmod(0o600)
                refused = json.loads(command([sys.executable, str(API), "checkpoint"],
                    {**environment, "PROJECT_UPDATE_RUN_ID": refusal.name,
                     "PROJECT_UPDATE_OPERATION_DIR": str(refusal), "PROJECT_UPDATE_CHECKPOINT_DIR": str(refusal / "checkpoints"),
                     "PROJECT_UPDATE_TARGET": session}, code=3))["targets"][0]
                assert refused["reason"] == "native-user-terminal-reconnect-checkpoint-unavailable"
                assert refused["process"] == connected["process"]
                assert os.waitpid(terminal.pid, os.WNOHANG)[0] == os.waitpid(second_client.pid, os.WNOHANG)[0] == 0
                assert os.waitpid(ordinary_client.pid, os.WNOHANG)[0] == 0
                ordinary_client.send(b"\x1a")
                wait(lambda: len(next(row for row in json.loads(command([sys.executable, str(API), "inventory"], environment))["targets"]
                                      if row["target"] == session)["connections"]) == 2)
                print("The unmanaged user client was preserved on refusal; two managed original TTYs remain connected for restoration.", flush=True)
                broker = Terminal(sys.executable, environment, "baseline", command=[
                    sys.executable, str(API), "baseline-serve"], install_navigation=False)
                wait(lambda: (base / "external/dotfiles/zellij-activation/baseline.json").is_file())
                # Build a genuinely different selected native image, leaving the mapped old vnode intact.
                next_environment = {**os.environ, "ZELLIJ_ACTIVATION_BUILD_ID": uuid.uuid4().hex * 2}
                command(["rustup", "run", "1.95.0", "cargo", "build", "--locked", "--release",
                         "--manifest-path", str(native / "Cargo.toml"), "--no-default-features",
                         "--features", "plugins_from_target,vendored_curl,web_server_capability", "--bin", "zellij"],
                        next_environment, timeout=600)
                command([sys.executable, str(ROOT / "scripts/zellij-artifacts.py"), "runtime", str(runtime)], environment)
                next_plugins = base / "next-plugins"
                shutil.copytree(ROOT / "zellij/copy-hop", next_plugins / "copy-hop",
                                ignore=shutil.ignore_patterns("target"))
                shutil.copytree(ROOT / "zellij/protocol", next_plugins / "protocol")
                symbols = base / "design-system/generated"
                symbols.mkdir(parents=True)
                shutil.copyfile(ROOT / "design-system/generated/zellij-symbols.rs",
                                symbols / "zellij-symbols.rs")
                with (next_plugins / "copy-hop/src/main.rs").open("a") as output:
                    output.write("\n// Select another compiled fixture image without changing plugin behavior.\n")
                command([sys.executable, str(ROOT / "scripts/zellij-artifacts.py"), "plugin",
                         "dotfiles-copy-hop", str(next_plugins / "copy-hop"),
                         str(ROOT / "zellij/copy-hop/target"), str(plugin)], environment)
                next_source = base / "next-studio"
                command([sys.executable, str(studio / "scripts/export.py"), str(next_source)], environment)
                with (next_source / "README.md").open("a") as output:
                    output.write("\nNative terminal fixture selects the updated immutable Pi bundle.\n")
                command([bun, str(next_source / "scripts/lifecycle.mjs"), "build"], environment)
                command([sys.executable, str(API), "stage"], environment)
                apps = app_inventory()
                assert len(apps) == 2 and all(row["running_identity"] != row["expected_identity"] for row in apps)
                terminal_rows = json.loads(command([sys.executable, str(API), "inventory"], environment))["targets"]
                terminal_before = next(row for row in terminal_rows if row["target"] == session)
                assert terminal_before["running_identity"] != terminal_before["expected_identity"]
                if nested_fixture:
                    assert child in terminal_before["nested_targets"].values()
                operation = base / str(uuid.uuid4())
                checkpoints = operation / "checkpoints"
                operation.mkdir(mode=0o700)
                checkpoints.mkdir(mode=0o700)
                for name, rows in (("studio", apps), ("zellij", terminal_rows)):
                    path = operation / f"{name}-inventory.json"
                    path.write_text(json.dumps({"schema_version": 1, "targets": rows}))
                    path.chmod(0o600)
                activation = {**environment, "PROJECT_UPDATE_RUN_ID": operation.name,
                              "PROJECT_UPDATE_OPERATION_DIR": str(operation),
                              "PROJECT_UPDATE_CHECKPOINT_DIR": str(checkpoints)}
                import hashlib
                for app in apps:
                    selected = {**activation, "PROJECT_UPDATE_TARGET": app["target"]}
                    confirmed = json.loads(command([bun, str(studio / "scripts/lifecycle.mjs"), "checkpoint"], selected))["targets"][0]
                    assert confirmed["checkpoint"]["state"] == "confirmed"
                    path = checkpoints / ("studio-" + hashlib.sha256(app["target"].encode()).hexdigest() + ".json")
                    path.write_text(json.dumps([confirmed]))
                    path.chmod(0o600)
                selected_terminal = {**activation, "PROJECT_UPDATE_TARGET": session}
                if nested_fixture:
                    confirmed_child = json.loads(command([sys.executable, str(API), "checkpoint"],
                        {**activation, "PROJECT_UPDATE_TARGET": child}))["targets"][0]
                    assert confirmed_child["checkpoint"]["state"] == "confirmed"
                confirmed_terminal = json.loads(command([sys.executable, str(API), "checkpoint"], selected_terminal))["targets"][0]
                assert confirmed_terminal["checkpoint"]["state"] == "confirmed"
                print("Application cancellation and native terminal checkpoints confirmed.", flush=True)
                for app in apps:
                    selected = {**activation, "PROJECT_UPDATE_TARGET": app["target"],
                                "PROJECT_UPDATE_DEFER_RESTORATION": "1",
                                "PROJECT_UPDATE_DEFERRED_SESSION_IDS": json.dumps([app["sessions"][0]["session_id"]])}
                    response = json.loads(command([bun, str(studio / "scripts/lifecycle.mjs"), "restart"], selected))["targets"][0]
                    assert response["process"] is None and response["sessions"][0]["restoration"] == "pending"
                restored = json.loads(command([sys.executable, str(API), "restart"], selected_terminal, timeout=60))["targets"][0]
                assert restored["ready"] and restored["running_identity"] == restored["expected_identity"]
                assert restored["process"] != terminal_before["process"]
                assert restored["persistent_identity"] == terminal_before["persistent_identity"]
                assert len(restored["restored_clients"]) == 2
                assert all(os.waitpid(client.pid, os.WNOHANG)[0] == 0 for client in (terminal, second_client))
                assert len(restored["restored_applications"]) == 2
                assert {row["original_process"]["native_id"] for row in restored["restored_applications"]} == {
                    row["process"]["native_id"] for row in apps}
                if nested_fixture:
                    final_child = next(row for row in json.loads(command([sys.executable, str(API), "verify"], activation))["targets"]
                                       if row["target"] == child)
                    initial_child = next(row for row in terminal_rows if row["target"] == child)
                    assert final_child["ready"] and final_child["persistent_identity"] == initial_child["persistent_identity"]
                    assert final_child["process"] != initial_child["process"]
                    assert len(final_child["restored_clients"]) == 2
                    assert os.waitpid(child_terminal.pid, os.WNOHANG)[0] == 0
                    assert child in restored["nested_targets"].values()
                # The original managed clients reconnected without replaying application commands.
                if True:
                    def restored_apps():
                        rows = app_inventory()
                        return rows if len(rows) == 2 and all(row["ready"] for row in rows) else None
                    after_apps = wait(restored_apps)
                    actual = {row["sessions"][0]["session_id"]: row for row in after_apps}
                    for app in apps:
                        restored_app = actual[app["sessions"][0]["session_id"]]
                        assert restored_app["process"] != app["process"]
                        assert restored_app["running_identity"] == app["expected_identity"]
                        assert restored_app["sessions"][0]["transcript_path"] == app["sessions"][0]["transcript_path"]
                        cp = json.loads((checkpoints / ("studio-" + app["process"]["native_id"] + ".json")).read_text())
                        assert restored_app["sessions"][0]["branch_id"] == cp["session"]["branch_id"]
                        assert restored_app["terminal_environment"]["NO_COLOR"] is None
                        assert restored_app["terminal_environment"]["GIT_PAGER"] == "delta"
                    assert len(calls) == 2, "Native restoration must not replay an interrupted model operation"
                    # An uncertain/repeated caller cannot launch the applications a second time.
                    command([sys.executable, str(API), "restart"], selected_terminal, timeout=60)
                    assert len(list(operation.glob("zellij-pane-launch-*.json"))) == (3 if nested_fixture else 2)
                    assert len(calls) == 2
                print("Real immutable runtime replacement, two exact Pi sessions, native layout/UUID, independent environment and one launch per application passed.")
            finally:
                subprocess.run([binary, "kill-session", session], env=environment,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                terminal.close()
                if second_client is not None:
                    second_client.close()
                if ordinary_client is not None:
                    ordinary_client.close()
                if broker is not None:
                    broker.close()
                if child_terminal is not None:
                    subprocess.run([binary, "kill-session", child], env=environment,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    child_terminal.close()
    finally:
        settled.set()
        provider.shutdown()
        provider.server_close()


if __name__ == "__main__":
    main()
