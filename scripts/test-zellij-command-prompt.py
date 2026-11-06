#!/usr/bin/env python3
"""Exercise the installed native command prompt with two real Zellij clients.

Requires the pinned Zellij fork, pyte 0.8.2, and the installer's Rust WASM toolchain.
Only this test's HOME, session, permissions and sockets are used. No shell or
status/navigation plugin from the user's environment is loaded.
"""

import codecs
import importlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import pyte

workflow = importlib.import_module("test-zellij")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


def block(text, start):
    """Extract a KDL node, retaining the production action rather than a copy."""
    begin = re.search(start, text).start()
    depth = 0
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|//[^\n]*|[{}]', text[begin:]):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return text[begin:begin + token.end()]
    raise AssertionError("Unclosed KDL node")


def configuration():
    source = (ROOT / "zellij/config.kdl").read_text()
    bindings = block(source, r"keybinds\b")
    tmux = block(bindings, r"\btmux\s*\{")
    keys = [block(tmux, rf'bind "{re.escape(key)}"') for key in (":", "c", "v", "h", "l")]
    alias = re.search(r'^\s*command-prompt location=.*$', block(source, r"\bplugins\s*\{"), re.M).group().strip()
    load = re.search(r'^\s*command-prompt\s*$', block(source, r"\bload_plugins\s*\{"), re.M).group().strip()
    # Restrict unrelated startup work, but consume the real installed plugin's
    # alias, autoload entry, prefix transition, and command binding unchanged.
    return '\n'.join([
        'default_mode "locked"', 'default_shell "/bin/sh"',
        'default_layout "test"', 'show_startup_tips false',
        'show_release_notes false', 'session_serialization false',
        'pane_frames true', 'mouse_mode false',
        'plugins { ' + alias + '\n}', 'load_plugins { ' + load + '\n}',
        'keybinds clear-defaults=true {', block(bindings, r'\blocked\s*\{'),
        'tmux {', *keys, 'bind "Esc" { SwitchToMode "Locked"; }', '}', '}',
    ]) + '\n'


class Display(pyte.Screen):
    def report_device_status(self, mode, **kwargs):
        if not kwargs.get("private"):
            super().report_device_status(mode)


def screen(terminal):
    # Use the same terminal decoder as the native status detector. Preserve
    # cursor state between updates, including UTF-8 split across PTY reads.
    if not hasattr(terminal, "command_display"):
        display = Display(120, 32)
        terminal.command_display = [display, pyte.Stream(display),
            codecs.getincrementaldecoder("utf-8")("replace"), 0]
    display, stream, decoder, offset = terminal.command_display
    stream.feed(decoder.decode(bytes(terminal.output[offset:])))
    terminal.command_display[3] = len(terminal.output)
    return display.display


def text(terminal):
    return '\n'.join(screen(terminal))


def open_prompt(terminal):
    original_terminals = {p['id'] for p in terminal.terminals()}
    terminal.prefix(b":")
    terminal.until("Ctrl-f : opens native input", lambda: "Zellij command" in text(terminal))
    title_rows = [row for row, line in enumerate(screen(terminal)) if "Zellij command" in line]
    assert title_rows and all(7 <= row <= 23 for row in title_rows), 'Prompt is not vertically centered'
    assert all(10 <= screen(terminal)[row].index('Zellij command') <= 90
               for row in title_rows), 'Prompt is not horizontally centered'
    # A native prompt renders over the existing panes; it must not create a
    # shell popup or reveal a suppressed plugin pane.
    assert {p['id'] for p in terminal.terminals()} == original_terminals, 'Prompt opened a shell pane'


def submit(terminal, command, bystander=None):
    open_prompt(terminal)
    terminal.send(command.encode())
    if bystander is not None:
        # Make the other client active both before submission and while the
        # prompt result is dispatched asynchronously, without first waiting for
        # the requesting client's action/render to finish.
        bystander.send(b"\x15")
        os.write(terminal.fd, b"\r")
        bystander.send(b"\x15")
        terminal.drain()
    else:
        terminal.send(b"\r")


