#!/usr/bin/env node
// One native pi-subagents workflow. Only model responses are fixtures.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const BROKEN = 'export const total = (amount, fee) => amount - fee;\n';
const FIXED = 'export const total = (amount, fee) => amount + fee;\n';

function installedPackage(prefix, name, version) {
  const directory = join(prefix, 'node_modules', name);
  assert.ok(existsSync(join(directory, 'package.json')),
    'Set PI_DISPATCHER_RUNTIME to a prefix containing Pi 1.4.0 and pi-subagents 0.84.0');
  const metadata = JSON.parse(readFileSync(join(directory, 'package.json'), 'utf8'));
  assert.equal(metadata.version, version, name + ' version');
  return { directory, metadata };
}

function fixtureModel() {
  const requests = [], errors = [];
  let reviewedHandoff;
  function answer(payload) {
    requests.push(payload);
    assert.ok(requests.length <= 20, 'Fixture did not converge');
    const results = payload.messages.filter(message => message.role === 'tool');
    const call = (name, args) => ({ tool_calls: [{
      index: 0, id: 'fixture-' + requests.length, type: 'function',
      function: { name, arguments: JSON.stringify(args) },
    }] });
    if (payload.model === 'builder') {
      if (results.length === 0) return call('read', { path: 'price.mjs' });
      if (results.length === 1) return call('edit', { path: 'price.mjs', oldText: 'amount - fee', newText: 'amount + fee' });
      if (results.length === 2) return call('bash', { command: 'node --test' });
      assert.ok(JSON.stringify(results.at(-1)).includes('pass 1'), 'Worker did not observe a passing test');
      const fence = String.fromCharCode(96).repeat(3);
      return { content: 'Implemented the fee fix.\n\n' + fence + 'acceptance-report\n' + JSON.stringify({
        criteriaSatisfied: [
          { id: 'criterion-1', status: 'satisfied', evidence: 'The patch adds the fee.' },
          { id: 'criterion-2', status: 'satisfied', evidence: 'The required test passed.' },
        ],
        changedFiles: ['price.mjs'], testsAddedOrUpdated: [],
        commandsRun: [{ command: 'node --test', result: 'passed', summary: 'Fee regression passes.' }],
        validationOutput: ['node --test passed'], residualRisks: [], noStagedFiles: true, diffSummary: 'Add the fee.',
      }) + '\n' + fence };
    }
    if (payload.model === 'reviewer') {
      const tools = payload.tools.map(tool => tool.function.name);
      assert.ok(tools.includes('read'));
      assert.equal(tools.some(name => ['bash', 'edit', 'write'].includes(name)), false, 'Reviewer received mutation tools');
      const prompt = payload.messages.flatMap(message => typeof message.content === 'string'
        ? [message.content] : message.content?.filter(block => block.type === 'text').map(block => block.text) ?? [])
        .find(text => text.includes('Builder handoff:\n'));
      const handoff = JSON.parse(prompt.split('Builder handoff:\n')[1].split('\n\nRead the handoff')[0]);
      const manifestPath = join(handoff.artifactPaths[0], 'handoff.json');
      if (results.length === 0) return call('read', { path: manifestPath });
      if (results.length === 1) {
        reviewedHandoff = JSON.parse(readFileSync(manifestPath, 'utf8'));
        return call('read', { path: reviewedHandoff.groups[0].children[0].patch.path });
      }
      if (results.length === 2) {
        const evidence = JSON.stringify(results.at(-1));
        assert.ok(evidence.includes('+export const total = (amount, fee) => amount + fee;'),
          'Reviewer did not receive the actual captured patch');
        assert.equal(reviewedHandoff.runId, handoff.runId);
        return call('structured_output', { value: {
          reviewedRunId: handoff.runId, verdict: 'approve',
          review: 'No issues found. The captured patch adds the fee; host verification passed.',
        } });
      }
      return { content: 'Review complete.' };
    }
    assert.equal(payload.model, 'parent');
    return { content: 'Dispatcher trial ready.' };
  }
  const server = createServer(async (request, response) => {
    try {
      let body = '';
      for await (const chunk of request) body += chunk;
      const payload = JSON.parse(body);
      const delta = answer(payload);
      response.writeHead(200, { 'Content-Type': 'text/event-stream' });
      for (const [part, reason] of [[{ role: 'assistant', ...delta }, null],
        [{}, delta.tool_calls ? 'tool_calls' : 'stop']]) {
        response.write('data: ' + JSON.stringify({ id: 'fixture', object: 'chat.completion.chunk', created: 0,
          model: payload.model, choices: [{ index: 0, delta: part, finish_reason: reason }] }) + '\n\n');
      }
      response.end('data: [DONE]\n\n');
    } catch (error) {
      errors.push(error.message);
      response.writeHead(400, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ error: { message: error.message } }));
    }
  });
  return { server, requests, errors };
}

