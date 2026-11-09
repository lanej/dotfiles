import { test } from 'bun:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { visibleWidth, type Terminal } from '@earendil-works/pi-tui';
import { renderDashboard, Dashboard, dashboard } from '../src/dashboard.js';
import { Coordinator } from '../src/coordinator.js';
import type { Snapshot } from '../src/domain.js';
const sample: Snapshot = { scheduler: 'running', worker: 'busy', jobs: [{ id: 'example', requestId: 'r', digest: 'd', task: { kind: 'resolve_conflict' }, status: 'resolving', createdAt: 1, updatedAt: 2, availableAt: 1, retryCount: 0, attempts: [{ number: 1, startedAt: 1 }], result: 'A long result '.repeat(30) }], events: [{ seq: 1, jobId: 'example', at: 1, kind: 'conflicted', detail: '<<<<<<< HEAD\npolicy conflict\n=======\nsource\n>>>>>>> source' }] };
test('dashboard fits wide, narrow and very small terminal sizes', () => {
  for (const [width, height] of [[120, 36], [80, 24], [40, 12], [12, 5], [1, 1]]) {
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
    const component = new Dashboard(c, () => 25, () => {}, () => {});
    component.handleInput('c'); assert.equal(c.store.get(job.id).status, 'cancelled');
    component.handleInput('\r'); assert.equal(component.view.expanded, true);
    component.handleInput('['); assert.equal(component.view.scroll, 3);
    component.handleInput(']'); assert.equal(component.view.scroll, 0);
    const done = dashboard(c, terminal);
    await new Promise(r => setTimeout(r, 40));
    assert.match(output, /QUEUE/);
    input!('q'); await done;
    assert.equal(stopped, true);
  } finally { await c.close(); await rm(directory, { recursive: true, force: true }); }
});
