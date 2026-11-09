import { test } from 'bun:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { transition, nextReady, retryDelay, parseTask, cleanText, type Job } from '../src/domain.js';
import { Store } from '../src/store.js';
import { publicPullRequest } from '../src/github.js';
import { createFixture, writeResolution, validateResolution, finishFixture, removeFixture } from '../src/fixture.js';
const temp = () => mkdtemp(join(tmpdir(), 'pg-'));
test('jobs follow explicit conflict, completion and cancellation contracts', () => {
  const job = { status: 'queued', updatedAt: 0 } as Job;
  const running = transition(job, 'running', 10);
  const conflict = transition(running, 'conflicted', 11);
  assert.equal(transition(transition(conflict, 'resolving', 12), 'succeeded', 13).status, 'succeeded');
  const cancelled = transition(transition(running, 'cancelling', 12), 'cancelled', 13);
  assert.throws(() => transition(cancelled, 'succeeded', 14));
  assert.throws(() => transition(job, 'succeeded', 14));
  assert.equal(job.updatedAt, 0);
});
test('FIFO selects due queued work and retry budget is bounded', () => {
  const jobs = [{ id: 'first', status: 'queued', createdAt: 1, availableAt: 5 }, { id: 'later', status: 'queued', createdAt: 2, availableAt: 0 }, { id: 'running', status: 'running', createdAt: 0, availableAt: 0 }] as Job[];
  assert.equal(nextReady(jobs, 4)?.id, 'later'); assert.equal(nextReady(jobs, 5)?.id, 'first');
  assert.deepEqual([retryDelay(0), retryDelay(1), retryDelay(2)], [1000, 5000, undefined]);
  const tied = [{ id: 'z', status: 'queued', createdAt: 1, availableAt: 0 }, { id: 'a', status: 'queued', createdAt: 1, availableAt: 0 }] as Job[];
  assert.equal(nextReady(tied, 1)?.id, 'z');
  assert.equal(nextReady([{ ...tied[0]!, createdAt: 20 }, { ...tied[1]!, createdAt: 10 }], 25)?.id, 'z');
});
test('private or indeterminate repository data is withheld from model tools', () => {
  for (const repo of [{ private: true }, {}, undefined]) assert.throws(() => publicPullRequest({ base: { repo }, body: 'private secret' }), /confirmed public/);
  const result = publicPullRequest({ base: { repo: { private: false }, ref: 'main' }, title: 'public', body: 'safe', head: { sha: 'abc' } }) as { body: string };
  assert.equal(result.body, 'safe');
});
test('task input rejects alternate hosts, arbitrary fields and shell fragments', () => {
  for (const url of ['https://evil.test/a/b/pull/1', 'https://github.com/a/b/pull/1;whoami', 'https://github.com/a/../pull/1', 'https://github.com/a/b/issues/1']) assert.throws(() => parseTask({ kind: 'summarize_pr', url }));
  assert.throws(() => parseTask({ kind: 'resolve_conflict', path: '/tmp' }));
  assert.equal(parseTask({ kind: 'summarize_pr', url: 'https://github.com/a/b/pull/1/' }).kind, 'summarize_pr');
  assert.equal(cleanText('\x1b[31mhello\x1b[0m\x00'), 'hello');
});
test('store deduplicates requests, rejects changed payload and excludes another owner', async () => {
  const path = await temp(); let store: Store | undefined;
  try {
    store = new Store(path, () => 123);
    const first = store.submit({ kind: 'resolve_conflict' }, 'same');
    assert.equal(store.submit({ kind: 'resolve_conflict' }, 'same').id, first.id);
    assert.throws(() => store!.submit({ kind: 'summarize_pr', url: 'https://github.com/a/b/pull/1' }, 'same'));
    assert.throws(() => new Store(path), /Another coordinator/);
    assert.equal(store.events(0, first.id).length, 1);
    store.setPaused(true); store.close(); store = new Store(path);
    assert.equal(store.paused(), true); assert.equal(store.get(first.id).status, 'queued');
  } finally { store?.close(); await rm(path, { recursive: true, force: true }); }
});
test('real merge conflict rejects either side and completes a verified combined merge', async () => {
  const directory = await temp();
  try {
    const fixture = await createFixture(directory);
    assert.match(fixture.conflict, /<<<<<<< HEAD/);
    assert.equal((await validateResolution(fixture.path)).valid, false);
    await writeResolution(fixture.path, { maxAttempts: 3, timeoutSeconds: 30, retryDelaySeconds: 1 });
    assert.equal((await validateResolution(fixture.path)).valid, false);
    await writeResolution(fixture.path, { maxAttempts: 5, timeoutSeconds: 60, retryDelaySeconds: 1 });
    await assert.rejects(finishFixture(fixture.path));
    await writeResolution(fixture.path, { maxAttempts: 3, timeoutSeconds: 60, retryDelaySeconds: 1 });
    assert.equal((await validateResolution(fixture.path)).valid, true);
    await writeFile(join(fixture.path, 'unexpected.txt'), 'unexpected');
    assert.equal((await validateResolution(fixture.path)).valid, false);
    await rm(join(fixture.path, 'unexpected.txt'));
    assert.equal(JSON.parse(await finishFixture(fixture.path)).clean, true);
    await removeFixture(directory, fixture.path);
    await assert.rejects(removeFixture(directory, directory), /outside owned fixtures/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
