#!/usr/bin/env python3
"""Accept smart pane navigation through installed Zsh, Neovim and Zellij.

Uses the pinned Navigator plugin, real terminal keystrokes and a private session.
Requires Neovim 0.12+, Zsh, tmux, Zellij 0.45.1+, git, and public GitHub access.
"""

import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


workflow = importlib.import_module("test-zellij")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


def nested_workflow(binary, env, work, init):
    """Keep navigation in the nearest mux in both real nesting directions."""
    env = {**env, "TMUX_TMPDIR": env["XDG_RUNTIME_DIR"]}
    tmux = shutil.which("tmux")
    outer_socket, inner_socket = "navigation-outer", "navigation-inner"
    name = "nested-" + work.name

    def mux(socket, *args):
        result = subprocess.run([tmux, "-L", socket, *args], env=env,
                                text=True, capture_output=True, timeout=3)
        result.check_returncode()
        return result.stdout.strip()

    terminal = Terminal(binary, env, name, [
        tmux, "-L", outer_socket, "-f", "/dev/null", "new-session", "-s", "outer",
        binary, "attach", "--create", name,
    ])
    try:
        terminal.until("Zellij starts inside tmux", lambda: PROMPT in terminal.output)
        outer_pane = mux(outer_socket, "display-message", "-p", "#{pane_id}")
        mux(outer_socket, "split-window", "-h", "-d", "/bin/sh")
        terminal.prefix(b"v")
        terminal.until("nested Zellij has two panes", lambda: len(terminal.terminals()) == 2)
        panes = sorted(terminal.terminals(), key=lambda p: p["pane_x"])
        left, right = panes[0]["id"], panes[1]["id"]
        terminal.until("nested Zsh is ready", lambda:
                       PROMPT.decode().strip() in terminal.action("dump-screen", "--pane-id", str(right)))
        terminal.send(b"\x08")
        terminal.until("Zsh navigation stays in nested Zellij", lambda:
                       next(p for p in terminal.terminals() if p["id"] == left)["is_focused"])

        socket = work / "nested-nvim.sock"
        terminal.send((shlex.join(["nvim", "-u", str(init), "-i", "NONE", "--listen", str(socket)]) + "\r").encode())
        def editor(expression, address=socket):
            result = subprocess.run(["nvim", "--server", str(address), "--remote-expr", expression],
                                    env=env, text=True, capture_output=True, timeout=2)
            result.check_returncode()
            return result.stdout.strip()
        terminal.until("nested editor has two splits", lambda: socket.exists() and editor('winnr("$")') == "2")
        terminal.send(b"\x0c")
        terminal.until("nested editor crosses its internal split", lambda: editor("winnr()") == "2")
        terminal.send(b"\x0c")
        terminal.until("editor boundary moves the inner Zellij pane", lambda:
                       next(p for p in terminal.terminals() if p["id"] == right)["is_focused"])
        assert mux(outer_socket, "display-message", "-p", "#{pane_id}") == outer_pane

        # Reverse the innermost ownership without clearing either inherited
        # mux's variables: tmux now owns this pane below a live Zellij server.
        terminal.send((shlex.join(["env", "-u", "TMUX", "-u", "TMUX_PANE",
                                  tmux, "-L", inner_socket, "-f", "/dev/null",
                                  "new-session", "-s", "inner"]) + "\r").encode())
        terminal.until("tmux starts inside Zellij", lambda:
                       PROMPT.decode().strip() in mux(inner_socket, "capture-pane", "-p"))
        inner_left = mux(inner_socket, "display-message", "-p", "#{pane_id}")
        inner_right = mux(inner_socket, "split-window", "-h", "-d", "-P", "-F", "#{pane_id}")
        inner_editor = work / "inner-tmux-nvim.sock"
        terminal.send((shlex.join(["nvim", "-u", str(init), "-i", "NONE", "--listen", str(inner_editor)]) + "\r").encode())
        terminal.until("tmux-owned editor starts", lambda:
                       inner_editor.exists() and editor('winnr("$")', inner_editor) == "2")
        terminal.send(b"\x0c")
        terminal.until("tmux-owned editor crosses its internal split", lambda:
                       editor("winnr()", inner_editor) == "2")
        terminal.send(b"\x0c")
        terminal.until("editor boundary moves the innermost tmux pane", lambda:
                       mux(inner_socket, "display-message", "-p", "#{pane_id}") == inner_right)
        assert inner_left != inner_right
        assert next(p for p in terminal.terminals() if p["id"] == right)["is_focused"]
        assert mux(outer_socket, "display-message", "-p", "#{pane_id}") == outer_pane
        terminal.until("innermost Zsh prompt is ready", lambda:
                       PROMPT.decode().strip() in mux(inner_socket, "capture-pane", "-p", "-t", inner_right))
        terminal.send(b"printf '%s' ax\x08 > \"$HOME/tmux-backspace\"\r")
        proof = Path(env["HOME"]) / "tmux-backspace"
        terminal.until("tmux-owned Zsh keeps backspace", lambda:
                       proof.exists() and proof.read_text() == "a")
        print("PASS: Zellij inside tmux and tmux inside Zellij each retain their own navigation; "
              "outer pane focus and tmux shell editing remain unchanged.")
    finally:
        subprocess.run([tmux, "-L", inner_socket, "kill-server"], env=env,
                       capture_output=True, timeout=5)
        subprocess.run([binary, "kill-session", name], env=env, capture_output=True, timeout=5)
        subprocess.run([tmux, "-L", outer_socket, "kill-server"], env=env,
                       capture_output=True, timeout=5)
        terminal.close()