def exercise(first, second, home):
    first.until("first shell starts", lambda: PROMPT.rstrip() in first.output)
    first.prefix(b'v')
    first.until("two starting panes", lambda: len(first.terminals()) == 2)
    first.prefix(b'h')
    first.drain(0.2)
    panes = sorted(first.terminals(), key=lambda pane: pane['pane_x'])
    left, right = panes[0]['id'], panes[1]['id']
    initial_tab = panes[0]['tab_id']

    def pane(pane_id):
        return next(p for p in first.terminals() if p['id'] == pane_id)

    def tabs():
        return {t['tab_id']: t for t in first.tabs()}

    second.until("second client attaches", lambda: PROMPT.rstrip() in second.output)
    # A new client may need its own grant and binding registration.
    if '(y/n)' in text(second).lower():
        second.send(b'y')
    second.prefix(b'c')
    first.until("second client's private tab", lambda: len(first.tabs()) == 2)
    other_pane = next(p for p in first.terminals() if p['tab_id'] != initial_tab and p['title'] == 'template-left')
    other_id, other_tab = other_pane['id'], other_pane['tab_id']

    submit(first, 'rename-pane "hello world"', second)
    first.until("quoted name applies to requesting pane", lambda: pane(left)['title'] == 'hello world')
    assert pane(other_id)['title'] != 'hello world'
    submit(second, 'rename-pane "other client"', first)
    first.until("second client owns its action", lambda: pane(other_id)['title'] == 'other client')
    assert pane(left)['title'] == 'hello world'

    submit(first, 'move-focus right', second)
    submit(first, 'rename-pane "moved right"', second)
    first.until("move-focus belongs to requester", lambda: pane(right)['title'] == 'moved right')
    submit(first, 'new-pane --direction right', second)
    first.until("new-pane belongs to requester tab", lambda:
                len([p for p in first.terminals() if p['tab_id'] == initial_tab]) == 3)
    assert len([p for p in first.terminals() if p['tab_id'] == other_tab]) == 2
    submit(first, 'rename-tab "first named tab"', second)
    first.until("rename-tab uses requester", lambda: tabs()[initial_tab]['name'] == 'first named tab')
    submit(second, 'rename-tab "second named tab"', first)
    first.until("second rename-tab uses requester", lambda: tabs()[other_tab]['name'] == 'second named tab')
    assert tabs()[initial_tab]['name'] == 'first named tab'

    # The quoted payload must be literal, even when it resembles shell syntax.
    literal = '$(touch ' + str(home / 'SHOULD-NOT-EXIST') + '); hello'
    submit(first, 'rename-pane "' + literal + '"', second)
    first.until("shell-looking text remains a pane name", lambda: any(p['title'] == literal for p in first.terminals()))
    assert not (home / 'SHOULD-NOT-EXIST').exists()

    # Prepare an existing float using the command itself, then hide it. Neither
    # opening a native overlay nor cancel/retry/help/history may show it again.
    submit(first, 'new-pane --floating', second)
    first.until("existing floating pane created", lambda: any(p['is_floating'] for p in first.terminals()))
    submit(first, 'toggle-floating-panes', second)
    first.until("existing floating pane hidden", lambda: not tabs()[initial_tab]['are_floating_panes_visible'])
    original = {p['id'] for p in first.terminals()}

    def unchanged():
        assert {p['id'] for p in first.terminals()} == original
        assert not tabs()[initial_tab]['are_floating_panes_visible'], 'Prompt revealed existing float'

    open_prompt(first)
    unchanged()
    first.send(b'rename-tab "cancelled"\x1b')
    first.drain(0.2)
    unchanged()
    assert tabs()[initial_tab]['name'] == 'first named tab'
    open_prompt(first)
    first.send(b'rename-pane "unterminated\r')
    first.until("invalid syntax reopens with an error", lambda:
                'unterminated' in text(first).lower() and 'Unclosed quote' in text(first))
    unchanged()
    first.send(b'\x1b')
    for command, result in (('help', 'move-focus'), ('history', 'toggle-floating-panes')):
        submit(first, command, second)
        first.until(command + " is displayed", lambda: result in text(first))
        unchanged()
        first.send(b'\r')
        guidance = 'Review the command' if command == 'history' else 'Add arguments'
        first.until(command + ' selection returns to editable input', lambda: guidance in text(first))
        unchanged()
        first.send(b'\x1b')
    submit(first, 'rename-tab "reopened successfully"', second)
    first.until("prompt remains reusable", lambda: tabs()[initial_tab]['name'] == 'reopened successfully')
    unchanged()
    # CLI-only variants must return an error instead of panicking in run_action.
    for command, message in (
        ('rename-pane --pane-id 9999 blocked', 'CLI-only actions'),
        ('new-pane --near-current-pane', 'terminal-pane origin'),
        ('new-tab --initial-plugin file:/not-a-plugin.wasm', 'external plugins'),
        ('definitely-not-a-command', 'Unknown or unsupported command'),
    ):
        submit(first, command, second)
        first.until('unsupported variant remains editable: ' + command, lambda: message in text(first))
        unchanged()
        first.send(b'\x1b')
    submit(first, 'rename-pane --help', second)
    first.until('native action help is displayed', lambda: 'Usage:' in text(first))
    first.send(b'\x1b')
    open_prompt(first)
    first.send(b'\r')
    first.until('empty input closes', lambda: 'Zellij command' not in text(first))
    unchanged()

    submit(second, 'history', first)
    second.until('history belongs to second client', lambda: 'second named tab' in text(second))
    assert 'toggle-floating-panes' not in text(second), 'History leaked from first client'
    second.send(b'\x1b')

    # Reload an observable ordinary binding in both clients, then verify the
    # plugin's private binding is restored independently for both of them.
    config = home / '.config/zellij/config.kdl'
    refreshed = configuration().replace('locked {', 'locked {\n bind "Ctrl r" { WriteChars "reload-observed"; }', 1)
    config.write_text(refreshed)
    for client in (first, second):
        def reload_observed():
            client.send(b'\x12')
            return 'reload-observed' in text(client)
        client.until('client observes configuration reload', reload_observed)
        client.send(b'\x15')
    submit(first, 'rename-tab "first after reload"', second)
    first.until('first binding survives reload', lambda: tabs()[initial_tab]['name'] == 'first after reload')
    submit(second, 'rename-tab "second after reload"', first)
    first.until('second binding survives reload', lambda: tabs()[other_tab]['name'] == 'second after reload')

    # NewTab must retain the session's configured template, including its pane
    # names and split, even though no layout file is loaded from WASM.
    submit(first, 'new-tab --name "layout proof"', second)
    first.until('new-tab uses requester', lambda: any(t['name'] == 'layout proof' for t in first.tabs()))
    created = next(t['tab_id'] for t in first.tabs() if t['name'] == 'layout proof')
    first.until('new-tab retains the default two-pane template', lambda:
                {p['title'] for p in first.terminals() if p['tab_id'] == created} == {'template-left', 'template-right'})
    submit(first, 'rename-pane "new tab requester"', second)
    first.until('new tab focus belongs to requester', lambda: any(
        p['tab_id'] == created and p['title'] == 'new tab requester' for p in first.terminals()))

    # Close the tab that originally held the autoloaded plugin, then reuse the
    # binding from both remaining clients. The plugin must outlive its old tab.
    submit(first, 'go-to-tab 1', second)
    submit(first, 'close-tab', second)
    first.until('owning tab closes', lambda: initial_tab not in tabs())
    submit(first, 'rename-pane "survived owning tab"', second)
    first.until('first prompt survives owning-tab closure', lambda: any(
        p['title'] == 'survived owning tab' for p in first.terminals()))
    submit(second, 'rename-tab "still client two"', first)
    first.until('second prompt survives owning-tab closure', lambda: tabs()[other_tab]['name'] == 'still client two')
    # A tab can disappear while its prompt is awaiting input. The stale command
    # must not land in the replacement tab, and the binding must remain usable.
    submit(first, 'go-to-tab-name "layout proof"', second)
    open_prompt(first)
    first.send(b'rename-tab "must not run"')
    second.action('close-tab', '--tab-id', str(created))
    first.until('prompt origin is closed externally', lambda: created not in tabs())
    first.send(b'\r')
    first.drain(0.3)
    assert all(t['name'] != 'must not run' for t in first.tabs())
    # Some native versions show the stale-origin notice; dismiss it before
    # exercising a fresh command, while also accepting automatic cancellation.
    first.send(b'\x1b')
    submit(first, 'rename-tab "recovered after interruption"', second)
    first.until('interrupted prompt recovers', lambda:
                tabs()[other_tab]['name'] == 'recovered after interruption')
    print('PASS: unsupported actions, action help, empty input, client config reload, '
          'default new-tab template, owning-tab closure, and interrupted-origin recovery.')

    print('PASS: native command entry, quoted/literal arguments, client-bound pane/tab actions, '
          'cancel/error/reopen/help/history, and hidden floats with two attached clients.')