test('native Pi dispatcher fixes, verifies, reviews, and hands off an isolated patch', { timeout: 60000 }, async context => {
  const prefix = process.env.PI_DISPATCHER_RUNTIME;
  assert.ok(prefix, 'PI_DISPATCHER_RUNTIME must point to the isolated npm runtime; see docs/pi-dispatcher-review.md');
  const pi = installedPackage(resolve(prefix), '@earendil-works/pi-coding-agent', '1.4.0');
  const subagents = installedPackage(resolve(prefix), 'pi-subagents', '0.84.0');
  const sdk = await import(pathToFileURL(resolve(pi.directory, pi.metadata.exports['.'].import)).href);
  const directory = mkdtempSync(join(tmpdir(), 'pi-dispatcher-'));
  const repo = join(directory, 'repo'), agentDir = join(directory, 'agent');
  const { server, requests, errors } = fixtureModel();
  const envBefore = { PI_CODING_AGENT_DIR: process.env.PI_CODING_AGENT_DIR, TMPDIR: process.env.TMPDIR,
    PI_SKIP_VERSION_CHECK: process.env.PI_SKIP_VERSION_CHECK, PI_TELEMETRY: process.env.PI_TELEMETRY };
  let session, rpc, launch, complete = false, timeout, offComplete = () => {};
  const extensionErrors = [];
  try {
    mkdirSync(repo); mkdirSync(agentDir); mkdirSync(join(directory, 'tmp'));
    const git = (...args) => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8' }).trim();
    git('init', '-q'); git('config', 'user.name', 'Pi Fixture'); git('config', 'user.email', 'fixture@example.invalid');
    writeFileSync(join(repo, '.gitignore'), '.pi/\n');
    writeFileSync(join(repo, 'price.mjs'), BROKEN);
    writeFileSync(join(repo, 'price.test.mjs'),
      "import {test} from 'node:test'; import assert from 'node:assert/strict'; import {total} from './price.mjs';\n"
      + "test('adds the fee',()=>assert.equal(total(100,5),105));\n");
    git('add', '.'); git('commit', '-qm', 'Fixture regression');
    const base = git('rev-parse', 'HEAD');
    assert.notEqual(spawnSync(process.execPath, ['--test'], { cwd: repo }).status, 0, 'The original bug must fail');

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    writeFileSync(join(agentDir, 'models.json'), JSON.stringify({ providers: { fixture: {
      baseUrl: 'http://127.0.0.1:' + server.address().port + '/v1', api: 'openai-completions', apiKey: 'fixture',
      models: [{ id: 'parent' }, { id: 'builder' }, { id: 'reviewer' }],
    } } }));
    writeFileSync(join(agentDir, 'settings.json'), JSON.stringify({
      defaultProvider: 'fixture', defaultModel: 'parent', retry: { enabled: false },
      subagents: { defaultExtensions: [], disableThinking: true },
    }));
    mkdirSync(join(agentDir, 'extensions/subagent'), { recursive: true });
    writeFileSync(join(agentDir, 'extensions/subagent/config.json'),
      JSON.stringify({ worktreeProvider: 'native', intercomBridge: { mode: 'off' }, timeoutMs: 20000 }));
    Object.assign(process.env, { PI_CODING_AGENT_DIR: agentDir, TMPDIR: join(directory, 'tmp'),
      PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0' });
    const bus = sdk.createEventBus();
    const settingsManager = sdk.SettingsManager.create(repo, agentDir);
    const resourceLoader = new sdk.DefaultResourceLoader({
      cwd: repo, agentDir, settingsManager, eventBus: bus, noExtensions: true,
      noSkills: true, noPromptTemplates: true, noThemes: true, noContextFiles: true,
      additionalExtensionPaths: [resolve(subagents.directory, subagents.metadata.pi.extensions[0])],
    });
    await resourceLoader.reload();
    assert.deepEqual(resourceLoader.getExtensions().errors, []);
    ({ session } = await sdk.createAgentSession({
      cwd: repo, agentDir, settingsManager, resourceLoader,
      sessionManager: sdk.SessionManager.create(repo, join(agentDir, 'sessions')),
    }));
    await session.bindExtensions({ onError: error => extensionErrors.push(error) });
    await session.prompt('Initialize this disposable dispatcher trial. Acknowledge only.');
    rpc = (method, params = {}) => new Promise((resolve, reject) => {
      const requestId = randomUUID();
      const timer = setTimeout(() => { off(); reject(new Error('pi-subagents RPC timed out: ' + method)); }, 10000);
      const off = bus.on('subagents:rpc:v1:reply:' + requestId, reply => {
        clearTimeout(timer); off();
        reply.success ? resolve(reply.data) : reject(new Error(JSON.stringify(reply.error)));
      });
      bus.emit('subagents:rpc:v1:request', { version: 1, requestId, method, params });
    });
    const ping = await rpc('ping');
    const completions = new Map();
    let finished;
    const completion = new Promise((resolve, reject) => {
      finished = resolve;
      timeout = setTimeout(() => reject(new Error('Native workflow timed out: ' + errors.join('; '))), 45000);
    });
    offComplete = bus.on(ping.events.asyncComplete, event => {
      completions.set(event.id, event);
      if (event.id === launch?.details.runId) finished(event);
    });
    launch = await rpc('spawn', {
      workflow: join(ROOT, 'pi/workflows/bugfix.js'), cwd: repo, timeoutMs: 40000,
      args: { task: 'Fix total() so that it adds the fee in price.mjs.', verifyCommand: 'node --test',
        workerModel: 'fixture/builder', reviewerModel: 'fixture/reviewer', timeoutMs: 20000 },
    });
    if (completions.has(launch.details.runId)) finished(completions.get(launch.details.runId));
    const event = await completion;
    complete = true;
    clearTimeout(timeout);
    const status = await rpc('status', { id: launch.details.runId });
    const state = JSON.parse(readFileSync(join(launch.details.asyncDir, 'status.json'), 'utf8'));
    assert.equal(event.success, true, state.error ?? errors.join('; '));
    assert.equal(state.state, 'complete');
    assert.equal(status.details.workflowTerminalProof.state, 'observed');
    assert.deepEqual(errors, []);
    assert.deepEqual(extensionErrors, []);
    const result = state.workflow.value;
    assert.equal(result.status, 'ready_for_integration');
    assert.equal(result.finished, false);
    assert.equal(result.review.verdict, 'approve');
    assert.equal(result.review.reviewedRunId, result.handoff.runId);
    assert.notEqual(result.review.runId, result.handoff.runId, 'Review must be a fresh child');
    const evidence = result.handoff.acceptance;
    assert.equal(evidence.evidenceStatus, 'verified');
    const check = evidence.verifyRuns.find(check => check.id === 'required');
    assert.equal(check.status, 'passed');
    assert.equal(check.command, 'node --test');
    assert.equal(check.exitCode, 0);
    assert.notEqual(check.cwd, repo, 'Required verification must run in the managed worktree');
    assert.equal(git('rev-parse', 'HEAD'), base);
    assert.equal(git('status', '--porcelain'), '');
    assert.equal(readFileSync(join(repo, 'price.mjs'), 'utf8'), BROKEN);
    const handoff = JSON.parse(readFileSync(join(result.handoff.artifactPaths[0], 'handoff.json'), 'utf8'));
    assert.equal(handoff.runId, result.handoff.runId);
    const group = handoff.groups[0];
    assert.equal(group.baseCommit, base);
    if (group.cleanup.state !== 'complete') context.diagnostic('Worktree retained: ' + JSON.stringify(group.cleanup));
    const patch = group.children[0].patch.path;
    assert.ok(requests.some(request => request.model === 'reviewer'
      && JSON.stringify(request.messages).includes('+export const total')));
    // The parent accepts only the captured patch against its exact base, then verifies again.
    git('apply', '--check', patch); git('apply', patch);
    assert.equal(readFileSync(join(repo, 'price.mjs'), 'utf8'), FIXED);
    execFileSync(process.execPath, ['--test'], { cwd: repo });
    assert.equal(git('rev-parse', 'HEAD'), base, 'The workflow must not commit or finish');
  } finally {
    clearTimeout(timeout);
    offComplete();
    if (launch && !complete && rpc) {
      try { await rpc('stop', { id: launch.details.runId }); } catch {}
    }
    if (session) {
      await session.abort();
      await session.extensionRunner.emit({ type: 'session_shutdown', reason: 'quit' });
      session.dispose();
    }
    if (server.listening) {
      server.closeAllConnections();
      await new Promise(resolve => server.close(resolve));
    }
    for (const [name, value] of Object.entries(envBefore)) {
      if (value === undefined) delete process.env[name]; else process.env[name] = value;
    }
    rmSync(directory, { recursive: true, force: true });
  }
});
