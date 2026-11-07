import { pathToFileURL } from 'node:url';
import { nativeCall, taskId } from './github-feedback.mjs';

const sections = [
  ['decisions_open', 'Waiting on you'],
  ['in_flight', 'Active tasks'],
  ['gates', 'Queued / deferred'],
  ['landed', 'Recently completed'],
  ['secondmates', 'Managed secondmate observations'],
];
const clean = value => String(value ?? '').replace(/\s+/g, ' ').trim();
const plain = value => clean(value).replace(/[\\`*_{}[\]<>|]/g, '\\$&');
const label = state => state === 'working' ? 'Running' : clean(state) || 'unknown';
const address = row => row.owner && row.owner !== '(main)' && !row.id.startsWith(`${row.owner}/`)
  ? `${row.owner}/${row.id}` : row.id;

export const localTaskObservations = (snapshot, id) => Object.fromEntries(
  sections.map(([key]) => [key, snapshot[key].filter(row => address(row) === id)]));

export async function board(home, { all = false, signal } = {}) {
  const args = all ? ['--all-in-flight', '--all-queued', '--all-landed', '--all-secondmates'] : [];
  // WHY: --all-decisions promotes deferred holds into Captain's Call; expand its bound while retaining canonical actionability.
  const env = all ? { ...process.env, FM_BEARINGS_DECISIONS: '2147483647' } : process.env;
  const snapshot = JSON.parse(await nativeCall(home, 'task-board', args, { signal, env, timeout: 90000 }));
  if (snapshot.schema !== 'fm-bearings.v1' || sections.some(([key]) => !Array.isArray(snapshot[key])) ||
      !Array.isArray(snapshot.omitted)) throw new Error('Unsupported Firstmate task snapshot; preserve the existing task records and update the adapter');
  return snapshot;
}

export function renderBoard(snapshot) {
  const lines = [`**Tasks** · observed ${plain(snapshot.generated)}`];
  for (const [key, title] of sections) {
    const rows = snapshot[key];
    if (key === 'secondmates' && !rows.length) continue;
    lines.push('', `**${title} (${rows.length} shown)**`);
    if (!rows.length) lines.push('None.');
    for (const row of rows) {
      const id = plain(address(row));
      if (key === 'decisions_open') {
        lines.push(`- **${id}** — ${plain(row.summary)}`);
      } else if (key === 'in_flight') {
        const repo = row.repo ? ` · ${plain(row.repo)}` : '';
        lines.push(`- **${id}** · **${plain(label(row.state))}**${repo} — ${plain(row.name)}`);
        if (row.doing) lines.push(`  ${plain(row.doing)}`);
      } else if (key === 'gates') {
        lines.push(`- **${id}** — ${plain(row.title)}`);
        if (row.reason && row.reason !== '-') lines.push(`  ${plain(row.reason)}`);
        if (row.blocked_by && row.blocked_by !== '-') {
          const scope = row.owner && row.owner !== '(main)' ? ` in ${plain(row.owner)}` : '';
          lines.push(`  Blocked by${scope}: ${plain(row.blocked_by)}`);
        }
      } else if (key === 'landed') {
        lines.push(`- **${id}** — ${plain(row.what)}`);
        if (row.artifact && row.artifact !== '-') lines.push(`  Result: ${plain(row.artifact)}`);
      } else {
        lines.push(`- **${id}** · **${plain(row.state)}** · ${plain(row.freshness)} · ${plain(row.provenance)}`);
        if (row.age_seconds != null) lines.push(`  Observation age: ${plain(row.age_seconds)} seconds.`);
        if (row.doing) lines.push(`  ${plain(row.doing)}`);
        if (row.reason && row.reason !== '-') lines.push(`  ${plain(row.reason)}`);
        if (row.contradiction) lines.push('  Conflicting observations require reconciliation.');
      }
    }
  }
  lines.push('', '**Observation limits**');
  if (snapshot.prs) lines.push(`- PRs/checks: ${plain(snapshot.prs)}`);
  for (const omitted of snapshot.omitted) lines.push(`- ${plain(omitted.surface)}; ${plain(omitted.reveal)}`);
  lines.push('', 'Use `/tasks <id>` or `firstmate tasks show <id>` for the full local task record. Counts above describe displayed rows.');
  return lines.join('\n');
}

export async function show(home, id, { signal } = {}) {
  if (String(id).includes('/')) throw new Error('Qualified secondmate task IDs belong to that operational home; inspect its native task record there');
  taskId(id);
  let record;
  try { record = await nativeCall(home, 'task-show', [id], { signal }); }
  catch (error) {
    throw new Error(`Cannot read local task ${id} from the active backlog or retained Done rows. Archived records require the native archive. ${error.message}`);
  }
  const snapshot = await board(home, { all: true, signal });
  return { id, record, generated: snapshot.generated,
    tracking: localTaskObservations(snapshot, id),
    limits: snapshot.omitted, prs: snapshot.prs };
}

export function renderTask(task) {
  const snapshot = { ...task.tracking, generated: task.generated, omitted: task.limits, prs: task.prs };
  return `${renderBoard(snapshot)}\n\n**Full backlog record for ${plain(task.id)}**\n\n${task.record}`;
}

export async function main(args, home) {
  if (!home) throw new Error('FIRSTMATE_HOME is required');
  if (args[0] === 'show' && args.length === 2) return renderTask(await show(home, args[1]));
  if (args.some(arg => !['--all', '--json'].includes(arg))) throw new Error('Usage: firstmate tasks [--all] [--json] | show <local-task-id>');
  const snapshot = await board(home, { all: args.includes('--all') });
  return args.includes('--json') ? JSON.stringify(snapshot, null, 2) : renderBoard(snapshot);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2), process.env.FIRSTMATE_HOME).then(value => console.log(value)).catch(error => {
    console.error(error.message); process.exitCode = 1;
  });
}
