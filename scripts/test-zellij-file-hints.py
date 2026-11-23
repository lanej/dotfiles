#!/usr/bin/env python3
"""Exercise the real file-hint receiver, editor RPC and routing in an isolated PTY.

Kitty's rendered picker is covered by test-kitty-image-preview.py. This detector
uses the same terminal reply protocol without requiring a graphical display.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("zellij_terminal", ROOT / "scripts/test-zellij.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Terminal = module.Terminal


def exercise(work, binary):
    home, runtime, source = work / "home", work / "run", work / "worktree"
    for directory in (home, runtime, source, work / "bin"):
        directory.mkdir()
    for alias in ("zellij-helper", "zellij-image-hints"):
        (work / "bin" / alias).symlink_to(binary)
    env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
           "XDG_CACHE_HOME": str(home / ".cache"), "XDG_DATA_HOME": str(home / ".local/share"),
           "XDG_STATE_HOME": str(home / ".local/state"), "XDG_RUNTIME_DIR": str(runtime),
           "ZELLIJ_SOCKET_DIR": str(runtime), "SHELL": "/bin/sh", "TERM": "xterm-256color",
           "PATH": str(work / "bin") + os.pathsep + os.environ["PATH"]}
    # Fixtures have their own editor and terminal configuration, not the user's startup.
    env.pop("NVIM", None)
    env.pop("ZELLIJ", None)
    for key in ("ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_ORIGIN_PANE_ID", "ZELLIJ_CONFIG_DIR",
                "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV"):
        env.pop(key, None)
    subprocess.run([sys.executable, str(ROOT / "scripts/make/zellij-config.py"), str(home)],
                   env=env, check=True, capture_output=True)
    config = home / ".config/zellij/config.kdl"
    config.parent.mkdir(parents=True)
    production = (ROOT / "zellij/config.kdl").read_text()
    binding = re.search(r'(?ms)^        bind "Ctrl Alt F12" \{.*?^        \}', production)
    if binding is None:
        raise AssertionError("Missing production file-hint binding")
    config.write_text('default_mode "locked"\nshow_startup_tips false\nshow_release_notes false\n'
                      'default_shell "/bin/sh"\nkeybinds clear-defaults=true {\n shared {\n'
                      + binding.group() + '\n}\n}\n')
    routes = config.parent / "file-routes.toml"
    shutil.copyfile(ROOT / "zellij/file-routes.toml", routes)
    init = work / "init.lua"
    init.write_text("vim.opt.runtimepath:prepend(" + json.dumps(str(ROOT / "nvim")) + ")\n"
                    "vim.opt.hidden = true\nrequire('file-opener').setup()\n")
    scratch = source / "scratch.lua"
    scratch.write_text("original\n")
    target = source / "src/source file.rs"
    target.parent.mkdir()
    target.write_text("fn reference_line() {}\n" * 60)
    fixture = work / "agent.py"
    fixture.write_text("import signal\nprint('src/source file.rs:42:7', flush=True)\nsignal.pause()\n")
    socket = work / "nvim.sock"
    layout = work / "layout.kdl"
    layout.write_text('layout {\n pane split_direction="vertical" {\n'
                      'pane command="' + sys.executable + '" cwd=' + json.dumps(str(source)) +
                      ' { args ' + json.dumps(str(fixture)) + '; }\n'
                      'pane command="nvim" close_on_exit=true cwd=' + json.dumps(str(source)) +
                      ' { args "-u" ' + json.dumps(str(init)) + ' "--listen" ' + json.dumps(str(socket)) +
                      ' ' + json.dumps(str(scratch)) + '; }\n}\n}\n')
    session = "file-hints-test"
    terminal = Terminal("zellij", env, session,
                        ["zellij", "--config", str(config), "--session", session,
                         "--new-session-with-layout", str(layout)], install_navigation=False)

    def rpc(expression, address=socket):
        result = subprocess.check_output(["nvim", "--server", str(address), "--remote-expr", expression],
                                         env=env, text=True, timeout=4)
        return result.strip()

    def lua(expression, address=socket):
        return json.loads(rpc("json_encode(luaeval(" + json.dumps(expression) + "))", address))

    def focused(identifier):
        return any(p["id"] == identifier and p["is_focused"] for p in terminal.terminals())

    def start_hint(selection):
        if not focused(agent_id):
            terminal.action("focus-pane-id", str(agent_id))
        output_start = len(terminal.output)
        terminal.send(b"\x1b[24;7~")
        receiver = terminal.until("file-hint receiver", lambda: next(
            (p for p in terminal.terminals() if p["is_floating"] and "Kitty hints" in p["title"]), None))
        receiver_id = receiver["id"]
        marker = terminal.until("file-hint ticket", lambda: re.search(
            rb"dotfiles-hints-v2://([0-9a-f]{32})/", terminal.output[output_start:]))
        payload = base64.urlsafe_b64encode(json.dumps(selection).encode()).rstrip(b"=") if selection else b""
        terminal.send(b"!" + marker[1] + payload + b".")
        return receiver_id

    def closed(identifier):
        terminal.until("receiver closure", lambda: all(p["id"] != identifier for p in terminal.terminals()))

    try:
        terminal.until("agent and editor", lambda: len(terminal.terminals()) == 2 and socket.exists())
        agent_id = next(p["id"] for p in terminal.terminals() if str(fixture) in (p.get("terminal_command") or ""))
        editor_id = next(p["id"] for p in terminal.terminals() if p["id"] != agent_id)
        registry = runtime / f"lane-zellij-editors-{os.getuid()}"
        terminal.until("editor registration", lambda: registry.exists() and list(registry.glob("*.json")))
        lua("vim.api.nvim_buf_set_lines(0, 0, -1, false, {'unsaved work'}) or true")
        receiver = start_hint({"path": "src/source file.rs", "line": 42, "column": 7})
        closed(receiver)
        terminal.until("editor focus", lambda: focused(editor_id))
        if lua("{vim.api.nvim_buf_get_name(0), vim.api.nvim_win_get_cursor(0)}") != [str(target), [42, 6]]:
            raise AssertionError("The existing editor did not open the source worktree file at 42:7")
        if lua("{vim.fn.getbufline(" + json.dumps(str(scratch)) + ", 1)[1], vim.fn.getbufvar(" +
               json.dumps(str(scratch)) + ", '&modified')}") != ["unsaved work", 1]:
            raise AssertionError("Opening the reference lost unsaved editor content")
        if len(terminal.terminals()) != 2:
            raise AssertionError("Reusing Neovim created an extra pane")
        readme = source / "README"
        readme.write_text("extensionless text\nsecond line\n")
        closed(start_hint({"path": "README", "line": 2}))
        if lua("{vim.api.nvim_buf_get_name(0), vim.api.nvim_win_get_cursor(0)[1]}") != [str(readme), 2]:
            raise AssertionError("Extensionless text did not use MIME fallback to Neovim")
        unusual = source / "odd 'quoted' {line};$(noop).rs"
        unusual.write_text("literal file\nsecond line\n")
        closed(start_hint({"path": unusual.name, "line": 2}))
        if lua("vim.api.nvim_buf_get_name(0)") != str(unusual):
            raise AssertionError("An unusual filename was interpreted as editor commands")
        closed(start_hint({"path": str(target), "line": 42, "column": 7}))
        closed(start_hint(None))
        receiver = start_hint({"path": "missing.rs"})
        terminal.until("missing-file error", lambda: "File does not exist" in terminal.action(
            "dump-screen", "--pane-id", str(receiver)))
        terminal.send(b"\r")
        closed(receiver)

        # Route table edits apply on the next selection, with literal argument expansion.
        recorder = work / "record.py"
        recorded = work / "recorded.json"
        recorder.write_text("import json, sys, time\nfrom pathlib import Path\ntime.sleep(.4)\n"
                            "Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))\n")
        strange = source / "literal {line};$(echo nope).probe"
        strange.write_text("fixture")
        with routes.open("a") as output:
            output.write('\n[[routes]]\nextensions=["probe"]\nhandler="command"\nlaunch="background"\ncommand=' +
                         json.dumps([sys.executable, str(recorder), str(recorded), "{path}", "{line}", "{column}"]) + "\n")
        closed(start_hint({"path": strange.name, "line": 3, "column": 2}))
        terminal.until("custom command result", recorded.exists)
        if json.loads(recorded.read_text()) != [str(strange), "3", "2"]:
            raise AssertionError("Custom command arguments were interpreted or expanded more than once")
        recorded.unlink()
        with routes.open("a") as output:
            output.write('\n[[routes]]\nextensions=["paneprobe"]\nhandler="command"\nlaunch="pane"\ncommand=' +
                         json.dumps([sys.executable, str(recorder), str(recorded), "{path}"]) + "\n")
        interactive = source / "interactive.paneprobe"
        interactive.write_text("fixture")
        closed(start_hint({"path": interactive.name}))
        terminal.until("custom pane command result", recorded.exists)
        if json.loads(recorded.read_text()) != [str(interactive)]:
            raise AssertionError("The custom pane program did not receive the file")
        terminal.until("custom command pane exits", lambda: len(terminal.terminals()) == 2)

        # Observe system-opener selection without launching the user's desktop apps.
        system_record = work / "system.json"
        system_opener = work / "bin" / ("open" if sys.platform == "darwin" else "xdg-open")
        system_opener.write_text("#!" + sys.executable + "\nimport json, sys\nfrom pathlib import Path\nPath(" +
                                 repr(str(system_record)) + ").write_text(json.dumps(sys.argv[1:]))\n")
        system_opener.chmod(0o755)
        pdf = source / "diagram.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")
        closed(start_hint({"path": pdf.name}))
        terminal.until("system opener arguments", system_record.exists)
        if json.loads(system_record.read_text()) != [str(pdf)]:
            raise AssertionError("A PDF did not reach the host's associated application")
        with routes.open("a") as output:
            output.write('\n[[routes]]\nextensions=["missingapp"]\nhandler="command"\n'
                         'launch="background"\ncommand=["file-hints-program-does-not-exist", "{path}"]\n')
        unavailable = source / "example.missingapp"
        unavailable.write_text("fixture")
        receiver = start_hint({"path": unavailable.name})
        terminal.until("missing-program error", lambda: "Could not start" in terminal.action(
            "dump-screen", "--pane-id", str(receiver)))
        terminal.send(b"\r")
        closed(receiver)

        # A second registered editor requires an explicit choice; Escape must not open anything.
        second_socket = work / "second.sock"
        terminal.action("new-pane", "--close-on-exit", "--direction", "right", "--cwd", str(source), "--",
                        "nvim", "-u", str(init), "--listen", str(second_socket), str(scratch))
        terminal.until("second editor registration", lambda: len(list(registry.glob("*.json"))) == 2)
        receiver = start_hint({"path": str(target), "line": 10})
        terminal.until("editor chooser", lambda: "Open in Neovim" in terminal.action("dump-screen", "--pane-id", str(receiver)))
        terminal.send(b"\x1b")
        closed(receiver)
        if lua("vim.api.nvim_win_get_cursor(0)")[0] != 42:
            raise AssertionError("Cancelling the chooser changed the editor")
        receiver = start_hint({"path": str(target), "line": 10})
        terminal.until("editor chooser again", lambda: "Open in Neovim" in terminal.action("dump-screen", "--pane-id", str(receiver)))
        terminal.send(b"\r")
        closed(receiver)
        if lua("vim.api.nvim_win_get_cursor(0)")[0] != 10:
            raise AssertionError("The chosen editor did not receive the file")

        # Normal exit removes registrations. A stale record must not suppress new-editor fallback.
        stale = json.loads(next(registry.glob("*.json")).read_text())
        for address in (second_socket, socket):
            subprocess.run(["nvim", "--server", str(address), "--remote-send", "<C-\\><C-N>:qa!<CR>"],
                           env=env, capture_output=True, timeout=4, check=True)
        terminal.until("editor exits", lambda: len(terminal.terminals()) == 1)
        terminal.until("registration cleanup", lambda: not list(registry.glob("*.json")))
        (registry / "stale.json").write_text(json.dumps(stale))
        # The fallback editor loads the fixture through XDG's normal init location.
        nvim_config = home / ".config/nvim"
        nvim_config.mkdir()
        shutil.copyfile(init, nvim_config / "init.lua")
        closed(start_hint({"path": str(target), "line": 12}))
        new_editor = terminal.until("new right-hand editor", lambda: next((p for p in terminal.terminals()
            if p["id"] != agent_id and not p["is_floating"] and p["is_focused"]), None))
        registrations = terminal.until("replacement registration", lambda: [json.loads(p.read_text())
            for p in registry.glob("*.json") if p.name != "stale.json"])
        address = registrations[0]["editor"]["socket"]
        terminal.until("replacement opens referenced line", lambda: lua("vim.api.nvim_win_get_cursor(0)", address)[0] == 12)
        if new_editor["pane_x"] <= next(p["pane_x"] for p in terminal.terminals() if p["id"] == agent_id):
            raise AssertionError("The fallback editor did not open to the right")
        print("PASS: file hints reuse Neovim, preserve unsaved work, route literal arguments, choose editors, and recover from stale registrations.")
    finally:
        subprocess.run(["zellij", "delete-session", session, "--force"], env=env, capture_output=True, timeout=5)
        terminal.close()


if __name__ == "__main__":
    binary = (ROOT / "zellij/target/release/lane-zellij").resolve()
    if len(sys.argv) > 1:
        binary = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="file-hints-", dir="/tmp") as directory:
        exercise(Path(directory).resolve(), binary)
