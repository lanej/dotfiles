import { test } from 'bun:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { spawn, type ChildProcess } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { Coordinator, processAlive } from '../src/coordinator.js';
import { request } from '../src/client.js';
import { Store } from '../src/store.js';
import type { Job } from '../src/domain.js';
const fake = fileURLToPath(new URL('./fake-worker.mjs', import.meta.url));
async function waitFor<T>(read: () => T, predicate: (value: T) => boolean, timeout = 10000): Promise<T> {
  const end = Date.now() + timeout;
  while (true) { const value = read(); if (predicate(value)) return value; if (Date.now() > end) throw new Error(`Timed out: ${JSON.stringify(value)}`); await new Promise(r => setTimeout(r, 20)); }
}
async function withCoordinator(mode: string, run: (c: Coordinator, directory: string) => Promise<void>, clock?: () => number) {
  const directory = await mkdtemp(join(tmpdir(), 'pg-'));
  const c = new Coordinator(directory, { workerPath: fake, workerEnv: { PG_TEST_MODE: mode }, now: clock });
  try { await c.start(); await run(c, directory); } finally { await c.close(); await rm(directory, { recursive: true, force: true }); }
}
function submit(c: Coordinator, requestId: string) { return c.command({ op: 'submit', requestId, task: { kind: 'resolve_conflict' } }) as Job; }
test('real IPC submissions deduplicate, pause, dispatch FIFO and record conflict states', async () => {
  await withCoordinator('resolve', async (c, directory) => {
    c.command({ op: 'pause' });
    const jobs = await Promise.all(Array.from({ length: 5 }, () => request(directory, { op: 'submit', requestId: 'one', task: { kind: 'resolve_conflict' } })));
    assert.equal(new Set(jobs.map(j => j.id)).size, 1);
    const second = submit(c, 'two');
    assert.equal(c.snapshot().jobs[0]?.status, 'queued');
    c.command({ op: 'resume' });
    await waitFor(() => c.store.get(second.id), j => j.status === 'succeeded');
    const all = c.snapshot().jobs;
    assert.equal(all.length, 2); assert.ok(all.every(j => j.attempts.length === 1 && j.status === 'succeeded'));
    assert.ok(all[0]!.attempts[0]!.endedAt! <= all[1]!.attempts[0]!.startedAt);
    for (const j of all) assert.deepEqual(c.store.events(0, j.id).map(e => e.kind).filter(k => ['running', 'conflicted', 'resolving', 'succeeded'].includes(k)), ['running', 'conflicted', 'resolving', 'succeeded']);
  });
});
test('cancellation wins over late success, waits for exit and releases the slot', async () => {
  await withCoordinator('hang', async c => {
    const first = submit(c, 'one'); const second = submit(c, 'two');
    await waitFor(() => c.store.events(0, first.id), e => e.some(x => x.kind === 'progress'));
    c.command({ op: 'cancel', id: first.id });
    assert.equal(c.store.get(first.id).status, 'cancelling'); assert.equal(c.store.get(second.id).status, 'queued');
    await waitFor(() => c.store.get(first.id), j => j.status === 'cancelled');
    assert.equal(c.store.get(first.id).result, undefined);
    await waitFor(() => c.store.get(second.id), j => j.status === 'resolving');
    c.command({ op: 'cancel', id: second.id });
    await waitFor(() => c.store.get(second.id), j => j.status === 'cancelled');
  });
});
test('queued cancellation never dispatches and invalid resolutions fail without retries', async () => {
  await withCoordinator('wrong-side', async c => {
    c.command({ op: 'pause' }); const cancelled = submit(c, 'cancel'); c.command({ op: 'cancel', id: cancelled.id });
    assert.equal(c.store.get(cancelled.id).attempts.length, 0);
    const bad = submit(c, 'bad'); c.command({ op: 'resume' });
    await waitFor(() => c.store.get(bad.id), j => j.status === 'failed');
    assert.equal(c.store.get(bad.id).attempts.length, 1);
    assert.match(c.store.get(bad.id).error!, /maxAttempts/);
  });
});
test('transient retry waits for injected clock; auth failure does not auto-retry', async () => {
  let now = 100;
  await withCoordinator('transient', async c => {
    const job = submit(c, 'retry');
    await waitFor(() => c.store.get(job.id), j => j.status === 'retry_wait');
    assert.equal(c.store.get(job.id).availableAt, 1100); c.tick(); assert.equal(c.store.get(job.id).attempts.length, 1);
    now = 1100; c.tick(); await waitFor(() => c.store.get(job.id), j => j.status === 'succeeded');
    assert.equal(c.store.get(job.id).attempts.length, 2);
  }, () => now);
  await withCoordinator('auth', async c => {
    const job = submit(c, 'auth'); await waitFor(() => c.store.get(job.id), j => j.status === 'failed');
    assert.equal(c.store.get(job.id).attempts.length, 1);
    c.command({ op: 'pause' }); c.command({ op: 'retry', id: job.id }); assert.equal(c.store.get(job.id).status, 'queued');
  });
});
test('shutdown preserves queued jobs and marks active work interrupted', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pg-'));
  const c = new Coordinator(directory, { workerPath: fake, workerEnv: { PG_TEST_MODE: 'hang' } });
  try {
    await c.start(); const active = submit(c, 'active'); const queued = submit(c, 'queued');
    await waitFor(() => c.store.events(0, active.id), e => e.some(x => x.kind === 'progress'));
    await c.close();
    const store = new Store(directory);
    try { assert.equal(store.get(active.id).status, 'interrupted'); assert.equal(store.get(queued.id).status, 'queued'); } finally { store.close(); }
  } finally { await c.close(); await rm(directory, { recursive: true, force: true }); }
});
test('recovery blocks replacement dispatch while the previous PID remains alive', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pg-'));
  const survivor = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], { stdio: 'ignore' });
  let c: Coordinator | undefined;
  try {
    const store = new Store(directory); const job = store.submit({ kind: 'resolve_conflict' }, 'old');
    store.save({ ...job, status: 'resolving', attempts: [{ number: 1, startedAt: Date.now(), pid: survivor.pid }] }, 'resolving'); store.close();
    c = new Coordinator(directory, { workerPath: fake }); await c.start();
    assert.equal(c.store.get(job.id).status, 'interrupted'); assert.equal(c.snapshot().worker, 'recovering');
    await c.close(); c = new Coordinator(directory, { workerPath: fake }); await c.start();
    assert.equal(c.snapshot().worker, 'recovering');
    assert.throws(() => c!.command({ op: 'retry', id: job.id }), /previous worker/);
    const waiting = submit(c, 'waiting'); c.tick(); assert.equal(c.store.get(waiting.id).status, 'queued');
    const exit = once(survivor, 'exit'); survivor.kill('SIGKILL'); await exit;
    c.tick(); await waitFor(() => c!.store.get(waiting.id), j => j.status === 'succeeded');
  } finally { survivor.kill(); await c?.close(); await rm(directory, { recursive: true, force: true }); }
});
test('a killed coordinator releases ownership and its child stops on disconnect', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pg-')); let old: ChildProcess | undefined; let replacement: Coordinator | undefined;
  try {
    old = spawn(process.execPath, [fileURLToPath(new URL('./coordinator-process.mjs', import.meta.url)), directory], { stdio: ['ignore', 'pipe', 'pipe'] });
    await Promise.race([once(old.stdout!, 'data'), once(old, 'exit').then(() => { throw new Error('Test coordinator exited before readiness'); })]);
    const job = await request(directory, { op: 'submit', requestId: 'crash', task: { kind: 'resolve_conflict' } });
    let pid: number | undefined;
    for (let i = 0; i < 200; i++) { const j = await request(directory, { op: 'get', id: job.id }); pid = j.attempts[0]?.pid; if (pid) break; await new Promise(r => setTimeout(r, 20)); }
    assert.ok(pid);
    const exit = once(old, 'exit'); old.kill('SIGKILL'); await exit;
    replacement = new Coordinator(directory, { workerPath: fake }); await replacement.start();
    assert.equal(replacement.store.get(job.id).status, 'interrupted');
    await waitFor(() => processAlive(pid!), alive => !alive);
    replacement.tick(); replacement.command({ op: 'retry', id: job.id }); replacement.tick();
    await waitFor(() => replacement!.store.get(job.id), j => j.status === 'succeeded');
    assert.equal(replacement.store.get(job.id).attempts.length, 2);
  } finally { old?.kill('SIGKILL'); await replacement?.close(); await rm(directory, { recursive: true, force: true }); }
});
test('simultaneous coordinator startup admits exactly one owner', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pg-'));
  const children = Array.from({ length: 2 }, () => spawn(process.execPath, [fileURLToPath(new URL('./coordinator-process.mjs', import.meta.url)), directory], { stdio: ['ignore', 'pipe', 'pipe'] }));
  try {
    const outcomes = await Promise.all(children.map(child => Promise.race([once(child.stdout!, 'data').then(() => 'ready'), once(child, 'exit').then(() => 'exited')])));
    assert.deepEqual(outcomes.sort(), ['exited', 'ready']);
    const snapshot = await request(directory, { op: 'snapshot' });
    assert.equal(snapshot.scheduler, 'running');
  } finally {
    await Promise.all(children.map(async child => { if (child.exitCode === null && child.signalCode === null) { const exit = once(child, 'exit'); child.kill('SIGTERM'); await exit; } }));
    await rm(directory, { recursive: true, force: true });
  }
});
for (const boundary of ['crash-before-pid', 'crash-after-pid']) test(`worker performs no tools when coordinator dies at ${boundary}`, async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pg-'));
  const old = spawn(process.execPath, [fileURLToPath(new URL('./coordinator-process.mjs', import.meta.url)), directory, boundary], { stdio: ['ignore', 'pipe', 'pipe'] });
  let replacement: Coordinator | undefined;
  try {
    await Promise.race([once(old.stdout!, 'data'), once(old, 'exit').then(() => { throw new Error('Coordinator failed before readiness'); })]);
    const exit = once(old, 'exit');
    const job = await request(directory, { op: 'submit', requestId: 'boundary', task: { kind: 'resolve_conflict' } });
    await exit;
    replacement = new Coordinator(directory, { workerPath: fake }); await replacement.start();
    assert.equal(replacement.store.get(job.id).status, 'interrupted');
    assert.equal(replacement.store.events(0, job.id).filter(e => e.kind === 'tool' || e.kind === 'progress').length, 0);
    await waitFor(() => { replacement!.tick(); return replacement!.snapshot().worker; }, worker => worker === 'idle');
    replacement.command({ op: 'retry', id: job.id }); replacement.tick();
    await waitFor(() => replacement!.store.get(job.id), j => j.status === 'succeeded');
  } finally { old.kill('SIGKILL'); await replacement?.close(); await rm(directory, { recursive: true, force: true }); }
});
test('production Pi worker fails cleanly without login and releases its slot', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'pg-'));
  const c = new Coordinator(directory, { workerPath: fileURLToPath(new URL('../dist/worker.js', import.meta.url)), workerEnv: { PI_CODING_AGENT_DIR: join(directory, 'no-auth'), CODEX_HOME: join(directory, 'no-codex-auth') } });
  try {
    await c.start(); const job = submit(c, 'real-worker-no-auth');
    await waitFor(() => c.store.get(job.id), j => j.status === 'failed');
    assert.match(c.store.get(job.id).error!, /Authentication required/);
    assert.equal(c.store.get(job.id).attempts.length, 1);
    assert.ok(c.store.get(job.id).attempts[0]!.exitObservedAt);
    await waitFor(() => c.snapshot().worker, worker => worker === 'idle');
  } finally { await c.close(); await rm(directory, { recursive: true, force: true }); }
});
