"""Read-only repository and agent observations for directory-picker previews."""

from concurrent.futures import ThreadPoolExecutor
import json
from itertools import zip_longest
import os
from pathlib import Path
import shlex
import re
import shutil
import subprocess
import textwrap
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def command(args, cwd=None, timeout=1, data=None, env=None):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, input=data,
                                env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0', **(env or {})})
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def git(path, *args):
    return command(['git', '-C', str(path), *args])


def text(value):
    return os.fsdecode(value or b'').removesuffix('\n')


def safe(value):
    return ''.join(c if c.isprintable() or unicodedata.category(c) == 'Co' else repr(c)[1:-1] for c in value)


def agent_name(value):
    try:
        argv = shlex.split(value)
    except ValueError:
        return None
    if not argv:
        return None
    executable = Path(argv[0]).name
    if executable == 'codex' and len(argv) > 1 and argv[1] == 'app-server':
        return None
    return {'codex': 'Codex', 'claude': 'Claude', 'pi': 'Pi'}.get(executable)


def zellij_agents(session):
    raw = command(['zellij', '--session', session, 'action', 'list-panes', '--all', '--json'], timeout=.6)
    if raw is None:
        return None
    try:
        panes = json.loads(raw)
        result = []
        for pane in panes:
            if pane.get('is_plugin') or pane.get('exited'):
                continue
            state = pane.get('command_state') or {}
            running = state.get('running') or {}
            name = agent_name((running.get('command') or {}).get('text', ''))
            cwd = pane.get('pane_cwd') or state.get('cwd')
            if name and cwd and state.get('phase') == 'Running':
                result.append({'cwd': cwd, 'name': name, 'state': 'attached · activity unknown',
                               'identity': f'zellij:{session}:{pane["id"]}'})
        return result
    except (ValueError, TypeError, KeyError):
        return None


def agent_snapshot():
    """Observe live terminal agents; a running client alone does not prove an active turn."""
    agents, sources = [], []
    if shutil.which('tmux'):
        raw = command(['tmux', 'list-panes', '-a', '-F',
                       '#{pane_current_path}\t#{pane_current_command}\t#{pane_id}'], timeout=.6)
        if raw is not None:
            sources.append('tmux')
            for line in text(raw).splitlines():
                fields = line.split('\t')
                if len(fields) != 3:
                    continue
                cwd, process, pane = fields
                name = agent_name(process)
                if name and cwd:
                    agents.append({'cwd': cwd, 'name': name, 'state': 'attached · activity unknown',
                                   'identity': f'tmux:{pane}'})
    if shutil.which('zellij'):
        raw = command(['zellij', 'list-sessions', '--short'], timeout=.6)
        if raw is not None:
            sessions = text(raw).splitlines()
            if not sessions:
                sources.append('Zellij')
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(zellij_agents, sessions[:16]))
            if len(sessions) <= 16 and all(result is not None for result in results):
                sources.append('Zellij')
            agents.extend(agent for result in results if result for agent in result)
    return {'agents': agents, 'sources': sources}


def matching_agents(path, snapshot):
    root = Path(path).resolve()
    matched = []
    for agent in snapshot['agents']:
        directory = Path(agent['cwd']).resolve()
        if directory.is_relative_to(root):
            actual = git(directory, 'rev-parse', '--show-toplevel')
            if actual is not None and Path(text(actual)).resolve() == root:
                matched.append(agent)
    return matched


def status_rows(raw):
    rows = []
    fields = (raw or b'').split(b'\0')
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        code, path = os.fsdecode(field[:2]), os.fsdecode(field[3:])
        if 'R' in code or 'C' in code:
            old = os.fsdecode(fields[index])
            index += 1
            path = f'{old} → {path}'
        rows.append((code, path))
    return rows


def diff_rows(raw):
    result = []
    for record in (raw or b'').split(b'\0'):
        if not record:
            continue
        added, removed, name = record.split(b'\t', 2)
        result.append((None if added == b'-' else int(added),
                       None if removed == b'-' else int(removed), os.fsdecode(name)))
    return result


