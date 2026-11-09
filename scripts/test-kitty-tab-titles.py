"""Exercise title selection with Kitty's real OSC parser and launcher output."""
import importlib.util
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest

from kitty.fast_data_types import Screen, set_options
from kitty.options.types import defaults
from kitty.tab_bar import CustomDrawTitleFunc
from kitty.window import Window

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dotfiles_tab_title', ROOT / 'kitty/tab_bar.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WindowFixture:
    def __init__(self):
        self.user_vars = {}
        self.override_title = None
        self.child = SimpleNamespace(foreground_processes=[])
        self.screen = Screen(self, 20, 90, 100)

    def on_activity_since_last_focus(self):
        pass

    def desktop_notify(self, code, value):
        if code == 1337:
            self.osc_1337(bytes(value).decode())

    def osc_1337(self, value):
        Window.osc_1337(self, value)

    def set_user_var(self, key, value):
        Window.set_user_var(self, key, value)

    def call_watchers(self, *args):
        pass

    watchers = SimpleNamespace(on_set_user_var=[])

    def feed(self, data):
        data = memoryview(data)
        while data:
            written = self.screen.test_commit_write_buffer(data, self.screen.test_create_write_buffer())
            data = data[written:]
            self.screen.test_parse_written_data()


class Titles(unittest.TestCase):
    def setUp(self):
        set_options(defaults)
        self.window = WindowFixture()
        self.tab = SimpleNamespace(active_window=self.window, name='')
        module.get_boss = lambda: SimpleNamespace(tab_for_id=lambda _: self.tab)
        self.accessor = SimpleNamespace(active_exe='zsh')

    def title(self, value):
        data = dict(title=value, tab_id=1, tab=self.accessor)
        return str(CustomDrawTitleFunc(data, module.draw_title))

    def test_local_and_explicit_titles(self):
        self.assertEqual(self.title('editor | file'), 'editor | file')
        self.accessor.active_exe = 'zellij'
        self.assertEqual(self.title('work | editor'), 'work')
        self.assertEqual(self.title('renamed | shell'), 'renamed')
        self.tab.name = 'My tab | custom'
        self.assertEqual(self.title(self.tab.name), self.tab.name)
        self.tab.name = ''
        self.window.override_title = 'My window | custom'
        self.assertEqual(self.title(self.window.override_title), self.window.override_title)

    def test_remote_transport_and_cleanup(self):
        self.window.child.foreground_processes = [dict(pid=44, cmdline=['/usr/bin/ssh', 'host'])]
        self.window.feed(b'\x1b]1337;SetUserVar=dotfiles_zellij=aG9zdC8xLzI=\x07\x1b[?1049h')
        self.assertEqual(self.title('work | editor'), 'host/work')
        self.assertEqual(self.title('renamed | shell'), 'host/renamed')
        self.window.feed(b'\x1b[?1049l')
        self.assertEqual(self.title('shell | normal'), 'shell | normal')
        self.window.feed(b'\x1b[?1049h')
        self.window.child.foreground_processes = [dict(pid=55, cmdline=['ssh', 'other'])]
        self.assertEqual(self.title('vim | file'), 'vim | file')
        self.window.feed(b'\x1b]1337;SetUserVar=dotfiles_zellij=b3RoZXIvMi8z\x07')
        self.assertEqual(self.title('next | shell'), 'other/next')
        self.window.feed(b'\x1b]1337;SetUserVar=dotfiles_zellij\x07')
        self.assertEqual(self.title('vim | file'), 'vim | file')

    def test_launcher_marks_remote_and_preserves_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'zellij'
            fake.write_text('#!/bin/sh\nprintf "args:%s\\n" "$*"\nexit 7\n')
            fake.chmod(0o755)
            env = {**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                   'SSH_CONNECTION': 'test', 'SSH_AUTH_SOCK': '', 'ZELLIJ': '', 'TMUX': ''}
            master, slave = pty.openpty()
            try:
                result = subprocess.run([str(ROOT / 'bin/zellij-attach'), 'work'], env=env, stdout=slave)
                os.close(slave)
                slave = -1
                data = b''
                while True:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    data += chunk
                self.assertEqual(result.returncode, 7)
                self.assertIn(b'args:attach --create work', data)
                self.window.feed(data)
                self.assertNotIn('dotfiles_zellij', self.window.user_vars)
                self.assertIn(b'SetUserVar=dotfiles_zellij=', data)
            finally:
                os.close(master)
                if slave >= 0:
                    os.close(slave)
            result = subprocess.run([str(ROOT / 'bin/zellij-attach')], env=env, capture_output=True)
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stdout, b'args:attach --create main\n')

    def test_launcher_cleans_remote_title_on_termination(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'zellij'
            child_pid = Path(directory) / 'child.pid'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$$" > "$CHILD_PID"\nprintf "attached\\n"\nexec sleep 30\n')
            fake.chmod(0o755)
            env = {**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                   'SSH_CONNECTION': 'test', 'SSH_AUTH_SOCK': '', 'ZELLIJ': '', 'TMUX': '',
                   'CHILD_PID': str(child_pid)}
            master, slave = pty.openpty()
            process = subprocess.Popen([str(ROOT / 'bin/zellij-attach'), 'work'],
                                       env=env, stdout=slave, start_new_session=True)
            os.close(slave)
            try:
                data = b''
                deadline = time.monotonic() + 5
                while b'attached' not in data:
                    remaining = max(0, deadline - time.monotonic())
                    self.assertTrue(select.select([master], [], [], remaining)[0], 'Launcher did not attach')
                    chunk = os.read(master, 4096)
                    self.assertTrue(chunk, 'Launcher exited before attaching')
                    data += chunk
                self.assertIn(b'SetUserVar=dotfiles_zellij=', data)
                process.send_signal(signal.SIGTERM)
                self.assertEqual(process.wait(timeout=5), 128 + signal.SIGTERM)
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(child_pid.read_text()), 0)
                while select.select([master], [], [], 5)[0]:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    data += chunk
                self.assertIn(b'\x1b]1337;SetUserVar=dotfiles_zellij\x07', data)
                self.window.feed(data)
                self.assertNotIn('dotfiles_zellij', self.window.user_vars)
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
                os.close(master)


if __name__ == '__main__':
    unittest.main()
