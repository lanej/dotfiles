#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte==0.8.2"]
# ///
"""Exercise the dotfiles Hop plugin against a real native-copy Zellij runtime."""

import argparse
import base64
import importlib
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unicodedata

ui = importlib.import_module("test-zellij-command-prompt")
workflow = importlib.import_module("test-zellij")
ROOT = workflow.ROOT


def configuration():
    source = (ROOT / "zellij/config.kdl").read_text()
    bindings = ui.block(source, r"keybinds\b")
    prefix = ui.block(bindings, r"\btmux\s*\{")
    alias = re.search(r'^\s*copy-hop location=.*$', ui.block(source, r"\bplugins\s*\{"), re.M).group().strip()
    autoload = re.search(r'^\s*copy-hop\s*$', ui.block(source, r"\bload_plugins\s*\{"), re.M).group().strip()
    return '\n'.join([
        'default_mode "locked"', 'default_shell "/bin/sh"', 'default_layout "test"',
        'show_startup_tips false', 'show_release_notes false', 'session_serialization false',
        'pane_frames true', 'pane_frame_style "full"', 'mouse_mode false',
        'plugins { ' + alias + '\n}',
        'load_plugins { ' + autoload + '\n}',
        'keybinds clear-defaults=true {', ui.block(bindings, r'\blocked\s*\{'),
        'tmux {', ui.block(prefix, r'bind "\["'), ui.block(prefix, r'bind "c"'), '}',
        ui.block(bindings, r'\bcopy\s*\{'), '}',
    ]) + '\n'


def fixture(terminal, content):
    escaped = content.replace('\\', '\\\\').replace("'", "'\\''").replace('\n', '\\n')
    terminal.send(("printf '\\033[3J\\033[2J\\033[H" + escaped + "\\nREADY\\n'\r").encode())
    terminal.until('fixture rendered', lambda: 'READY' in ui.text(terminal) and unicodedata.normalize('NFC', content.split('\n')[0]) in unicodedata.normalize('NFC', ui.text(terminal)))
    terminal.prefix(b'[')
    terminal.until('native copy active', lambda: 'COPY' in ui.text(terminal))


def begin(terminal, character):
    terminal.send(b's')
    terminal.until('plugin captures jump input', lambda: 'JUMP' in ui.text(terminal))
    terminal.send(character)


def copied(terminal, keys, expected):
    offset = len(terminal.output)
    terminal.send(keys)
    osc = b'\x1b]52;c;' + base64.b64encode(expected.encode()) + b'\x1b\\'
    terminal.until('native clipboard contains ' + repr(expected), lambda: osc in terminal.output[offset:])
    terminal.until('copy returns to shell', lambda: 'JUMP' not in ui.text(terminal) and 'VISUAL' not in ui.text(terminal) and 'COPY' not in ui.text(terminal))


def exercise(terminal):
    original = {pane['id'] for pane in terminal.terminals()}
    fixture(terminal, 'alpha beta gamma')
    terminal.send(b'kk0wv')
    begin(terminal, b'a')
    terminal.until('Hop labels on original pane', lambda: 'etd gfmmg' in ui.text(terminal))
    artifacts = os.environ.get('ZELLIJ_TEST_ARTIFACTS')
    if artifacts:
        directory = Path(artifacts) / 'copy-hop'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'labels.txt').write_text(ui.text(terminal))
        (directory / 'labels.bin').write_bytes(terminal.output)
    copied(terminal, b'dy', 'beta')

    fixture(terminal, 'alpha beta gamma')
    terminal.send(b'kk0wv')
    terminal.send(b's')
    terminal.until('next jump captures input', lambda: 'JUMP' in ui.text(terminal))
    copied(terminal, b'adhy', 'bet')

    fixture(terminal, '界e\u0301 beta')
    terminal.send(b'kk0v')
    begin(terminal, b'e')
    terminal.until('wide and combining cells keep label coordinates', lambda: 'a bsta' in ui.text(terminal))
    copied(terminal, b'ay', '界e\u0301')

    fixture(terminal, 'x ' * 30)
    terminal.send(b'kk0v')
    begin(terminal, b'x')
    terminal.until('first label page', lambda: 's d f g h j k' in ui.text(terminal))
    terminal.send(b'\t')
    terminal.until('second label page', lambda: 'x x x x a s d f' in ui.text(terminal))
    copied(terminal, b'ay', 'x ' * 26 + 'x')

    fixture(terminal, 'alpha beta gamma')
    terminal.send(b'kk0')
    begin(terminal, b'!')
    terminal.until('no matches cancels jump', lambda: 'JUMP' not in ui.text(terminal))
    begin(terminal, b'a')
    terminal.until('labels before Escape', lambda: 'etd gfmmg' in ui.text(terminal))
    terminal.send(b'\x1b')
    terminal.until('Escape preserves native copy', lambda: 'JUMP' not in ui.text(terminal) and 'COPY' in ui.text(terminal))
    copied(terminal, b'0wvey', 'beta')
    assert {pane['id'] for pane in terminal.terminals()} == original
    assert len(original) == 1, 'Selection must stay in its original terminal pane'
    print('PASS: Hop labels, rapid input, Unicode, paging, cancellation and native OSC52 copy without an editor.')


