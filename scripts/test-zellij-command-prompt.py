#!/usr/bin/env python3
"""Exercise the installed native command prompt with two real Zellij clients.

Requires the pinned Zellij fork, pyte 0.8.2, and the installer's Rust WASM toolchain.
The independent --session-keys mode also needs make zellij-status.
Only this test's HOME, session, permissions and sockets are used. No shell or
status/navigation plugin from the user's environment is loaded.
"""

import argparse
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


def configuration(session_keys=False):
    source = (ROOT / "zellij/config.kdl").read_text()
    bindings = block(source, r"keybinds\b")
    tmux = block(bindings, r"\btmux\s*\{")
    selected = ("C", "w", "P", "k", "j", "c") if session_keys else (":", "c", "v", "h", "l")
    keys = [block(tmux, rf'bind "{re.escape(key)}"') for key in selected]
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
        'tmux {', *keys, 'bind "Esc" { SwitchToMode "Locked"; }', '}',
        block(bindings, r'\brenamesession\s*\{') if session_keys else '', '}',
    ]) + '\n'


class Display(pyte.Screen):
    def report_device_status(self, mode, **kwargs):
        if not kwargs.get("private"):
            super().report_device_status(mode)


class Decoder:
    def __init__(self):
        self.display = Display(120, 32)
        self.stream = pyte.Stream(self.display)
        self.utf8 = codecs.getincrementaldecoder("utf-8")("replace")
        self.pending = ""
        self.offset = 0

    def feed(self, data):
        # pyte does not implement DCS. Zellij's attachment metadata (ESC P
        # 26661n ... ST) must not draw over the popup or move the screen cursor.
        # Retain incomplete strings and ESC prefixes across arbitrary PTY reads.
        self.pending += self.utf8.decode(data)
        while self.pending:
            start = self.pending.find("\x1bP")
            if start < 0:
                end = len(self.pending) - int(self.pending.endswith("\x1b"))
                self.stream.feed(self.pending[:end])
                self.pending = self.pending[end:]
                break
            self.stream.feed(self.pending[:start])
            self.pending = self.pending[start:]
            end = self.pending.find("\x1b\\", 2)
            if end < 0:
                break
            self.pending = self.pending[end + 2:]


def screen(terminal):
    if not hasattr(terminal, "command_display"):
        terminal.command_display = Decoder()
    decoder = terminal.command_display
    decoder.feed(bytes(terminal.output[decoder.offset:]))
    decoder.offset = len(terminal.output)
    return decoder.display.display


def check_decoder():
    # Reproduce CI's metadata after a dialog render, including chunk boundaries
    # inside ESC/ST and UTF-8. The message must neither draw nor move the cursor.
    rendered = '\x1b[12;32HZellij command :\x1b[12;32H'
    metadata = '\x1bP26661nCh0KF2NvbW1hbmQ=\x1b\\'
    data = (rendered + metadata + '\x1b[14;32H→ editable').encode()
    for size in (1, 7, len(data)):
        decoder = Decoder()
        for offset in range(0, len(data), size):
            decoder.feed(data[offset:offset + size])
        assert decoder.display.display[11][31:47] == 'Zellij command :'
        assert decoder.display.display[13][31:41] == '→ editable'
        assert '26661n' not in '\n'.join(decoder.display.display)


def text(terminal):
    return '\n'.join(screen(terminal))


def open_prompt(terminal):
    # Esc and accepted actions close asynchronously. A stale title must not
    # satisfy the next open and let its keystrokes enter the previous dialog.
    terminal.until("previous command dialog closes", lambda: "Zellij command" not in text(terminal))
    original_terminals = {p['id'] for p in terminal.terminals()}
    terminal.prefix(b":")
    try:
        terminal.until("Ctrl-f : opens native input", lambda: "Zellij command" in text(terminal))
    except AssertionError:
        print("Decoded prompt screen:\n" + text(terminal), flush=True)
        raise
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
    second.until('history dialog closes before reload', lambda: 'Zellij command' not in text(second))

    # Reload an observable ordinary binding in both clients, then verify the
    # plugin's private binding is restored independently for both of them.
    # Observe native tab state, not shell echo: Ctrl-r before the reload enters
    # Bash's reverse search and its display can obscure subsequently typed text.
    config = home / '.config/zellij/config.kdl'
    marker = 'reload-observed'
    name_bytes = ' '.join(str(byte) for byte in marker.encode())
    binding = f'\n bind "Ctrl r" {{ TabNameInput 0; TabNameInput {name_bytes}; }}'
    refreshed = configuration().replace('locked {', 'locked {' + binding, 1)
    config.write_text(refreshed)
    for client, tab_id in ((first, initial_tab), (second, other_tab)):
        def reload_observed():
            client.send(b'\x12')
            return tabs()[tab_id]['name'] == marker
        client.until('client observes configuration reload', reload_observed)
        client.send(b'\x03')
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


