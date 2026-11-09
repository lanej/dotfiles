import { test } from 'bun:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { visibleWidth, type Terminal } from '@earendil-works/pi-tui';
import { renderDashboard, Dashboard, dashboard } from '../src/dashboard.js';
import { Coordinator } from '../src/coordinator.js';
import type { Snapshot } from '../src/domain.js';
const sample: Snapshot = { scheduler: 'running', worker: 'busy', jobs: [{ id: 'example', requestId: 'r', digest: 'd', task: { kind: 'resolve_conflict' }, status: 'resolving', createdAt: 1, updatedAt: 2, availableAt: 1, retryCount: 0, attempts: [{ number: 1, startedAt: 1 }], result: '**Reconciling branches**\n\nKeep the policy conflict visible.\n\n```json\n{"maxAttempts":3,"timeoutSeconds":60,"retryDelaySeconds":1}\n```' }], events: [{ seq: 1, jobId: 'example', at: 1, kind: 'conflicted', detail: '<<<<<<< HEAD\npolicy conflict\n=======\nsource\n>>>>>>> source' }] };
test('dashboard fits wide, narrow and very small terminal sizes', () => {
  for (const [width, height] of [[160, 50], [120, 36], [96, 24], [95, 24], [80, 24], [40, 12], [32, 12], [12, 5], [1, 1]]) {
    const lines = renderDashboard(sample, { selected: 0, expanded: false, scroll: 0, message: '' }, width!, height!);
    assert.equal(lines.length, height);
    assert.ok(lines.every(line => visibleWidth(line) <= width!));
  }
  const wide = renderDashboard(sample, { selected: 0, expanded: false, scroll: 0, message: '' }, 120, 36).join('\n');
  assert.match(wide, /QUEUE/); assert.match(wide, /resolving/); assert.match(wide, /policy conflict/);
});
test('keyboard actions use the same coordinator API and terminal cleanup runs on quit', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pg-'));
  const c = new Coordinator(directory);
  let input: ((data: string) => void) | undefined;
  let stopped = false;
  let output = '';
  const terminal: Terminal = {
    columns: 100, rows: 25, start(onInput) { input = onInput; }, stop() { stopped = true; },
    write(text) { output += text; }, moveBy() {}, hideCursor() {}, showCursor() {}, clearLine() {}, clearFromCursor() {}, clearScreen() {},
  };
  try {
    await c.start(); c.command({ op: 'pause' });
    const job = c.command({ op: 'submit', requestId: 'ui', task: { kind: 'resolve_conflict' } }) as { id: string };
    let height = 25;
    const component = new Dashboard(c, () => height, () => {}, () => {});
    component.handleInput('c'); assert.equal(c.store.get(job.id).status, 'cancelled');
    component.handleInput('\r'); assert.equal(component.view.expanded, true);
    component.render(100);
    component.handleInput('['); assert.equal(component.view.scroll, 0);
    component.handleInput(']'); assert.equal(component.view.scroll, 0);
    c.store.save({ ...c.store.get(job.id), result: Array.from({ length: 60 }, (_, i) => `Paragraph ${i}.\n\n`).join('') }, 'progress');
    for (let i = 0; i < 15; i++) c.store.event(job.id, 'tool', 'read_conflict');
    component.render(100);
    component.handleInput(']'); assert.equal(component.view.scroll, 3);
    component.handleInput('\t'); assert.equal(component.view.focus, 'activity');
    component.handleInput('['); assert.equal(component.view.activityScroll, 3); assert.equal(component.view.scroll, 3);
    for (let i = 0; i < 50; i++) component.handleInput('[');
    const end = component.view.activityScroll;
    component.handleInput('['); assert.equal(component.view.activityScroll, end);
    component.handleInput(']'); assert.equal(component.view.activityScroll, end! - 3);
    height = 16; component.render(100);
    assert.equal(component.view.focus, 'result');
    component.handleInput(']'); assert.equal(component.view.scroll, 6);


    const done = dashboard(c, terminal);
    await new Promise(r => setTimeout(r, 40));
    assert.match(output, /QUEUE/);
    input!('q'); await done;
    assert.equal(stopped, true);
  } finally { await c.close(); await rm(directory, { recursive: true, force: true }); }
});

test('worker Markdown renders with formatting and JSON blocks, without raw fences or control injection', () => {
  const snapshot = structuredClone(sample);
  snapshot.jobs[0]!.result = '# Result\n\n**Combined policy** in `retry-policy.json`.\n\n- Keep three attempts.\n- Use the longer timeout.\n\n```json\n{"maxAttempts":3,"timeoutSeconds":60}\n```\n\n\x1b[2JVisible text';
  const output = renderDashboard(snapshot, { selected: 0, expanded: true, scroll: 0, message: '' }, 100, 40).join('\n');
  assert.match(output, /Combined policy/);
  assert.match(output, /Keep three attempts/);
  assert.match(output, /"maxAttempts": 3/);
  assert.match(output, /\x1b\[1m/);
  assert.doesNotMatch(output, /```|\*\*Combined policy\*\*|`retry-policy.json`|\x1b\[2J/);
});
test('verified merge metadata is readable and independent scrolling keeps the other pane stationary', () => {
  const snapshot = structuredClone(sample);
  snapshot.jobs[0]!.status = 'succeeded';
  snapshot.jobs[0]!.result = '**Resolved**\n\n' + Array.from({ length: 45 }, (_, i) => `Result paragraph ${i}.\n\n`).join('') + 'BOTTOM RESULT\n\n' + JSON.stringify({ policy: { maxAttempts: 3, timeoutSeconds: 60, retryDelaySeconds: 1 }, clean: true, mergeCommit: 'a'.repeat(40) });
  snapshot.events = Array.from({ length: 20 }, (_, i) => ({ seq: i + 1, jobId: 'example', at: i + 1, kind: 'tool', detail: `activity_${i}` }));
  const view = { selected: 0, expanded: false, scroll: 0, message: '' };
  const beginning = renderDashboard(snapshot, view, 120, 36).join('\n');
  const ending = renderDashboard(snapshot, { ...view, scroll: 9999 }, 120, 36).join('\n');
  const older = renderDashboard(snapshot, { ...view, focus: 'activity', activityScroll: 9999 }, 120, 36).join('\n');
  assert.match(beginning, /Result paragraph 0/);
  assert.match(ending, /BOTTOM RESULT/); assert.match(ending, /Independently verified/);
  assert.doesNotMatch(ending, /"mergeCommit"|"clean"/);
  assert.match(beginning, /activity 19/); assert.match(ending, /activity 19/);
  assert.match(older, /activity 0/); assert.match(older, /Result paragraph 0/);
});

test('tiny terminals retain quit help even when the selected result is long', () => {
  const snapshot = structuredClone(sample);
  snapshot.jobs[0]!.result = 'A long result. '.repeat(500);
  for (const [width, height] of [[12, 5], [1, 1]]) {
    const lines = renderDashboard(snapshot, { selected: 0, expanded: false, scroll: 0, message: '' }, width!, height!);
    assert.match(lines.at(-1)!, /q/);
  }
});