def repository(path):
    root = git(path, 'rev-parse', '--show-toplevel')
    if root is None:
        return None
    root = Path(text(root))
    branch = text(git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')) or text(git(root, 'rev-parse', '--short', 'HEAD'))
    status = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=normal')
    local = git(root, 'diff', '--no-ext-diff', '--numstat', '-z', '--no-renames', 'HEAD', '--')
    result = {'root': root, 'branch': branch, 'status': None if status is None else status_rows(status),
              'local': None if local is None else diff_rows(local),
              'base': None, 'committed': None, 'recent': None}
    default = text(git(root, 'symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD'))
    for ref in dict.fromkeys([default, 'refs/heads/main', 'refs/heads/master']):
        if not ref:
            continue
        base = git(root, 'merge-base', ref, 'HEAD')
        if base is None:
            continue
        base = text(base)
        committed = git(root, 'diff', '--no-ext-diff', '--numstat', '-z', '--no-renames', base, 'HEAD', '--')
        log = git(root, 'log', '--max-count=5', '--format=%h%x00%s', '-z', base + '..HEAD', '--')
        recent = None
        if log is not None:
            fields = log.split(b'\0')
            recent = []
            for i in range(0, len(fields)-1, 2):
                commit, subject = text(fields[i]), text(fields[i+1])
                stats = git(root, 'show', '--format=', '--no-ext-diff', '--numstat', '-z',
                            '--no-renames', '--diff-merges=first-parent', commit, '--')
                recent.append({'hash': commit, 'subject': subject,
                               'stats': None if stats is None else diff_rows(stats)})
        result.update(recent=recent, base=(ref.removeprefix('refs/heads/').removeprefix('refs/remotes/'), base[:8]),
                      committed=None if committed is None else diff_rows(committed))
        break
    return result


def theme_directory():
    return Path(os.environ.get('DOTFILES_THEME_DIR', str(Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'dotfiles/theme')))


def theme():
    try:
        return json.loads((theme_directory() / 'colors.json').read_text())
    except (OSError, ValueError, KeyError):
        return json.loads((ROOT / 'design-system/generated/colors.json').read_text())


def readme_lines(root, width, available=None):
    if available is not None and available < 3:
        return None
    names = ('README.md', 'README.markdown', 'README.rst', 'README.txt', 'README', 'readme.md', 'Readme.md')
    readme = next((root / name for name in names if (root / name).is_file()), None)
    if readme is None:
        return None
    try:
        with readme.open('rb') as source:
            data = source.read(65536)
    except OSError:
        return None
    if not data.strip():
        return None
    highlighted = None
    markdown = readme.suffix.lower() in ('.md', '.markdown', '')
    if markdown and shutil.which('glow'):
        style = theme_directory() / 'glow.json'
        if not style.is_file():
            style = ROOT / 'design-system/generated/glow.json'
        color = not os.environ.get('NO_COLOR')
        # Glow writes into a pipe even when the picker is displaying a true-color terminal.
        highlighted = command(['glow', '--style', str(style) if color else 'notty',
                               '--width', str(width), '-'], data=data, env={'CLICOLOR_FORCE': '1' if color else '0'})
    if highlighted is None and shutil.which('bat'):
        args = ['bat', '--color=' + ('never' if os.environ.get('NO_COLOR') else 'always'),
                '--paging=never', '--style=plain', '--wrap=character', '--terminal-width=' + str(width),
                '--theme=' + os.environ.get('BAT_THEME', 'Dotfiles'),
                '--file-name=' + readme.name]
        if available is not None:
            args.append('--line-range=:' + str(available))
        if markdown:
            args.append('--language=Markdown')
        highlighted = command(args, data=data)
    if highlighted is not None:
        lines = highlighted.decode(errors='replace').splitlines()
        def blank(value):
            return not re.sub(r'\x1b\[[0-9;]*m', '', value).strip()
        while lines and blank(lines[0]):
            lines.pop(0)
        while lines and blank(lines[-1]):
            lines.pop()
    else:
        lines = [part for line in data.decode(errors='replace').splitlines()
                 for part in textwrap.wrap(safe(line), width=width, replace_whitespace=False) or ['']]
    return readme.name, lines[:available]


def render(path, snapshot, structured=False):
    path = Path(path)
    repo = repository(path)
    preset = theme()
    colors = preset['roles']
    ascii_mode = preset.get('symbols') == 'ascii'
    available_width = max(1, int(os.environ.get('FZF_PREVIEW_COLUMNS', '80')))
    is_root = repo is not None and path.resolve() == repo['root'].resolve()
    # A worktree without a README can show its files alongside its Git activity.
    gap = 3
    paired = available_width >= 2 * 42 + gap
    width = (available_width - gap) // 2 if paired else available_width
    context_width = available_width - gap - width if paired else width
    readme = readme_lines(path, context_width)
    if readme is None and repo is None:
        width, paired = available_width, False
    blocks = [[]]

    def glyph(unicode, fallback):
        return fallback if ascii_mode else unicode

    minus = glyph('−', '-')
    separator = glyph('·', '|')

    def span(value, role='text', bold=False, background=None):
        return safe(str(value)), role, bold, background

    def styled(value, role, bold, background):
        if os.environ.get('NO_COLOR'):
            return value
        rgb = tuple(bytes.fromhex(colors.get(role, colors['text']).removeprefix('#')))
        style = f'{"1;" if bold else ""}38;2;{rgb[0]};{rgb[1]};{rgb[2]}'
        if background:
            rgb = tuple(bytes.fromhex(colors[background].removeprefix('#')))
            style += f';48;2;{rgb[0]};{rgb[1]};{rgb[2]}'
        return f'\033[{style}m{value}\033[0m'

    def cell_width(value):
        return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in value)

    def row(*parts):
        chunks, occupied = [], 0
        for value, role, bold, background in parts:
            if chunks and occupied + cell_width(value) > width and cell_width(value) <= width:
                blocks[-1].append(''.join(chunks))
                chunks, occupied = [], 0
            fragment = ''
            for char in value:
                size = cell_width(char)
                if occupied + size > width:
                    chunks.append(styled(fragment, role, bold, background))
                    blocks[-1].append(''.join(chunks))
                    chunks, occupied, fragment = [], 0, ''
                fragment += char
                occupied += size
            chunks.append(styled(fragment, role, bold, background))
        blocks[-1].append(''.join(chunks))

    def line(value='', role='text', bold=False):
        row(span(value, role, bold))

    def pill(value, role='text.muted', background='surface.raised'):
        if ascii_mode or os.environ.get('NO_COLOR'):
            return span(f'[{value}]', role, True)
        return span(f' {value} ', role, True, background)

    def section(value, icon):
        label = f'{icon} {value}  '
        rule = glyph('─', '-') * max(0, width - cell_width(label))
        row(span(label, 'heading', True), span(rule, 'border'))

    def count(number, noun):
        return f'{number} {noun}' + ('' if number == 1 else 's')

    def totals(rows):
        added, removed = sum(a or 0 for a, _, _ in rows), sum(d or 0 for _, d, _ in rows)
        row(pill(count(len(rows), 'file')), span('  '), pill(f'+{added}', 'diff.add', 'diff.add.bg'),
            span('  '), pill(f'{minus}{removed}', 'diff.delete', 'diff.delete.bg'))
        if any(a is None for a, _, _ in rows):
            line('binary changes', 'text.muted')

    def directory_contents():
        try:
            with os.scandir(path) as children:
                entries = sorted(((item.is_dir(follow_symlinks=False), item.is_symlink(), item.name)
                                  for item in children if item.name != '.git'),
                                 key=lambda item: (item[2].startswith('.'), not item[0], item[2].casefold(), item[2]))
        except OSError as error:
            line(f'Cannot list directory: {error.strerror}', 'status.warning')
            return
        if not entries:
            line('No entries besides .git' if (path / '.git').exists() else 'Empty directory', 'text.muted')
            return
        directories = sum(is_dir for is_dir, _, _ in entries)
        links = sum(is_link for _, is_link, _ in entries)
        files = len(entries) - directories - links
        summary = [f'{directories} ' + ('directory' if directories == 1 else 'directories')] if directories else []
        if files:
            summary.append(count(files, 'file'))
        if links:
            summary.append(count(links, 'link'))
        line(f'Contents  {f" {separator} ".join(summary)}', 'heading', True)
        for is_dir, is_link, name in entries:
            label = safe(name) + ('/' if is_dir else '@' if is_link else '')
            line(label, 'accent' if is_dir else 'text')

    try:
        relative = path.relative_to(Path.home())
        label = '~' if not relative.parts else '~/' + str(relative)
    except ValueError:
        label = str(path)

    def folder_header():
        row(span(f'{glyph("", "dir")} {label}', 'text.strong', True))

    def git_details():
        branch = glyph(preset.get('components', {}).get('git.file.branch', {}).get('symbol', ''), '@')
        row(span(f'{glyph("", "dir")} {repo["root"].name}', 'text.strong', True), span('  '),
            pill(f'{branch} {repo["branch"]}', 'accent'))
        agents = matching_agents(repo['root'], snapshot)
        if agents:
            for agent in agents:
                row(pill(f'{glyph("󰚩", "agent")} {agent["name"]}', 'accent'), span('  '), span(agent['state'].replace('·', separator), 'text.muted'))
        elif snapshot.get('pending'):
            line('Agents  checking', 'text.muted')
        else:
            line('Agents  none observed' if snapshot['sources'] else 'Agents  unavailable', 'text.muted')
        line()
        status = repo['status']
        if status is None:
            line('Working tree  unavailable', 'status.warning')
        elif status:
            staged = sum(code[0] not in (' ', '?') for code, _ in status)
            unstaged = sum(code[1] not in (' ', '?') for code, _ in status)
            untracked = sum(code == '??' for code, _ in status)
            section(f'Working tree  {len(status)} files', glyph('', '~'))
            row(pill(f'{staged} staged', 'text.inverse', 'git.file.staged'), span('  '),
                pill(f'{unstaged} unstaged', 'diff.change', 'diff.change.bg'), span('  '),
                pill(f'{untracked} untracked', 'git.file.untracked'))
            if repo['local'] is None:
                line('Tracked diff  unavailable', 'text.muted')
            elif repo['local']:
                added = sum(a or 0 for a, _, _ in repo['local'])
                removed = sum(d or 0 for _, d, _ in repo['local'])
                row(span(f'{len(repo["local"])} tracked files  ', 'text.muted'), span(f'+{added}', 'diff.add'),
                    span('  '), span(f'{minus}{removed}', 'diff.delete'))
            for code, name in status:
                role = 'git.file.untracked' if code == '??' else ('git.file.staged' if code[0] != ' ' else 'git.file.modified')
                row(span(code, role, True), span('  '), span(name))
        else:
            row(span('Working tree  ', 'heading', True), pill(f'{glyph("", "ok")} clean', 'status.success'))
        blocks.append([])
        if repo['base'] is None:
            line('Branch changes  base unavailable', 'text.muted')
        elif repo['committed'] is None:
            line('Branch changes  unavailable', 'status.warning')
        else:
            ref, commit = repo['base']
            section(f'Since {ref} {separator} {commit}', branch)
            totals(repo['committed'])
            for added, removed, name in repo['committed']:
                if added is None:
                    row(span('binary  ', 'text.muted'), span(name))
                else:
                    row(span(f'+{added:>3}', 'diff.add'), span('  '), span(f'{minus}{removed:<3}', 'diff.delete'), span('  '), span(name))
            if repo['recent']:
                blocks.append([])
                section('Recent commits', glyph('', 'o'))
                subject_width = max(cell_width(safe(commit['subject'])) for commit in repo['recent'])
                for recent in repo['recent']:
                    stats = recent['stats']
                    if stats is None:
                        summary = [span('stats unavailable', 'text.muted')]
                    else:
                        added = sum(a or 0 for a, _, _ in stats)
                        removed = sum(d or 0 for _, d, _ in stats)
                        files = count(len(stats), 'file') if width >= 45 else f'{len(stats)}f'
                        summary = [span(files, 'text.muted'), span(' '), span(f'+{added}', 'diff.add'),
                                   span(' '), span(f'{minus}{removed}', 'diff.delete')]
                        binary = sum(a is None for a, _, _ in stats)
                        if binary:
                            summary.append(span(f' {binary}bin', 'text.muted'))
                    stats_width = sum(cell_width(part[0]) for part in summary)
                    room = max(0, width - cell_width(recent['hash']) - stats_width - 4)
                    subject = safe(recent['subject'])
                    if cell_width(subject) > room:
                        ending = glyph('…', '.') if room else ''
                        clipped = ''
                        for char in subject:
                            if cell_width(clipped + char + ending) > room:
                                break
                            clipped += char
                        subject = clipped + ending
                    padding = max(2, min(room, subject_width) - cell_width(subject) + 2)
                    row(span(recent['hash'], 'accent.secondary'), span('  '), span(subject),
                        span(' ' * padding), *summary)
            elif repo['recent'] is None:
                line('Recent commits  unavailable', 'text.muted')
    if repo is not None:
        git_details()
    else:
        folder_header()
        directory_contents()
    details = '\n\n'.join('\n'.join(block) for block in blocks).splitlines()
    blocks = [[]]
    width = context_width
    if readme is not None:
        name, content = readme
        section(name, glyph('', 'file'))
        blocks[-1].extend(content)
    if repo is not None and (readme is None or not is_root):
        if readme is not None:
            blocks.append([])
        folder_header()
        directory_contents()
    context = '\n\n'.join('\n'.join(block) for block in blocks).splitlines()
    split = context_width if context and paired else 0
    if structured:
        print(json.dumps({'context': context, 'details': details, 'split': split}, ensure_ascii=True))
    elif split:
        for left, right in zip_longest(context, details, fillvalue=''):
            visible = re.sub(r'\x1b\[[0-9;:]*m', '', left)
            print(left + ' ' * max(gap, split - cell_width(visible) + gap) + right if right else left)
    else:
        print('\n\n'.join('\n'.join(pane) for pane in (details, context) if pane))
    return True