def sessions(client):
    result = subprocess.run([client.binary, 'list-sessions', '--short', '--no-formatting'],
                            env=client.env, capture_output=True, text=True, timeout=5)
    result.check_returncode()
    return set(result.stdout.splitlines())


def exercise_session_keys(first, second, home, clients):
    """Use the real keys, shell identities and native clients, not plugin messages."""
    original = first.name
    second.until('second client attaches', lambda: PROMPT.decode().strip() in text(second))
    if '(y/n)' in text(second).lower():
        second.send(b'y')

    def grant_bar(client):
        # A switching PTY still contains its earlier command-plugin consent.
        # Inspect the current screen rather than that stale output history.
        ready = lambda: re.search(r'!\d+ ●\d+', text(client))
        client.until('current session status consent or live bar', lambda:
                     '(y/n)' in text(client).lower() or ready())
        if '(y/n)' in text(client).lower():
            client.prefix(b'k')
            client.send(b'y')
        client.until('current session status bar is ready', ready)

    def client_count(name):
        return len(first.action('list-clients', session=name).strip().splitlines()[1:])

    def shell_probe(client, label):
        path = home / label
        client.send(("printf '%s\\n' \"$ZELLIJ_SESSION_NAME\" \"$$\" \"$PWD\" > "
                     + str(path) + '\r').encode())
        client.until('shell identity ' + label, lambda: path.exists() and len(path.read_text().splitlines()) == 3)
        name, pid, cwd = path.read_text().splitlines()
        return name, int(pid), cwd

    first.until('two original clients', lambda: client_count(original) == 2)
    focused = home / 'focused-cwd'
    focused.mkdir()
    first.send(('cd ' + str(focused) + '\r').encode())
    _, old_pid, old_cwd = shell_probe(first, 'original-shell')
    assert old_cwd == str(focused)
    original_panes = {p['id'] for p in first.terminals()}

    def create(client, bystander, label):
        before = sessions(client)
        # Keep the other client active around the asynchronous private dispatch.
        bystander.send(b'\x15')
        os.write(client.fd, b'\x06C')
        bystander.send(b'\x15')
        created = client.until('Ctrl-f C immediately creates an unnamed session',
                               lambda: sessions(client) - before)
        assert len(created) == 1, created
        name = created.pop()
        client.until('requesting client attaches to generated session', lambda: client_count(name) == 1)
        client.name = name
        client.until('new session terminal is ready', lambda: len(client.terminals()) == 1)
        grant_bar(client)
        client.prefix(b'j')
        client.drain(0.3)
        actual, pid, cwd = shell_probe(client, label)
        assert actual == name, 'C switched a different client or left a chooser open'
        assert pid != old_pid
        assert any(p['is_plugin'] for p in client.panes()), 'C did not load the regular tmux layout'
        return name, pid, cwd

    created, _, cwd = create(first, second, 'new-shell')
    assert cwd == str(focused), 'New session lost the requesting pane cwd'
    assert client_count(original) == 1
    name, pid, _ = shell_probe(second, 'bystander-shell')
    assert (name, pid) == (original, old_pid), 'Bystander moved or original shell restarted'
    assert {p['id'] for p in second.terminals()} == original_panes
    os.kill(old_pid, 0)

    # RenameSession edits are private drafts until Enter. They neither create
    # a shell/picker pane nor rename the live session as each byte is entered.
    observer = Terminal(first.binary, first.env, created, install_navigation=False)
    clients.append(observer)
    observer.until('rename observer attaches', lambda: PROMPT.decode().strip() in text(observer))
    grant_bar(observer)
    before = sessions(first)
    pane_ids = {p['id'] for p in first.terminals()}
    renamed = created + '-renamed'
    first.prefix(b'w')
    first.send(renamed.encode())
    first.until('status bar shows native rename draft', lambda:
                'RENAME SESSION: ' + renamed in text(first))
    assert {p['id'] for p in first.terminals()} == pane_ids, 'w opened a shell picker'
    observer.prefix(b'c')
    observer.until('second client metadata broadcast', lambda: len(observer.tabs()) == 2)
    first.drain(0.3)
    observer.drain(0.2)
    assert 'RENAME SESSION: ' + renamed in text(first), 'Session update erased draft'
    assert renamed not in text(observer), 'Rename draft leaked to bystander'
    assert sessions(first) == before, 'Rename draft changed live names before Enter'
    first.send(b'\r')
    first.until('Enter commits session rename', lambda: renamed in sessions(first) and created not in sessions(first))
    first.name = renamed
    observer.name = renamed
    first.until('rename UI closes on Enter', lambda: 'RENAME SESSION:' not in text(first))
    for key in (b'\x1b', b'\x03'):
        first.prefix(b'w')
        first.send(b'must-not-be-committed')
        first.until('cancel draft is visible', lambda: 'RENAME SESSION: must-not-be-committed' in text(first))
        first.send(key)
        first.until('rename UI closes on cancel', lambda: 'RENAME SESSION:' not in text(first))
        assert sessions(first) == (before - {created}) | {renamed}, 'Cancelled rename changed session names'
        shell_probe(first, 'cancel-' + key.hex())  # proves return to Locked
    for invalid in ('', 'bad/name', original):
        first.prefix(b'w')
        first.send(invalid.encode() + b'\r')
        first.until('invalid/colliding name displays native error', lambda: 'Could not rename session' in text(first))
        assert 'RENAME SESSION:' not in text(first)
        assert sessions(first) == (before - {created}) | {renamed}, 'Invalid/colliding rename changed names'
        # Dismiss the native rejection notice before the next rename.
        first.send(b'\x1b')
        first.until('rename error notice closes', lambda: 'Could not rename session' not in text(first))
        shell_probe(first, 'rejected-' + str(len(invalid)))
    assert client_count(original) == 1 and client_count(renamed) == 2
    os.kill(old_pid, 0)

    # Start the actual popup launcher on its own PTY to inspect its client
    # directly, without adding a second nested terminal decoder. Its layout
    # overlay is exactly the one used when Ctrl-f P launches it in a float.
    popup_env = {**first.env, 'ZELLIJ_SESSION_NAME': renamed}
    popup = Terminal(first.binary, popup_env, 'dotfiles-popup',
                     [str(ROOT / 'bin/zellij-popup')], install_navigation=False)
    clients.append(popup)
    popup.until('popup shell starts', lambda: PROMPT.decode().strip() in text(popup))
    if '(y/n)' in text(popup).lower():
        popup.send(b'y')
    grant_bar(popup)
    popup.prefix(b'j')
    _, popup_pid, _ = shell_probe(popup, 'popup-shell')
    popup_name, regular_pid, _ = create(popup, second, 'created-from-popup')
    assert client_count('dotfiles-popup') == 0
    os.kill(popup_pid, 0)
    popup.prefix(b'P')
    popup.until('new session uses regular P launcher, not popup detach override', lambda:
                any(p['is_floating'] for p in popup.terminals()) and client_count('dotfiles-popup') == 1)
    # Native list-clients lists visible-pane focus, not every attachment: a
    # descended host can have no rows. Check the actual requesting PTY and its
    # original regular shell instead of treating guest focus as a detach.
    print('Host focused-client rows while descended:\n' + popup.action('list-clients'), flush=True)
    assert os.waitpid(popup.pid, os.WNOHANG) == (0, 0), 'Requesting client exited after P'
    os.kill(regular_pid, 0)
    assert client_count(original) == 1
    os.kill(old_pid, 0)
    os.kill(popup_pid, 0)
    print('PASS: direct C with two clients, preserved shells/cwd, native rename commit/cancel/'
          'validation, and regular layout/P binding after creating from popup.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-keys', action='store_true',
                        help='exercise direct new-session and native rename keys independently')
    args = parser.parse_args()
    check_decoder()
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
        (config / 'config.kdl').write_text(configuration(args.session_keys))
        if args.session_keys:
            # Match managed installation, so C is not intercepted by first-run
            # desktop onboarding (there is no explicit shell command on C).
            subprocess.run([sys.executable, str(ROOT / 'scripts/make/zellij-config.py'),
                            str(home)], env=env, check=True)
            status = ROOT / 'zellij/status/target/wasm32-wasip1/release/lane-status.wasm'
            assert status.exists(), 'Build the status plugin with make zellij-status first'
            (config / 'plugins').mkdir()
            shutil.copyfile(status, config / 'plugins/lane-status.wasm')
            shutil.copyfile(ROOT / 'zellij/layouts/tmux.kdl', config / 'layouts/tmux.kdl')
            env['PATH'] = str(ROOT / 'bin') + os.pathsep + env['PATH']
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
            # An explicit command skips native desktop-install onboarding in a
            # fresh HOME. The actual plugin consent and configured layout remain.
            first = Terminal(binary, env, name,
                             [binary, 'attach', '--create', name, '--', '/bin/sh'],
                             install_navigation=False)
            clients.append(first)
            # Attach only after first-use consent, otherwise the permission
            # prompt's own focus can interfere with setting up the two clients.
            first.until('first-use permissions', lambda: '(y/n)' in text(first).lower())
            first.send(b'y')
            first.until('permission accepted and first shell ready', lambda:
                        PROMPT.decode().strip() in text(first) and '(y/n)' not in text(first).lower())
            second = Terminal(binary, env, name, install_navigation=False)
            clients.append(second)
            if args.session_keys:
                exercise_session_keys(first, second, home, clients)
            else:
                exercise(first, second, home)
        finally:
            names = (sessions(first) | {client.name for client in clients}
                     if args.session_keys and clients else {name})
            for session in names:
                subprocess.run([binary, 'kill-session', '--', session], env=env,
                               capture_output=True, timeout=5)
            for client in clients:
                client.close()


if __name__ == '__main__':
    main()