def exercise_clients(first, second):
    second.prefix(b'c')
    second.until('second client owns a separate tab', lambda:
                 len(second.tabs()) == 2 and workflow.PROMPT.decode().strip() in ui.text(second))
    fixture(first, 'alpha beta gamma')
    first.send(b'kk0wv')
    fixture(second, 'bravo delta bravo')
    second.send(b'kk0wv')
    begin(second, b'a')
    second.until('second client labels its own text', lambda: 'bravo delts brdvo' in ui.text(second))
    first.drain()
    assert 'JUMP' not in ui.text(first), 'Starting a jump must not capture the other client'
    begin(first, b'a')
    first.until('first client labels its own text', lambda: 'etd gfmmg' in ui.text(first))
    second.until('first jump preserves second client labels', lambda: 'bravo delts brdvo' in ui.text(second))
    first_offset = len(first.output)
    copied(second, b'sy', 'delta')
    first.drain()
    assert b'\x1b]52;c;' not in first.output[first_offset:], 'Copy must stay on its originating client'
    first.until('second copy preserves first jump', lambda: 'etd gfmmg' in ui.text(first))
    copied(first, b'dy', 'beta')

    config = Path(first.env['HOME']) / '.config/zellij/config.kdl'
    config.write_text(configuration().replace('tmux {',
                      'tmux {\n bind "n" { NewTab; SwitchToMode "Locked"; }\n'))

    def reloaded_tab():
        if len(first.tabs()) < 3:
            first.prefix(b'n')
        return len(first.tabs()) >= 3

    first.until('configuration watcher installs the new tab shortcut', reloaded_tab)
    first.until('reconfigured tab shell ready', lambda: workflow.PROMPT.decode().strip() in ui.text(first))
    fixture(first, 'alpha beta gamma')
    first.send(b'kk0wv')
    begin(first, b'a')
    first.until('private binding recovers after reconfiguration', lambda: 'etd gfmmg' in ui.text(first))
    copied(first, b'dy', 'beta')
    print('PASS: two clients keep independent labels, keyboard capture and clipboard; reconfiguration restores routing.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', default=os.environ.get('ZELLIJ_TEST_ZELLIJ_BIN', shutil.which('zellij')))
    parser.add_argument('--plugin', type=Path, default=Path(os.environ.get('ZELLIJ_COPY_HOP_WASM', Path.home() / '.local/share/zellij/plugins/copy-hop.wasm')))
    args = parser.parse_args()
    assert args.binary, 'Install the native-copy API runtime first'
    plugin = args.plugin.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='zj-copy-hop-', dir='/tmp') as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / 'home', work / 'run', work / 'tmp'
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, 'HOME': str(home), 'SHELL': '/bin/sh', 'PS1': workflow.PROMPT.decode(),
               'TERM': 'xterm-256color', 'XDG_CONFIG_HOME': str(home / '.config'),
               'XDG_CACHE_HOME': str(work / 'cache'), 'XDG_DATA_HOME': str(work / 'data'),
               'XDG_STATE_HOME': str(work / 'state'), 'XDG_RUNTIME_DIR': str(runtime),
               'ZELLIJ_SOCKET_DIR': str(runtime), 'TMPDIR': str(temporary)}
        for key in ('ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'ZELLIJ_CONFIG_DIR',
                    'ZELLIJ_CONFIG_FILE', 'TMUX', 'TMUX_PANE', 'ENV', 'BASH_ENV'):
            env.pop(key, None)
        installed = home / '.local/share/zellij/plugins/copy-hop.wasm'
        installed.parent.mkdir(parents=True)
        installed.symlink_to(plugin)
        config = home / '.config/zellij'
        (config / 'layouts').mkdir(parents=True)
        (config / 'config.kdl').write_text(configuration())
        (config / 'layouts/test.kdl').write_text('layout { pane; }\n')
        subprocess.run([args.binary, 'setup', '--check'], env=env, check=True, capture_output=True)
        name = 'hop-' + work.name
        terminal = workflow.Terminal(args.binary, env, name,
                                     [args.binary, 'attach', '--create', name, '--', '/bin/sh'],
                                     install_navigation=False)
        second = None
        try:
            terminal.until('plugin requests consent', lambda: '(y/n)' in ui.text(terminal).lower())
            terminal.send(b'y')
            terminal.until('shell ready', lambda: workflow.PROMPT.decode().strip() in ui.text(terminal) and '(y/n)' not in ui.text(terminal).lower())
            exercise(terminal)
            second = workflow.Terminal(args.binary, env, name,
                                       [args.binary, 'attach', name, '--', '/bin/sh'],
                                       install_navigation=False)
            second.until('second client ready', lambda: workflow.PROMPT.decode().strip() in ui.text(second))
            exercise_clients(terminal, second)
        except Exception:
            print("Terminal grid at failure:\n" + ui.text(terminal), flush=True)
            if second is not None:
                print("Second client grid at failure:\n" + ui.text(second), flush=True)
            raise
        finally:
            subprocess.run([args.binary, 'kill-session', name], env=env, capture_output=True, timeout=5)
            if second is not None:
                second.close()
            terminal.close()


if __name__ == '__main__':
    main()
