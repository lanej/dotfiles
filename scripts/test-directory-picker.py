#!/usr/bin/env python3
"""Exercise directory jumps and Git discovery with a controlled picker boundary."""

import base64
import importlib.machinery
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
import io
import json
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
picker = importlib.machinery.SourceFileLoader("directory_picker", str(ROOT / "bin/directory-picker")).load_module()


preview = picker.directory_preview


class PickerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="directory-picker-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.home = self.work / "home"
        self.home.mkdir()
        (self.home / ".files").symlink_to(ROOT)

    def git(self, directory, *args):
        return subprocess.check_output(["git", "-C", str(directory), *args], stderr=subprocess.DEVNULL)

    def repository(self, name):
        repo = self.work / name
        repo.mkdir()
        self.git(repo, "init", "-b", "main")
        self.git(repo, "-c", "user.name=Fixture", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "-m", "fixture")
        return repo

    def test_registered_worktrees_scope_and_literal_paths(self):
        repo = self.repository("first repo")
        other = self.repository("second")
        external = self.work / "outside\tquote'\n"
        self.git(repo, "worktree", "add", "-b", "topic", str(external))
        self.git(repo, "worktree", "lock", str(external))
        nested = repo / "nested"
        nested.mkdir()
        choices = dict(picker.worktrees(nested))
        self.assertEqual(set(choices), {str(repo), str(external)})
        self.assertEqual(choices[str(external)], "first repo · topic · locked")
        self.assertEqual(set(dict(picker.worktrees(self.work))), {str(repo), str(other), str(external)})
        self.git(repo, "-C", str(external), "checkout", "--detach")
        self.assertIn("detached", dict(picker.worktrees(repo))[str(external)])
        shutil.rmtree(external)
        self.assertNotIn(str(external), dict(picker.worktrees(repo)))

    def test_history_stale_rows_duplicates_and_spaces(self):
        first, second = self.work / "a", self.work / "two words"
        first.mkdir()
        second.mkdir()
        choices = picker.history([f"12.5 {second}\n", f"  9 {first}\n", f"2 {second}\n", "bad diagnostic\n", "/missing\n"])
        self.assertEqual(choices, [(str(second), ""), (str(first), "")])
        for row, (path, _) in zip(picker.rows(choices), choices):
            self.assertEqual(os.fsdecode(base64.urlsafe_b64decode(row.split('\t')[0])), path)

    def test_directory_preview_reads_local_readme_lists_files_and_identifies_empty_dirs(self):
        target = self.work / "ordinary"
        target.mkdir()
        (target / "invoices").mkdir()
        (target / "README.md").write_text("Invoices")
        env = {**os.environ, "FZF_PREVIEW_COLUMNS": "126", "NO_COLOR": "1"}
        def panes(path):
            token = base64.urlsafe_b64encode(os.fsencode(path)).decode()
            result = subprocess.check_output([ROOT / "bin/directory-picker", "--preview-json", token, ""], env=env)
            return json.loads(result)
        first = panes(target)
        self.assertGreater(first['split'], 0)
        self.assertIn("Invoices", "\n".join(first['context']))
        self.assertIn("invoices/", first['details'])
        self.assertIn("1 directory", "\n".join(first['details']))
        self.assertIn("Empty directory", panes(target / "invoices")['details'])
        repo = self.repository("mixed")
        (repo / "README.md").write_text("Root instructions")
        nested = repo / "jobs"
        nested.mkdir()
        (nested / "README.md").write_text("Run the billing worker.")
        (nested / "worker.py").touch()
        selected = panes(nested)
        self.assertIn("Run the billing worker.", "\n".join(selected['context']))
        self.assertNotIn("Root instructions", "\n".join(selected['context']))
        self.assertIn("worker.py", selected['context'])
        self.assertIn("Working tree", "\n".join(selected['details']))

    def test_shell_jump_uses_full_path_and_cancel_stays_put(self):
        target = self.work / "a quote' and spaces"
        target.mkdir()
        tools = self.work / "tools"
        tools.mkdir()
        fzf = tools / "fzf"
        fzf.write_text('''#!/usr/bin/env python3
import os, sys
rows = sys.stdin.buffer.read().rstrip(b'\\0').split(b'\\0')
if os.environ.get('CANCEL'): sys.exit(130)
sys.stdout.buffer.write(b'enter\\0' + rows[0] + b'\\0')
''')
        fzf.chmod(0o755)
        env = {**os.environ, "HOME": str(self.home), "PATH": str(tools) + os.pathsep + os.environ['PATH'], "TARGET": str(target)}
        script = '''source "$1/sh/alias"
_z() { printf '1 %s\\n' "$TARGET"; }
zz
result=$?
printf '%s\\n%s\\n' "$result" "$PWD"
'''
        for shell in ("bash", "zsh"):
            result = subprocess.run([shell, "-c", script, "test", str(ROOT)], env=env, cwd=self.work, text=True, capture_output=True)
            self.assertEqual(result.stdout.splitlines(), ["0", str(target)], result.stderr)
            result = subprocess.run([shell, "-c", script, "test", str(ROOT)], env={**env, "CANCEL": "1"}, cwd=self.work, text=True, capture_output=True)
            self.assertEqual(result.stdout.splitlines(), ["130", str(self.work)], result.stderr)

    def test_repository_changes_keep_committed_and_uncommitted_separate(self):
        repo = self.repository('project')
        (repo / 'main.txt').write_text('first\nsecond\n')
        self.git(repo, 'add', '.')
        self.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'base')
        self.git(repo, 'switch', '-c', 'topic')
        (repo / 'main.txt').write_text('first\nsecond\nthird\n')
        self.git(repo, 'add', '.')
        self.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'one added line')
        (repo / 'main.txt').write_text('changed\nsecond\nthird\n')
        self.git(repo, 'add', '.')
        (repo / 'main.txt').write_text('changed\nsecond\nthird\nfourth\n')
        (repo / 'new file.txt').write_text('untracked\n')
        model = preview.repository(repo)
        self.assertEqual(model['committed'], [(1, 0, 'main.txt')])
        self.assertEqual(model['base'][0], 'main')
        self.assertEqual(dict(model['status']), {'MM': 'main.txt', '??': 'new file.txt'})
        self.assertEqual(model['local'], [(2, 1, 'main.txt')])
        output = io.StringIO()
        with patch.dict(os.environ, {'NO_COLOR': '1'}), redirect_stdout(output):
            self.assertTrue(preview.render(repo, {'agents': [], 'sources': []}))
        self.assertIn('Working tree  2 files', output.getvalue())
        for label in ('[1 staged]', '[1 unstaged]', '[1 untracked]'):
            self.assertIn(label, output.getvalue())
        self.assertIn('Agents  unavailable', output.getvalue())
        self.assertIn('[1 file]', output.getvalue())
        self.assertIn('[+1]', output.getvalue())
        self.assertIn('one added line', output.getvalue())
        self.assertNotIn('1 commit ·', output.getvalue())

    def test_agent_matching_does_not_attribute_nested_worktree_to_parent(self):
        repo = self.repository('agents')
        nested = repo / '.worktrees/topic'
        self.git(repo, 'worktree', 'add', '-b', 'topic', str(nested))
        agents = {'sources': ['tmux'], 'agents': [
            {'cwd': str(nested), 'name': 'Codex', 'state': 'working', 'identity': 'tmux:1'}]}
        self.assertEqual(preview.matching_agents(repo, agents), [])
        self.assertEqual(preview.matching_agents(nested, agents), agents['agents'])

    def test_agent_snapshot_reports_presence_without_guessing_activity(self):
        observation = b'/project\tcodex\t%1\n/project\tclaude\t%2\n'
        with patch.object(preview.shutil, 'which', side_effect=lambda name: name if name == 'tmux' else None), patch.object(preview, 'command', return_value=observation):
            snapshot = preview.agent_snapshot()
        self.assertEqual([agent['state'] for agent in snapshot['agents']], ['attached · activity unknown'] * 2)
        self.assertEqual(snapshot['sources'], ['tmux'])
        for cmd in ('rg codex', 'echo claude', 'git diff -- pi', 'codex app-server'):
            self.assertIsNone(preview.agent_name(cmd))
        self.assertEqual(preview.agent_name('/usr/bin/codex --resume session'), 'Codex')

    def test_unavailable_statistics_are_not_rendered_as_zero(self):
        repo = self.repository('statistics')
        (repo / 'new').write_text('untracked\n')
        original = preview.git
        def incomplete(path, *args):
            if args[0] in ('diff', 'rev-list'):
                return None
            return original(path, *args)
        output = io.StringIO()
        with patch.object(preview, 'git', side_effect=incomplete), patch.dict(os.environ, {'NO_COLOR': '1'}), redirect_stdout(output):
            preview.render(repo, {'agents': [], 'sources': ['tmux']})
        self.assertIn('Tracked diff  unavailable', output.getvalue())
        self.assertIn('Branch changes  unavailable', output.getvalue())

    def test_newline_ending_worktree_path_and_unknown_base(self):
        repo = self.repository('literal\n')
        self.git(repo, 'branch', '-m', 'trunk')
        model = preview.repository(repo)
        self.assertEqual(model['root'], repo)
        self.assertEqual(model['status'], [])
        self.assertIsNone(model['base'])

    def test_recent_commits_exclude_base_and_limit_to_five(self):
        repo = self.repository('history')
        self.git(repo, 'switch', '-c', 'topic')
        for number in range(6):
            self.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid',
                     'commit', '--allow-empty', '-m', f'Change {number}')
        recent = preview.repository(repo)['recent']
        self.assertEqual([commit['subject'] for commit in recent], [f'Change {n}' for n in range(5, 0, -1)])
        self.git(repo, 'switch', 'main')
        self.assertEqual(preview.repository(repo)['recent'], [])

    def test_recent_commit_statistics_are_per_commit_and_first_parent(self):
        repo = self.repository('commit-statistics')
        (repo / 'main.txt').write_text('first\nsecond\n')
        self.git(repo, 'add', '.')
        self.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'base')
        self.git(repo, 'switch', '-c', 'topic')
        (repo / 'main.txt').write_text('first\nsecond\nthird\n')
        self.git(repo, 'add', '.')
        self.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'add line')
        (repo / 'binary.dat').write_bytes(b'\0binary')
        self.git(repo, 'add', '.')
        self.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'add binary')
        recent = preview.repository(repo)['recent']
        self.assertEqual(recent[0]['stats'], [(None, None, 'binary.dat')])
        self.assertEqual(recent[1]['stats'], [(1, 0, 'main.txt')])
        self.git(repo, 'switch', '-c', 'side', 'main')
        (repo / 'side.txt').write_text('side\n')
        self.git(repo, 'add', '.')
        self.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'side change')
        self.git(repo, 'switch', 'topic')
        self.git(repo, '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'merge', '--no-ff', 'side', '-m', 'merge side')
        recent = preview.repository(repo)['recent']
        self.assertEqual(recent[0]['subject'], 'merge side')
        self.assertEqual(recent[0]['stats'], [(1, 0, 'side.txt')])

    def test_readme_uses_remaining_rows_without_pushing_out_git_summary(self):
        readme = self.work / 'README.md'
        readme.write_text('# Heading\n\n' + 'Text ' * 80)
        self.assertIsNone(preview.readme_lines(self.work, 40, 2))
        with patch.object(preview.shutil, 'which', return_value=None):
            name, lines = preview.readme_lines(self.work, 40, 5)
        self.assertEqual(name, 'README.md')
        self.assertEqual(lines[0], '# Heading')
        self.assertEqual(len(lines), 5)
        self.assertTrue(all(len(line) <= 40 for line in lines))

    def test_markdown_renderer_replaces_fences_with_highlighted_python(self):
        if not shutil.which('glow'):
            self.skipTest('Optional glow renderer is not installed')
        (self.work / 'README.md').write_text('# Payments\n\n```python\ndef retry(attempts=5):\n    return attempts\n```\n')
        with patch.dict(os.environ, {'NO_COLOR': ''}):
            _, lines = preview.readme_lines(self.work, 60, 20)
        rendered = '\n'.join(lines)
        self.assertIn('Payments', rendered)
        self.assertNotIn('```', rendered)
        self.assertNotIn('# Payments', rendered)
        self.assertIn('\x1b[', rendered)
        self.assertRegex(rendered, r'\x1b\[[0-9;]*mdef')
        plain = __import__('re').sub(r'\x1b\[[0-9;]*m', '', rendered)
        self.assertIn('def retry(attempts=5):', plain)
        self.assertIn('return attempts', plain)
        with patch.dict(os.environ, {'NO_COLOR': '1'}):
            _, lines = preview.readme_lines(self.work, 60, 20)
        self.assertNotIn('\x1b', '\n'.join(lines))

    def test_ascii_preview_preserves_labels_without_color_or_nerd_glyphs(self):
        repo = self.repository('ascii')
        (repo / 'new').write_text('untracked\n')
        preset = {**preview.theme(), 'symbols': 'ascii'}
        output = io.StringIO()
        with patch.object(preview, 'theme', return_value=preset), patch.dict(os.environ, {'NO_COLOR': '1'}), redirect_stdout(output):
            preview.render(repo, {'agents': [], 'sources': []})
        rendered = output.getvalue()
        self.assertTrue(rendered.isascii(), repr(rendered))
        self.assertIn('[1 untracked]', rendered)
        self.assertIn('[+0]', rendered)
        self.assertIn('[-0]', rendered)

    def test_fallback_keeps_preview_visible(self):
        self.assertTrue(picker.layout(140, 20).startswith("right"))
        self.assertTrue(picker.layout(80, 40).startswith("down"))
        self.assertTrue(picker.layout(80, 20).endswith(",nohidden"))


if __name__ == "__main__":
    unittest.main()