def main():
    for name in ("zellij", "nvim", "zsh", "tmux", "git"):
        assert shutil.which(name), f"Install {name} before testing pane navigation"
    with tempfile.TemporaryDirectory(prefix="zj-nav-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / "home", work / "run", work / "tmp"
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": shutil.which("zsh"),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temporary),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "NVIM", "NVIM_LISTEN_ADDRESS",
                    "ENV", "BASH_ENV", "TERM_PROGRAM"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij", "zsh-config", "vim-config"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        binary = shutil.which("zellij")
        # Delay one real query to exercise a tab switch while application-owned
        # navigation waits. All answers still come from the actual server.
        proxy = work / "tools"
        proxy.mkdir()
        (proxy / "zellij").write_text('''#!/usr/bin/env python3
import os, pathlib, sys, time
work = pathlib.Path(os.environ["NAVIGATION_WORK"])
armed = work / "query-armed"
if armed.exists() and (armed.read_text() or "list-panes") in sys.argv:
    armed.unlink()
    (work / "query-blocked").touch()
    while not (work / "query-release").exists():
        time.sleep(0.01)
os.execv(os.environ["NAVIGATION_ZELLIJ"], [os.environ["NAVIGATION_ZELLIJ"], *sys.argv[1:]])
''')
        (proxy / "zellij").chmod(0o700)
        env.update(NAVIGATION_WORK=str(work), NAVIGATION_ZELLIJ=binary)
        env["PATH"] = str(proxy) + os.pathsep + env["PATH"]
        # The actual installed zshrc activates the integration. Omit unrelated
        # account/profile setup and replace only its prompt in this fixture.
        (home / ".profile").unlink()
        zdot = work / "zdot"
        zdot.mkdir()
        (zdot / ".zshenv").write_text("unsetopt globalrcs\n")
        (zdot / ".zshrc").write_text('source "$HOME/.zshrc"\nPS1=' + shlex.quote(PROMPT.decode()) + "\n")
        env["ZDOTDIR"] = str(zdot)
        plugin = work / "Navigator.nvim"
        revision = json.loads((ROOT / "nvim/lazy-lock.json").read_text())["Navigator.nvim"]["commit"]
        subprocess.run(["git", "init", "-q", str(plugin)], check=True, env=env)
        subprocess.run(["git", "-C", str(plugin), "fetch", "-q", "--depth=1",
                        "https://github.com/numToStr/Navigator.nvim.git", revision], check=True, env=env)
        subprocess.run(["git", "-C", str(plugin), "checkout", "-q", "--detach", "FETCH_HEAD"], check=True, env=env)
        env["NAVIGATOR_RUNTIME"] = str(plugin)
        editing = work / "editing.txt"
        editing.write_text("Navigation fixture\n")
        env["NAVIGATION_FILE"] = str(editing)
        init = work / "init.lua"
        init.write_text('''
vim.opt.runtimepath:prepend(vim.env.HOME .. "/.config/nvim")
vim.opt.runtimepath:append(vim.env.NAVIGATOR_RUNTIME)
vim.opt.swapfile = false
require("pane-navigation").setup()
vim.cmd.edit(vim.env.NAVIGATION_FILE)
vim.cmd("vsplit")
vim.cmd("wincmd h")
''')
        # Keep native scrollback editing isolated from unrelated editor
        # plugins; the editor under test still uses the installed integration.
        env["NVIM_APPNAME"] = "navigation-scrollback"
        scrollback_config = home / ".config" / env["NVIM_APPNAME"]
        scrollback_config.mkdir()
        (scrollback_config / "init.lua").write_text("vim.opt.swapfile = false\n")
        outside = subprocess.run(["zsh", "-d", "-i", "-c", "bindkey -M viins '^H'"],
                                 env=env, text=True, capture_output=True, check=True, timeout=5)
        assert '"^H" backward-delete-char' in outside.stdout, outside
        subprocess.run(["nvim", "--headless", "-u", str(init), "-i", "NONE",
                        '+lua vim.cmd.normal(vim.api.nvim_replace_termcodes("<C-l>", true, false, true)); assert(vim.fn.winnr() == 2)',
                        "+qa!"], env=env, text=True, capture_output=True, check=True, timeout=5)
        socket = work / "nvim.sock"
        name = "navigation-" + work.name
        terminal = Terminal(binary, env, name)
        try:
            terminal.until("installed Zsh starts", lambda:
                           PROMPT in terminal.output and len(terminal.terminals()) == 1)
            terminal.prefix(b"v")
            terminal.until("two Zellij panes", lambda: len(terminal.terminals()) == 2)
            panes = sorted(terminal.terminals(), key=lambda p: p["pane_x"])
            left, right = panes[0]["id"], panes[1]["id"]
            terminal.until("the new Zsh prompt is ready", lambda:
                           PROMPT.decode().strip() in terminal.action("dump-screen", "--pane-id", f"terminal_{right}"))

            def focused():
                current = json.loads(terminal.action("current-tab-info", "--json"))["tab_id"]
                return next(p["id"] for p in terminal.terminals()
                            if p["tab_id"] == current and p["is_focused"])

            def editor(expression):
                result = subprocess.run(["nvim", "--server", str(socket), "--remote-expr", expression],
                                        env=env, text=True, capture_output=True, timeout=2)
                result.check_returncode()
                return result.stdout.strip()

            terminal.send(b"\x08")
            terminal.until("bare Ctrl-h moves from the Zsh prompt", lambda: focused() == left)
            terminal.send((shlex.join(["nvim", "-u", str(init), "-i", "NONE", "--listen", str(socket)]) + "\r").encode())
            terminal.until("Neovim opens two splits", lambda: socket.exists() and editor('winnr("$")') == "2")
            terminal.send(b"\x0c")
            terminal.until("Ctrl-l moves inside Neovim first", lambda: editor("winnr()") == "2")
            assert focused() == left
            terminal.send(b"\x0c")
            terminal.until("Ctrl-l crosses the editor boundary", lambda: focused() == right)
            terminal.send(b"\x08")
            terminal.until("Ctrl-h returns from Zsh to Neovim", lambda: focused() == left)
            assert editor('winnr("$")') == "2"
            terminal.send(b"\x08")
            terminal.until("Ctrl-h returns to the editor's left split", lambda: editor("winnr()") == "1")

            terminal.send(b"i\x0c")
            terminal.until("insert-mode navigation stays inside the editor first", lambda:
                           editor("winnr()") == "2" and editor("mode()") == "i")
            assert focused() == left
            terminal.send(b"\x0c")
            terminal.until("insert-mode boundary reaches the shell", lambda: focused() == right)
            terminal.send(b"\x08")
            terminal.until("return preserves insert mode", lambda: focused() == left and editor("mode()") == "i")
            terminal.send(b"\x08\x1b")
            terminal.until("return to the left editor split", lambda: editor("winnr()") == "1")
            terminal.send(b":split\r")
            terminal.until("editor has a horizontal split", lambda: editor('winnr("$")') == "3")
            upper = editor("win_getid()")
            terminal.send(b"\x0a")
            terminal.until("Ctrl-j uses the lower editor split", lambda: editor("win_getid()") != upper)
            lower = editor("win_getid()")
            assert focused() == left
            terminal.send(b"\x0b")
            terminal.until("Ctrl-k uses the upper editor split", lambda: editor("win_getid()") == upper)
            terminal.send(b"\x0a")
            terminal.until("return to the lower editor split", lambda: editor("win_getid()") == lower)

            terminal.prefix(b"s")
            terminal.until("create a shell below the editor", lambda: len(terminal.terminals()) == 3)
            below = next(p["id"] for p in terminal.terminals() if p["id"] not in (left, right))
            terminal.until("the lower shell is ready", lambda:
                           PROMPT.decode().strip() in terminal.action("dump-screen", "--pane-id", f"terminal_{below}"))
            terminal.send(b"\x0b")
            terminal.until("Ctrl-k enters the editor from below", lambda: focused() == left)
            terminal.send(b"\x0a")
            terminal.until("Ctrl-j crosses the lower editor boundary", lambda: focused() == below)
            terminal.send(b"\x0b")
            terminal.until("return to the editor", lambda: focused() == left)
            assert editor('winnr("$")') == "3"

            terminal.prefix(b"z")
            terminal.until("zoom the editor", lambda: any(p["id"] == left and p["is_fullscreen"] for p in terminal.terminals()))
            terminal.send(b"\x0a:let g:navigation_settled = 1\r")
            terminal.until("zoomed navigation has finished", lambda: editor("get(g:, 'navigation_settled', 0)") == "1")
            assert focused() == left and any(p["is_fullscreen"] for p in terminal.terminals())
            terminal.send(b"\x0b")
            terminal.until("zoom still permits internal editor movement", lambda: editor("win_getid()") == upper)
            terminal.prefix(b"z")
            terminal.prefix(b"c")
            terminal.until("second tab exists", lambda: len(terminal.tabs()) == 2)
            terminal.prefix(b"\x10")
            terminal.until("back to the editor tab", lambda: focused() == left)
            terminal.send(b"\x08\x0b:let g:navigation_settled = 2\r")
            terminal.until("edge navigation has finished", lambda: editor("get(g:, 'navigation_settled', 0)") == "2")
            assert focused() == left
            assert next(t for t in terminal.tabs() if t["active"])["position"] == 0

            terminal.prefix(b"n")
            terminal.until("second tab becomes active", lambda: terminal.tabs()[1]["active"])
            terminal.prefix(b"v")
            terminal.until("second tab has two panes", lambda:
                           len([p for p in terminal.terminals() if p["tab_id"] == 1]) == 2)
            second = sorted([p for p in terminal.terminals() if p["tab_id"] == 1],
                            key=lambda p: p["pane_x"])
            terminal.prefix(b"h")
            terminal.until("second tab left pane selected", lambda: focused() == second[0]["id"])
            terminal.prefix(b"\x10")
            terminal.until("return to original editor", lambda: focused() == left)
            (work / "query-armed").touch()
            terminal.send(b"\x08")
            terminal.until("navigation waits for the real pane query", lambda:
                           (work / "query-blocked").exists())
            terminal.prefix(b"n")
            terminal.until("change tab while navigation waits", lambda: terminal.tabs()[1]["active"])
            (work / "query-release").touch()
            # A response from the editor's event loop follows its synchronous
            # navigation helper completing; no arbitrary settling sleep.
            terminal.until("delayed navigation finishes", lambda: editor('winnr("$")') == "3")
            assert focused() == second[0]["id"], "Stale navigation moved a different tab"
            terminal.prefix(b"\x10")
            terminal.until("return to the original tab", lambda: focused() == left)

            # Scrollback editors are omitted from list-clients even though
            # their clients remain connected and can become the CLI target.
            second_client = Terminal(binary, env, name)
            try:
                def attached_clients():
                    return {client_id for tab in terminal.tabs()
                            for client_id in tab["other_focused_clients"]}

                def listed_clients():
                    return [line.split(None, 2) for line in
                            terminal.action("list-clients").splitlines()[1:] if line.strip()]

                terminal.until("second client attaches", lambda: len(attached_clients()) == 2)
                second_client.prefix(b"l")
                terminal.until("second client focuses the right shell", lambda:
                               any(row[1] == f"terminal_{right}" for row in listed_clients()))
                known_panes = {p["id"] for p in terminal.terminals()}
                second_client.prefix(b"e")
                terminal.until("scrollback editor hides its client from the pane listing", lambda:
                               len(listed_clients()) == 1 and
                               any(p["id"] not in known_panes for p in terminal.terminals()))
                scrollback = next(p["id"] for p in terminal.terminals()
                                  if p["id"] not in known_panes)
                assert len(attached_clients()) == 2
                assert listed_clients()[0][1] == f"terminal_{left}"
                (work / "query-blocked").unlink()
                (work / "query-release").unlink()
                (work / "query-armed").write_text("list-clients")
                terminal.send(b"\x08")
                terminal.until("navigation waits for client ownership", lambda:
                               (work / "query-blocked").exists())
                second_client.send(b"j")
                (work / "query-release").touch()
                terminal.until("ambiguous navigation is rejected", lambda:
                               "needs one attached client" in terminal.action(
                                   "dump-screen", "--pane-id", str(left)))
                terminal.send(b"\r")
                terminal.until("editor dismisses the navigation warning", lambda:
                               editor('winnr("$")') == "3")
                assert len(listed_clients()) == 1, "Navigation moved the omitted scrollback client"
                assert next(p for p in terminal.terminals() if p["id"] == scrollback)["is_focused"]
                second_client.send(b"\x1b:q!\r")
                terminal.until("scrollback closes and restores the shell", lambda:
                               all(p["id"] != scrollback for p in terminal.terminals()) and
                               any(p["id"] == right for p in terminal.terminals()))
                second_client.prefix(b"d")
                terminal.until("second client detaches", lambda: len(attached_clients()) == 1)
            finally:
                (work / "query-release").touch()
                second_client.close()

            # Foreground TUIs receive these same bytes rather than having their
            # own controls globally intercepted by the multiplexer.
            raw = work / "raw.py"
            ready, received = work / "raw-ready", work / "raw-input"
            raw.write_text('''import os, pathlib, termios, tty
state = termios.tcgetattr(0)
try:
    tty.setraw(0)
    pathlib.Path(os.environ["RAW_READY"]).touch()
    data = b""
    while len(data) < 4:
        data += os.read(0, 4 - len(data))
    pathlib.Path(os.environ["RAW_INPUT"]).write_bytes(data)
finally:
    termios.tcsetattr(0, termios.TCSADRAIN, state)
''')
            terminal.prefix(b"l")
            terminal.until("focus the right shell", lambda: focused() == right)
            command = shlex.join(["env", f"RAW_READY={ready}", f"RAW_INPUT={received}", "python3", str(raw)])
            terminal.send((command + "\r").encode())
            terminal.until("foreground application is reading keys", ready.exists)
            terminal.send(b"\x08\x0a\x0b\x0c")
            terminal.until("foreground application receives all four control keys", lambda:
                           received.exists() and received.read_bytes() == b"\x08\x0a\x0b\x0c")
            assert focused() == right
            print("PASS: installed navigation preserves editor modes/zoom and application keys; "
                  "delayed requests cannot use inactive-tab focus or an omitted scrollback client.")
        except Exception:
            print("Pane state:", terminal.panes())
            print("Focused screen:", terminal.action("dump-screen"))
            raise
        finally:
            (work / "query-release").touch()
            subprocess.run([binary, "kill-session", name], env=env, capture_output=True, timeout=5)
            terminal.close()
        nested_workflow(binary, env, work, init)


if __name__ == "__main__":
    main()
