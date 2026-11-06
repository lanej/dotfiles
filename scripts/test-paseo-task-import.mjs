import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, mkdir, rm, writeFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';

const runtime = process.env.PASEO_TASKS_RUNTIME;
const piRoot = process.env.PASEO_TASKS_PI_ROOT;
if (!runtime || !piRoot) throw new Error('Set PASEO_TASKS_RUNTIME to official Paseo 0.15.1 and PASEO_TASKS_PI_ROOT to Pi 1.4.0');
const modules = join(resolve(runtime), 'node_modules');
const load = path => import(pathToFileURL(path));
const { createTestPaseoDaemon } = await load(join(modules, '@getpaseo/server/dist/server/server/test-utils/paseo-daemon.js'));
const { PiRpcAgentClient } = await load(join(modules, '@getpaseo/server/dist/server/server/agent/providers/pi/agent.js'));
const { DaemonClient } = await load(join(modules, '@getpaseo/client/dist/daemon-client.js'));
const { createPaseoApi } = await load(join(modules, '@getpaseo/client/dist/index.js'));
const { SessionManager } = await load(join(resolve(piRoot), 'dist/index.js'));
const source = dirname(dirname(fileURLToPath(import.meta.url)));
const { tsImport } = await load(join(source, 'paseo-tasks/node_modules/tsx/dist/esm/api/index.mjs'));
const { TaskService } = await tsImport(join(source, 'paseo-tasks/server/service.ts'), import.meta.url);
const { Store } = await tsImport(join(source, 'paseo-tasks/server/store.ts'), import.meta.url);
const { Feedback } = await tsImport(join(source, 'paseo-tasks/server/github.ts'), import.meta.url);
const { Treehouse } = await tsImport(join(source, 'paseo-tasks/server/treehouse.ts'), import.meta.url);
const directory = await mkdtemp(join(tmpdir(), 'paseo-task-import-'));
const cwd = join(directory, 'checkout');
const agentDir = join(directory, 'pi');
const logger = { child() { return this; }, debug() {}, info() {}, warn() {}, error() {}, trace() {} };
let daemon, raw, api, store, codingLease, result;
try {
  await mkdir(cwd); await mkdir(agentDir);
  await writeFile(join(agentDir, 'settings.json'), JSON.stringify({
    defaultProvider: 'amazon-bedrock', defaultModel: 'us.anthropic.claude-sonnet-5-5', defaultThinkingLevel: 'medium',
  }));
  const saved = SessionManager.create(cwd, join(agentDir, 'sessions'));
  saved.appendModelChange('amazon-bedrock', 'us.anthropic.claude-sonnet-5-5');
  saved.appendThinkingLevelChange('medium');
  saved.appendMessage({ role: 'user', content: 'PASEO_TASK_IMPORT_HISTORY: retain my original task conversation', timestamp: Date.now() });
  const originalId = saved.getSessionId();
  const sessionFile = saved.getSessionFile();
  assert.ok(sessionFile);
  const pi = new PiRpcAgentClient({ logger, runtimeSettings: {
    command: [process.execPath, join(resolve(piRoot), 'dist/bundle/cli.js')],
    env: { PI_CODING_AGENT_DIR: agentDir, PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0' },
  } });
  daemon = await createTestPaseoDaemon({
    paseoHomeRoot: join(directory, 'daemon'), daemonVersion: '0.15.1', pluginsEnabled: false,
    agentClients: { pi }, mcpEnabled: false, resumeOnStartup: false,
  });
  const cli = join(modules, '@getpaseo/cli/bin/paseo');
  const imported = JSON.parse((await promisify(execFile)(process.execPath, [
    cli, '--host', `127.0.0.1:${daemon.port}`, 'import', '--provider', 'pi', '--cwd', cwd, '--json', sessionFile,
  ], { timeout: 45000, env: { ...process.env, PI_CODING_AGENT_DIR: agentDir } })).stdout);
  assert.ok(imported.agentId, 'The real Paseo CLI imports the existing Pi session file');
  raw = new DaemonClient({ url: `ws://127.0.0.1:${daemon.port}/ws`, clientId: `task-import-${process.pid}` });
  await raw.connect();
  api = createPaseoApi(raw);
  const handle = api.agents.ref(imported.agentId);
  await handle.refresh();
  assert.equal(handle.cwd, cwd);
  const history = await handle.timeline.refetch({ direction: 'tail', limit: 100 });
  assert.match(JSON.stringify(history), /PASEO_TASK_IMPORT_HISTORY/);
  await handle.reload();
  assert.equal(handle.runtimeInfo?.sessionId, originalId, 'Interactive resume keeps the original Pi session UUID');
  assert.match(JSON.stringify(await handle.timeline.refetch({ direction: 'tail', limit: 100 })), /PASEO_TASK_IMPORT_HISTORY/);
  store = new Store(join(directory, 'tasks.sqlite'), raw.getLastServerInfoMessage().serverId);
  const unused = async () => { throw new Error('This launch-only check must not contact GitHub or another host'); };
  const service = new TaskService(store, api, { call: unused }, new Feedback(store, {
    observe: unused, login: unused, comments: unused, submit: unused,
  }, 'lanej'), 'entrypoint', 'pi/amazon-bedrock/us.anthropic.claude-sonnet-5-5');
  const brief = { title: 'Entrypoint launch', outcome: 'Retain one Pi conversation on a valid Paseo workspace',
    successCriteria: ['The official daemon accepts the reservation and preserves it on retry'], constraints: ['Do not send a provider prompt'],
    kind: 'investigation', repository: cwd, baseRef: null };
  const request = { serverId: store.serverId, brief, requestId: randomUUID(), group: null, start: true };
  const launched = await service.create(request);
  assert.ok(launched.worker, launched.error ?? 'The real Paseo entrypoint launches a task worker');
  const retry = await service.create(request);
  assert.deepEqual(retry.worker, launched.worker, 'Replay retains the same agent and workspace');
  await promisify(execFile)('git', ['init', '-b', 'main', cwd]);
  await writeFile(join(cwd, '.gitignore'), '.worktrees/\n');
  await writeFile(join(cwd, 'retained.txt'), 'Original checkout\n');
  await promisify(execFile)('git', ['-C', cwd, 'add', 'retained.txt', '.gitignore']);
  await promisify(execFile)('git', ['-C', cwd, '-c', 'user.name=Task fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Fixture']);
  const originalCommit = (await promisify(execFile)('git', ['-C', cwd, 'rev-parse', 'HEAD'])).stdout.trim();
  await promisify(execFile)('git', ['-C', cwd, 'update-ref', 'refs/remotes/origin/main', originalCommit]);
  await writeFile(join(cwd, 'retained.txt'), 'Local primary branch is ahead\n');
  await promisify(execFile)('git', ['-C', cwd, 'add', 'retained.txt']);
  await promisify(execFile)('git', ['-C', cwd, '-c', 'user.name=Task fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Local ahead']);
  const coding = await service.create({ ...request, requestId: randomUUID(), brief: {
    ...brief, kind: 'coding', baseRef: 'refs/remotes/origin/main',
  } });
  assert.ok(coding.worker, coding.error ?? 'The real Paseo entrypoint launches isolated coding work');
  codingLease = coding.treehouseLease;
  assert.ok(codingLease, 'The native coding entrypoint acquires a durable Treehouse lease');
  assert.equal(coding.worker.cwd, codingLease.path);
  assert.equal(codingLease.lease_holder, `paseo-task:${store.serverId}:${coding.taskId}`);
  assert.equal(coding.treehouseReservation.baseCommit, originalCommit, 'The exact requested base survives a locally ahead primary branch');
  assert.equal((await promisify(execFile)('git', ['rev-parse', 'HEAD'], { cwd: coding.worker.cwd })).stdout.trim(), originalCommit);
  const recoveredLease = await new Treehouse().acquire(coding.treehouseReservation,
    () => { throw new Error('Owned-lease recovery must not attempt another Treehouse acquisition'); });
  assert.deepEqual(recoveredLease, codingLease, 'Real native status restores the exact lease after a lost allocation response');
  assert.notEqual(coding.worker.cwd, cwd);
  assert.equal(await readFile(join(coding.worker.cwd, 'retained.txt'), 'utf8'), 'Original checkout\n');
  const conversations = await service.conversations();
  assert.ok([imported.agentId, launched.worker.agentId, coding.worker.agentId].every(id =>
    conversations.some(agent => agent.id === id)), 'The official directory API exposes imported and created conversations');
  result = { importedThrough: 'paseo import', historyRetained: true, sessionResumed: true,
    checkoutRetained: true, taskLaunch: true, launchReplayRetained: true, codingWorktreeIsolated: true, treehouseLease: true,
    conversationDirectory: true, pluginsEnabled: false };
} finally {
  store?.close();
  await api?.dispose();
  await raw?.close();
  await daemon?.close();
  if (codingLease) {
    const status = await promisify(execFile)('git', ['status', '--short', '--untracked-files=all'], { cwd: codingLease.path });
    assert.equal(status.stdout.trim(), '', 'The disposable fixture checkout is clean before returning its lease');
    const ignored = await promisify(execFile)('git', ['ls-files', '--others', '--ignored', '--exclude-standard'], { cwd: codingLease.path });
    assert.equal(ignored.stdout.trim(), '', 'The disposable fixture has no valuable ignored artifacts');
    await promisify(execFile)('treehouse', ['--root', codingLease.root, 'return', codingLease.path,
      '--if-lease-id', codingLease.lease_id, '--if-lease-holder', codingLease.lease_holder], { cwd, timeout: 45000 });
  }
  await rm(directory, { recursive: true, force: true });
}
console.log(JSON.stringify(result));