def main():
    binary = shutil.which('zellij')
    assert binary, 'Install the pinned Zellij fork before testing the command prompt'
    with tempfile.TemporaryDirectory(prefix='zj-cmd-', dir='/tmp') as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / 'home', work / 'run', work / 'tmp'
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, 'HOME': str(home), 'SHELL': '/bin/sh', 'PS1': PROMPT.decode(),
               'TERM': 'xterm-256color', 'XDG_CONFIG_HOME': str(home / '.config'),
               'XDG_CACHE_HOME': str(work / 'cache'), 'XDG_DATA_HOME': str(work / 'data'),
               'XDG_STATE_HOME': str(work / 'state'), 'XDG_RUNTIME_DIR': str(runtime),
               'ZELLIJ_SOCKET_DIR': str(runtime), 'TMPDIR': str(temporary)}
        workflow.preserve_rust_homes(env)
        for key in ('ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'ZELLIJ_CONFIG_DIR',
                    'ZELLIJ_CONFIG_FILE', 'TMUX', 'TMUX_PANE', 'ENV', 'BASH_ENV'):
            env.pop(key, None)
        build_cache = os.environ.get('ZELLIJ_TEST_BUILD_CACHE')
        if build_cache:
            cache = Path(build_cache).resolve()
            cache.mkdir(parents=True, exist_ok=True)
            link = Path(env['XDG_CACHE_HOME']) / 'dotfiles/zellij-command-prompt'
            link.parent.mkdir(parents=True)
            link.symlink_to(cache, target_is_directory=True)
        subprocess.run([sys.executable, str(ROOT / 'scripts/install-zellij-command-prompt.py')],
                       cwd=ROOT, env=env, check=True)
        config = home / '.config/zellij'
        (config / 'layouts').mkdir(parents=True)
        (config / 'config.kdl').write_text(configuration())
        (config / 'layouts/test.kdl').write_text('''layout {
    tab { pane; }
    new_tab_template {
        pane split_direction="vertical" {
            pane name="template-left" focus=true
            pane name="template-right"
        }
    }
}
''')
        subprocess.run([binary, 'setup', '--check'], env=env, check=True, capture_output=True)
        name = 'command-' + work.name
        clients = []
        try:
            first = Terminal(binary, env, name, install_navigation=False)
            clients.append(first)
            # Attach only after first-use consent, otherwise the permission
            # prompt's own focus can interfere with setting up the two clients.
            first.until('first-use permissions', lambda: '(y/n)' in text(first).lower())
            first.send(b'y')
            first.until('first shell ready', lambda: PROMPT.rstrip() in first.output)
            second = Terminal(binary, env, name, install_navigation=False)
            clients.append(second)
            exercise(first, second, home)
        finally:
            subprocess.run([binary, 'kill-session', name], env=env, capture_output=True, timeout=5)
            for client in clients:
                client.close()


if __name__ == '__main__':
    main()
