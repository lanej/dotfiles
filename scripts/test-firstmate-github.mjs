import assert from 'node:assert/strict';
import { execFileSync, spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import * as fs from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import test from 'node:test';
import { run, configurePi, configurePiRouter } from '../firstmate/github-feedback.mjs';
import { renderBoard, localTaskObservations } from '../firstmate/tasks.mjs';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const delay = ms => new Promise(accept => setTimeout(accept, ms));
async function until(predicate, description) {
  const end = Date.now() + 45000;
  while (Date.now() < end) { if (await predicate()) return; await delay(100); }
  throw new Error(`Timed out: ${description}`);
}
async function json(path) { return JSON.parse(await fs.readFile(path, 'utf8')); }
async function write(path, value) { await fs.mkdir(resolve(path, '..'), { recursive: true }); await fs.writeFile(path, value); }
const logger = { child() { return this; }, debug() {}, info() {}, warn() {}, error() {}, trace() {} };

test('Pi discovers the Bedrock router and preserves its session identity across a resumed Sol exchange', { timeout: 60000 }, async () => {
  const runtime = process.env.FIRSTMATE_TEST_RUNTIME;
  assert.ok(runtime, 'Set FIRSTMATE_TEST_RUNTIME with Pi 1.4.0 and Paseo 0.15.1');
  const modules = join(resolve(runtime), 'node_modules');
  const { PiCliRuntime } = await import(pathToFileURL(join(modules, '@getpaseo/server/dist/server/server/agent/providers/pi/cli-runtime.js')));
  const directory = await fs.mkdtemp('/tmp/firstmate-router-'), agentDir = join(directory, '.pi/agent');
  const settingsPath = join(agentDir, 'settings.json'), modelsPath = join(agentDir, 'models.json');
  const defaults = { theme: 'dark', defaultProvider: 'amazon-bedrock', defaultModel: 'us.anthropic.claude-sonnet-5-5', defaultThinkingLevel: 'medium' };
  const unrelated = { api: 'openai-completions', apiKey: 'fixture', baseUrl: 'http://127.0.0.1:1/v1', models: [{ id: 'unrelated' }] };
  const requests = [], failures = [];
  let client, server;
  try {
    await write(settingsPath, JSON.stringify(defaults));
    await write(modelsPath, JSON.stringify({ providers: { unrelated } }));
    await configurePi(settingsPath); await configurePiRouter(modelsPath);
    await configurePi(settingsPath); await configurePiRouter(modelsPath);
    const installedSettings = await json(settingsPath);
    assert.deepEqual(Object.fromEntries(Object.keys(defaults).map(key => [key, installedSettings[key]])), defaults);
    const installedModels = await json(modelsPath);
    assert.deepEqual(installedModels.providers.unrelated, unrelated);
    server = createServer(async (request, response) => {
      try {
        let body = ''; for await (const chunk of request) body += chunk;
        const payload = JSON.parse(body);
        assert.equal(request.url, '/openai/v1/responses');
        assert.equal(request.headers.authorization, 'Bearer fixture-bedrock-token');
        assert.equal(payload.model, 'openai.gpt-6.1-sol');
        assert.equal(payload.store, false, 'The local route keeps Pi response storage disabled');
        assert.ok(request.headers['session-id'], 'The router must receive its recognized session field');
        requests.push({ sessionId: request.headers['session-id'] });
        const item = { id: `msg_${requests.length}`, type: 'message', role: 'assistant', content: [{ type: 'output_text', text: 'ROUTER_FIXTURE_OK', annotations: [] }] };
        response.writeHead(200, { 'content-type': 'text/event-stream' });
        for (const event of [
          { type: 'response.output_item.added', output_index: 0, item: { ...item, content: [] } },
          { type: 'response.content_part.added', item_id: item.id, output_index: 0, content_index: 0, part: { type: 'output_text', text: '', annotations: [] } },
          { type: 'response.output_text.delta', item_id: item.id, output_index: 0, content_index: 0, delta: 'ROUTER_FIXTURE_OK' },
          { type: 'response.output_item.done', output_index: 0, item },
          { type: 'response.completed', response: { id: `resp_${requests.length}`, status: 'completed', output: [item], usage: { input_tokens: 1, output_tokens: 1, total_tokens: 2 } } },
        ]) response.write(`data: ${JSON.stringify(event)}\n\n`);
        response.end();
      } catch (error) { failures.push(error.message); response.writeHead(500); response.end('Fixture rejected request'); }
    });
    await new Promise(accept => server.listen(0, '127.0.0.1', accept));
    installedModels.providers['bedrock-router'].baseUrl = `http://127.0.0.1:${server.address().port}/openai/v1`;
    await write(modelsPath, JSON.stringify(installedModels));
    const env = { ...process.env, HOME: directory, PI_CODING_AGENT_DIR: agentDir, PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0',
      AWS_BEARER_TOKEN_BEDROCK: 'fixture-bedrock-token' };
    for (const key of ['NODE_TEST_CONTEXT', 'FM_HOME', 'FIRSTMATE_HOME', 'FM_TASK_ID']) delete env[key];
    const launch = session => new PiCliRuntime({ logger, command: [join(modules, '.bin/pi')] }).startSession({
      cwd: directory, env, model: 'bedrock-router/openai.gpt-6.1-sol', session,
      extraArgs: ['--no-extensions', '--extension', join(ROOT, 'pi/extensions/firstmate-bedrock-router.mjs')],
    });
    client = await launch();
    assert.ok((await client.getAvailableModels()).some(model => model.provider === 'bedrock-router' && model.id === 'openai.gpt-6.1-sol'));
    const before = await client.getState();
    await client.prompt('Reply through the router fixture');
    await until(async () => !(await client.getState()).isStreaming, 'Sol response through the router');
    assert.ok((await client.getMessages()).some(message => message.role === 'assistant' && JSON.stringify(message).includes('ROUTER_FIXTURE_OK')));
    await client.close(); client = await launch(before.sessionFile);
    assert.equal((await client.getState()).sessionId, before.sessionId);
    await client.prompt('Reply after reconnect');
    await until(async () => !(await client.getState()).isStreaming, 'resumed Sol response through the router');
    assert.deepEqual(requests, [{ sessionId: before.sessionId }, { sessionId: before.sessionId }]);
    assert.deepEqual(failures, []);
  } finally {
    await client?.close();
    if (server) { server.closeAllConnections(); await new Promise(accept => server.close(accept)); }
    await fs.rm(directory, { recursive: true, force: true });
  }
});

test('Firstmate questions reach native Paseo cards, survive a client reconnect, and preserve answers and cancellation on resume', { timeout: 60000 }, async () => {
  const runtime = process.env.FIRSTMATE_TEST_RUNTIME, source = process.env.FIRSTMATE_SOURCE;
  assert.ok(runtime && source, 'Set FIRSTMATE_TEST_RUNTIME and FIRSTMATE_SOURCE for the native Pi/Paseo question bridge');
  const modules = join(resolve(runtime), 'node_modules');
  const { PiCliRuntime } = await import(pathToFileURL(join(modules, '@getpaseo/server/dist/server/server/agent/providers/pi/cli-runtime.js')));
  const { PiRpcAgentClient } = await import(pathToFileURL(join(modules, '@getpaseo/server/dist/server/server/agent/providers/pi/agent.js')));
  const directory = await fs.mkdtemp('/tmp/firstmate-questions-'), fleet = join(directory, 'fleet'), agentDir = join(directory, '.pi/agent');
  const questions = [
    { header: 'Scope', question: 'Which fixture scope should I use?', options: [
      { label: 'Read only', description: 'Inspect the fixture' }, { label: 'Edit', description: 'Change the fixture' },
    ] },
    { header: 'Result', question: 'How should I report the fixture result?', options: [
      { label: 'Brief', description: 'One sentence' }, { label: 'Detailed', description: 'Include evidence' },
    ] },
  ];
  const requests = [], errors = [], events = [], rpcEvents = [];
  let session, worker, server, unsubscribe;
  try {
    await fs.mkdir(join(fleet, 'state'), { recursive: true });
    const fixture = join(directory, 'ownership.mjs');
    await write(fixture, `import {writeFileSync} from 'node:fs';export default function(pi){pi.on('session_start',()=>{if(!process.env.FM_TASK_ID)writeFileSync(${JSON.stringify(join(fleet, 'state/.lock'))},String(process.pid));});}\n`);
    server = createServer(async (request, response) => {
      try {
        let body = ''; for await (const chunk of request) body += chunk;
        const payload = JSON.parse(body); requests.push(payload);
        assert.ok(requests.length < 15, 'Question fixture did not converge');
        const at = payload.messages.findLastIndex(message => message.role === 'user');
        const outputs = payload.messages.slice(at + 1).filter(message => message.role === 'tool');
        const content = payload.messages[at].content;
        const prompt = typeof content === 'string' ? content : content.filter(block => block.type === 'text').map(block => block.text).join('\n');
        const isWorker = prompt === 'Inspect worker tool availability.';
        assert.equal(payload.tools.some(tool => tool.function.name === 'ask_user_question'), !isWorker,
          'The question tool must reach the captain model and stay absent from a worker');
        const batches = prompt === 'Ask two independent question calls.' ? questions.map(question => [question])
          : prompt === 'Ask malformed questions with duplicate headers.' ? [questions.map(question => ({ ...question, header: 'Repeated' }))] : [questions];
        const delta = isWorker ? { content: 'Worker has no captain question tool.' }
          : outputs.length ? { content: `Question result: ${outputs.map(output => output.content).join('\n')}` }
          : { tool_calls: batches.map((batch, index) => ({ index, id: `question-${requests.length}-${index}`, type: 'function',
            function: { name: 'ask_user_question', arguments: JSON.stringify({ questions: batch }) } })) };
        response.writeHead(200, { 'Content-Type': 'text/event-stream' });
        response.end(`data: ${JSON.stringify({ choices: [{ index: 0, delta, finish_reason: null }] })}\n\ndata: ${JSON.stringify({ choices: [{ index: 0, delta: {}, finish_reason: delta.tool_calls ? 'tool_calls' : 'stop' }] })}\n\ndata: [DONE]\n\n`);
      } catch (error) { errors.push(error.stack); response.writeHead(500); response.end(); }
    });
    await new Promise(accept => server.listen(0, '127.0.0.1', accept));
    await write(join(agentDir, 'models.json'), JSON.stringify({ providers: { fixture: {
      baseUrl: `http://127.0.0.1:${server.address().port}/v1`, apiKey: 'fixture', api: 'openai-completions',
      models: [{ id: 'questions', name: 'questions', reasoning: false, input: ['text'], contextWindow: 128000,
        maxTokens: 2048, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } }],
    } } }));
    const env = { ...process.env, HOME: directory, PI_CODING_AGENT_DIR: agentDir, FIRSTMATE_HOME: fleet,
      FM_HOME: fleet, FIRSTMATE_SOURCE: resolve(source), PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0' };
    for (const key of ['NODE_TEST_CONTEXT', 'FM_TASK_ID']) delete env[key];
    const rpc = new PiCliRuntime({ logger, command: [
      join(modules, '.bin/pi'), '--no-extensions', '--extension', fixture,
      '--extension', join(ROOT, 'pi/extensions/firstmate-questions.mjs'),
    ] });
    const client = new PiRpcAgentClient({ logger, runtime: { async startSession(input) {
      const channel = await rpc.startSession(input);
      channel.onEvent(event => rpcEvents.push(event));
      return channel;
    } } });
    session = await client.createSession({ provider: 'pi', cwd: fleet, model: 'fixture/questions' }, { env });
    unsubscribe = session.subscribe(event => events.push(event));
    const first = session.run('Ask the fixture questions.');
    await until(() => session.getPendingPermissions().length === 1, 'native Paseo question card');
    const card = session.getPendingPermissions()[0], handle = session.describePersistence();
    assert.equal(card.kind, 'question');
    assert.ok(card.id.startsWith('rpiv-question:'), 'The structured Paseo adapter recognizes the registered tool');
    assert.deepEqual(card.input.questions, questions.map(question => ({ ...question, multiSelect: false, allowOther: true })));
    unsubscribe(); unsubscribe = undefined;
    await delay(100);
    assert.equal(session.getPendingPermissions()[0].id, card.id, 'The disconnected client does not dismiss the question');
    unsubscribe = session.subscribe(event => events.push(event));
    await session.respondToPermission(card.id, { behavior: 'allow', updatedInput: { answers: {
      Scope: 'Read only', Result: 'Report the exact token, please.',
    } } });
    const result = await first;
    assert.ok(result.finalText.includes('"answer":"Read only"'), result.finalText);
    assert.ok(result.finalText.includes('"kind":"custom","answer":"Report the exact token, please."'));
    assert.ok(events.some(event => event.type === 'timeline' && event.item.type === 'tool_call' &&
      event.item.detail?.label === 'Questions' && event.item.detail.text.includes('Report the exact token, please.')),
    'Paseo renders the actual answers in its question tool row');
    const paired = session.run('Ask two independent question calls.');
    // WHY: Preserve the card assertion if fixture cleanup rejects this still-running turn.
    paired.catch(() => {});
    await until(() => session.getPendingPermissions().length > 0, 'first card from a model question batch');
    await delay(100);
    assert.equal(session.getPendingPermissions().length, 1, 'Question calls must serialize through the single-dialog Paseo adapter');
    const firstCard = session.getPendingPermissions()[0];
    assert.equal(firstCard.input.questions[0].header, 'Scope');
    await session.respondToPermission(firstCard.id, { behavior: 'allow', updatedInput: { answers: { Scope: 'Edit' } } });
    await until(() => session.getPendingPermissions().length === 1 && session.getPendingPermissions()[0].id !== firstCard.id, 'second card after first answer');
    assert.equal(session.getPendingPermissions()[0].input.questions[0].header, 'Result');
    await session.respondToPermission(session.getPendingPermissions()[0].id, { behavior: 'allow', updatedInput: { answers: { Result: 'Detailed' } } });
    const pairedResult = await paired;
    assert.ok(pairedResult.finalText.includes('"answer":"Edit"') && pairedResult.finalText.includes('"answer":"Detailed"'),
      'Answers stay correlated to both independent calls in one model message');
    assert.equal(session.getPendingPermissions().length, 0, 'No question card remains stranded after a batch');
    unsubscribe(); unsubscribe = undefined;
    await session.close(); session = await client.resumeSession(handle, undefined, { env });
    unsubscribe = session.subscribe(event => events.push(event));
    assert.equal(session.id, handle.sessionId, 'Host resume keeps the same persisted conversation');
    const cancelled = session.run('Ask again, and allow the captain to cancel.');
    await until(() => session.getPendingPermissions().length === 1, 'question available after captain resume');
    await session.respondToPermission(session.getPendingPermissions()[0].id, { behavior: 'deny', message: 'Cancelled fixture question' });
    const cancellation = await cancelled;
    assert.ok(cancellation.finalText.includes('"answers":[],"cancelled":true'), 'Cancellation supplies no fabricated approval');
    const malformed = await session.run('Ask malformed questions with duplicate headers.');
    assert.ok(malformed.finalText.includes('distinct nonempty headers'), 'Repeated headers fail before any answer can be used');
    assert.equal(session.getPendingPermissions().length, 1, 'Official Paseo retains a card after execute-side validation failure');
    await session.respondToPermission(session.getPendingPermissions()[0].id, { behavior: 'deny', message: 'Dismiss failed fixture question' });
    assert.equal(session.getPendingPermissions().length, 0, 'Dismissing the stale card clears it without an answer');
    const dialogCount = rpcEvents.filter(event => event.type === 'extension_ui_request' && event.method === 'select').length;
    const interrupted = session.run('Ask a question that the captain will stop.');
    await until(() => session.getPendingPermissions().length === 1, 'question pending before Stop');
    await until(() => rpcEvents.filter(event => event.type === 'extension_ui_request' && event.method === 'select').length > dialogCount,
      'the question dialog is waiting for an answer before Stop');
    await session.interrupt(); const stopped = await interrupted;
    assert.ok(events.some(event => event.type === 'turn_canceled'), 'Stop actually interrupts the native provider turn');
    assert.ok(stopped.timeline.some(item => item.type === 'tool_call' && item.detail?.label === 'Questions' && item.detail.text === 'Cancelled'),
      `An aborted dialog records cancellation instead of a choice: ${JSON.stringify(stopped.timeline)}`);
    assert.equal(session.getPendingPermissions().length, 1, 'Official Paseo retains the stopped question card');
    await session.respondToPermission(session.getPendingPermissions()[0].id, { behavior: 'deny', message: 'Dismiss stopped fixture question' });
    assert.equal(session.getPendingPermissions().length, 0, 'Dismissing a stopped card clears the pending request');
    const recovered = session.run('Ask again after dismissing the stopped card.');
    await until(() => session.getPendingPermissions().length === 1, 'captain question after Stop recovery');
    await session.respondToPermission(session.getPendingPermissions()[0].id, { behavior: 'allow', updatedInput: { answers: {
      Scope: 'Read only', Result: 'Brief',
    } } });
    assert.ok((await recovered).finalText.includes('"answer":"Brief"'), 'The same captain session accepts a fresh question after Stop recovery');
    const owner = await fs.readFile(join(fleet, 'state/.lock'), 'utf8');
    worker = await client.createSession({ provider: 'pi', cwd: fleet, model: 'fixture/questions' }, { env: { ...env, FM_TASK_ID: 'fixture-worker' } });
    assert.equal((await worker.run('Inspect worker tool availability.')).finalText, 'Worker has no captain question tool.');
    assert.equal(await fs.readFile(join(fleet, 'state/.lock'), 'utf8'), owner, 'Checking the worker tool list preserves captain ownership');
    assert.deepEqual(errors, []);
  } finally {
    unsubscribe?.(); await worker?.close(); await session?.close();
    if (server) { server.closeAllConnections(); await new Promise(accept => server.close(accept)); }
    await fs.rm(directory, { recursive: true, force: true });
    if (errors.length) console.error(errors.join('\n'));
  }
});

test('Paseo resumes Firstmate and its Pi owner, catches up GitHub review, and records one verified revision', { timeout: 120000 }, async () => {
  const runtime = process.env.FIRSTMATE_TEST_RUNTIME;
  const source = process.env.FIRSTMATE_SOURCE;
  assert.ok(runtime && source, 'Set FIRSTMATE_TEST_RUNTIME (Pi 1.4.0, Paseo 0.15.1, tasks-axi 0.2.6) and FIRSTMATE_SOURCE');
  const modules = join(resolve(runtime), 'node_modules');
  assert.equal((await json(join(modules, '@earendil-works/pi-coding-agent/package.json'))).version, '1.4.0');
  assert.equal((await json(join(modules, '@getpaseo/server/package.json'))).version, '0.15.1');
  const { PiCliRuntime } = await import(pathToFileURL(join(modules, '@getpaseo/server/dist/server/server/agent/providers/pi/cli-runtime.js')));
  const { ProviderOverridesSchema } = await import(pathToFileURL(join(modules, '@getpaseo/protocol/dist/provider-config.js')));
  const directory = await fs.mkdtemp(join(tmpdir(), 'firstmate-github-'));
  const childEnv = { ...process.env }; delete childEnv.NODE_TEST_CONTEXT;
  const testContext = process.env.NODE_TEST_CONTEXT; delete process.env.NODE_TEST_CONTEXT;
  const home = join(directory, 'home'), fleet = join(home, 'src/firstmate'), worktree = join(directory, 'worktree');
  const issue = 'https://github.com/lanej/fixture/issues/7', pr = 'https://github.com/lanej/fixture/pull/8';
  const errors = [], requests = [], comments = [], inline = [], reviews = [], posted = [], modelRequests = [];
  const remote = join(directory, 'origin.git');
  let task, originalHead;
  const remoteHead = branch => execFileSync('git', ['--git-dir', remote, 'rev-parse', `refs/heads/${branch}`], { encoding: 'utf8' }).trim();
  let main, worker, origin, runtimeEnv;
  const server = createServer(async (request, response) => {
    try {
      let body = ''; for await (const chunk of request) body += chunk;
      const url = new URL(request.url, origin);
      if (url.pathname === '/v1/chat/completions') {
        const payload = JSON.parse(body); modelRequests.push(payload);
        assert.ok(modelRequests.length < 50, 'Model fixture did not converge');
        const messageText = message => typeof message.content === 'string' ? message.content
          : (message.content ?? []).filter(block => block.type === 'text').map(block => block.text).join('\n');
        const index = payload.messages.findLastIndex(message => messageText(message).includes('GitHub feedback for your assigned task'));
        let delta = { content: 'Work recorded; awaiting the next task event.' };
        if (payload.model === 'worker' && index >= 0) {
          const event = JSON.parse(messageText(payload.messages[index]).split('\n\n').at(-1));
          const outputs = payload.messages.slice(index + 1).filter(message => message.role === 'tool');
          const call = (name, args) => ({ tool_calls: [{ index: 0, id: `fixture-${modelRequests.length}`, type: 'function',
            function: { name, arguments: JSON.stringify(args) } }] });
          if (event.type === 'inline') {
            assert.equal(event.authority, 'owner-direction', 'Human feedback shares the agent’s GitHub login');
            if (outputs.length === 0) delta = call('read', { path: 'price.mjs' });
            else if (outputs.length === 1) delta = call('edit', { path: 'price.mjs', oldText: 'amount - fee', newText: 'amount + fee' });
            else if (outputs.length === 2) delta = call('bash', { command: 'node --test' });
            else if (outputs.length === 3) {
              assert.match(JSON.stringify(outputs.at(-1)), /pass 1/, `The real regression must pass before replying: ${JSON.stringify(outputs.at(-1))}`);
              delta = call('bash', { command: 'git add price.mjs' });
            } else if (outputs.length === 4) delta = call('bash', { command: "git commit -m 'fix: add fee'" });
            else if (outputs.length === 5) delta = call('bash', { command: 'git push origin HEAD' });
            else if (outputs.length === 6) {
              delta = call('firstmate_github_reply', { eventId: event.id, body: 'Fixed the fee calculation. node --test passes; ready for another review.' });
            } else if (outputs.length === 7) delta = call('firstmate_github_done', { eventId: event.id, summary: `${pr} revised and verified`, needsFirstmate: false });
          } else if (outputs.length === 0) delta = call('firstmate_github_done', { eventId: event.id, summary: `${event.url} discussion/check state reviewed`, needsFirstmate: false });
        }
        response.writeHead(200, { 'Content-Type': 'text/event-stream' });
        for (const [part, reason] of [[{ role: 'assistant', ...delta }, null], [{}, delta.tool_calls ? 'tool_calls' : 'stop']]) {
          response.write('data: ' + JSON.stringify({ id: 'fixture', object: 'chat.completion.chunk', created: 0,
            model: payload.model, choices: [{ index: 0, delta: part, finish_reason: reason }] }) + '\n\n');
        }
        response.end('data: [DONE]\n\n'); return;
      }
      requests.push([request.method, url.pathname]);
      assert.equal(request.headers.authorization, 'Bearer fixture-token');
      let output;
      if (url.pathname === '/user') output = { login: 'lanej' };
      else if (url.pathname === '/graphql' && request.method === 'POST') {
        assert.match(JSON.parse(body).query, /^query\(/);
        output = { data: { repository: { pullRequest: { reviewThreads: { nodes: inline.filter(comment => !comment.in_reply_to_id).map(comment => ({
          id: `thread-${comment.id}`, isResolved: false, comments: { nodes: [{ databaseId: comment.id }] },
        })), pageInfo: { hasNextPage: false, endCursor: null } } } } } };
      }
      else if (url.pathname === '/repos/lanej/fixture/issues/7') output = { title: 'Correct the fee calculation', state: 'open', labels: [] };
      else if (url.pathname === '/repos/lanej/fixture/issues/7/comments') output = comments;
      else if (url.pathname === '/repos/lanej/fixture/pulls/8') output = { state: 'open', head: { sha: remoteHead('fix-fee') }, labels: [], merged: false, draft: false, mergeable: true };
      else if (url.pathname === '/repos/lanej/fixture/pulls/8/reviews') output = reviews;
      else if (url.pathname === '/repos/lanej/fixture/pulls/8/comments') output = inline;
      else if (url.pathname === '/repos/lanej/fixture/issues/8/comments') output = posted;
      else if (/\/commits\/.*\/check-runs$/.test(url.pathname)) output = { check_runs: [{ id: 1, name: 'tests', status: 'completed', conclusion: 'success' }] };
      else if (/\/commits\/.*\/statuses$/.test(url.pathname)) output = [];
      else if (url.pathname === '/repos/lanej/fixture/pulls/8/comments/12/replies' && request.method === 'POST') {
        output = { id: 100, body: JSON.parse(body).body, user: { login: 'lanej' }, html_url: `${pr}#discussion_r100`, updated_at: '2026-11-02T01:03:00Z', in_reply_to_id: 12 };
        inline.push(output); posted.push(output);
      } else throw new Error(`Unexpected GitHub mutation or endpoint: ${request.method} ${url.pathname}`);
      const encoded = JSON.stringify(output), etag = '"' + createHash('sha256').update(encoded).digest('hex') + '"';
      if (request.method === 'GET' && request.headers['if-none-match'] === etag) {
        response.writeHead(304, { ETag: etag }); response.end();
      } else {
        response.writeHead(200, { 'Content-Type': 'application/json', ETag: etag }); response.end(encoded);
      }
    } catch (error) { errors.push(error.stack); response.writeHead(500); response.end(JSON.stringify({ error: error.message })); }
  });
  try {
    await new Promise(accept => server.listen(0, '127.0.0.1', accept));
    origin = `http://127.0.0.1:${server.address().port}`;
    await fs.mkdir(join(fleet, 'state'), { recursive: true });
    await fs.mkdir(join(fleet, 'data'), { recursive: true });
    await fs.mkdir(join(fleet, 'config'), { recursive: true });
    await fs.mkdir(worktree);
    await fs.symlink(join(resolve(source), 'bin'), join(fleet, 'bin'));
    await fs.symlink(join(resolve(source), '.tasks.toml'), join(fleet, '.tasks.toml'));
    // Native Firstmate dispatch/supervision is exercised by its existing detector.
    // Here task metadata is seeded; ambient primary extensions are deliberately disabled.
    for (const name of ['fm-primary-pi-watch', 'fm-primary-turnend-guard', 'fm-branch-supervision']) {
      await write(join(fleet, '.pi/extensions', `${name}.ts`), 'export default function () {}\n');
    }
    await write(join(fleet, 'data/backlog.md'), '# Backlog\n\n## In flight\n\n## Queued\n\n## Done\n');
    await write(join(worktree, 'price.mjs'), 'export const total = (amount, fee) => amount - fee;\n');
    await write(join(worktree, 'price.test.mjs'), "import {test} from 'node:test';import assert from 'node:assert/strict';import {total} from './price.mjs';test('adds fee',()=>assert.equal(total(100,5),105));\n");
    const git = (...args) => execFileSync('git', ['-C', worktree, ...args], { encoding: 'utf8' }).trim();
    git('init', '-q', '-b', 'main'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
    git('add', '.'); git('commit', '-qm', 'fixture');
    const head = git('rev-parse', 'HEAD');
    originalHead = head;
    execFileSync('git', ['init', '--bare', '-q', remote]);
    git('remote', 'add', 'origin', remote); git('push', '-q', 'origin', 'main');
    git('switch', '-qc', 'fix-fee'); git('push', '-q', 'origin', 'fix-fee');
    assert.throws(() => execFileSync('node', ['--test'], { cwd: worktree, env: childEnv, stdio: 'pipe' }), 'The actual fee regression starts red');
    const env = { ...childEnv, HOME: home, FIRSTMATE_HOME: fleet, FIRSTMATE_SOURCE: resolve(source), GH_TOKEN: 'fixture-token',
      PATH: `${join(modules, '.bin')}:${process.env.PATH}`, PI_CODING_AGENT_DIR: join(home, '.pi/agent'), PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0',
      FM_ZELLIJ_SESSION: `firstmate-github-${process.pid}` };
    runtimeEnv = env;
    delete env.FM_TASK_ID; delete env.FM_TASK_INBOX; delete env.FM_HOME; delete env.GITHUB_TOKEN;
    await write(join(fleet, 'config/crew-harness'), 'pi\n');
    await write(join(home, '.pi/agent/settings.json'), JSON.stringify({ theme: 'dark', extensions: [] }));
    await write(join(home, '.paseo/config.json'), JSON.stringify({ listen: '127.0.0.1:6767', agents: { providers: { codex: { enabled: true } } } }));
    execFileSync('make', ['firstmate-mobile-config', `FIRSTMATE_HOME=${fleet}`], { cwd: ROOT, env, stdio: 'pipe' });
    await write(join(fleet, 'config/github-feedback.json'), JSON.stringify({ owner: 'lanej', pollSeconds: 10 }));
    execFileSync('make', ['firstmate-mobile-config', `FIRSTMATE_HOME=${fleet}`], { cwd: ROOT, env, stdio: 'pipe' });
    assert.equal((await json(join(home, '.pi/agent/settings.json'))).theme, 'dark');
    assert.equal((await json(join(fleet, 'config/github-feedback.json'))).pollSeconds, 10);
    assert.equal(await fs.readFile(join(fleet, 'config/crew-harness'), 'utf8'), 'pi\n');
    const paseoConfig = await json(join(home, '.paseo/config.json'));
    ProviderOverridesSchema.parse(paseoConfig.agents.providers);
    assert.equal(paseoConfig.agents.providers.codex.enabled, true);
    assert.equal(paseoConfig.agents.providers.firstmate.extends, 'pi');
    await write(join(home, '.pi/agent/models.json'), JSON.stringify({ providers: { fixture: { baseUrl: `${origin}/v1`, apiKey: 'fixture', api: 'openai-completions',
      models: ['primary', 'worker'].map(id => ({ id, name: id, reasoning: false, input: ['text'], contextWindow: 128000, maxTokens: 2048,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } })) } } }));
    const fixture = join(directory, 'fixture.mjs');
    await write(fixture, `import {writeFileSync} from 'node:fs'; const original = globalThis.fetch; globalThis.fetch = (url, opts) => original(String(url).startsWith('https://api.github.com/') ? ${JSON.stringify(origin)} + String(url).slice('https://api.github.com'.length) : url, opts); export default function (pi) { pi.on('session_start', () => { if (!process.env.FM_TASK_ID) writeFileSync(${JSON.stringify(join(fleet, 'state/.lock'))}, String(process.pid)); }); }\n`);
    const intakeEnv = { ...env, NODE_OPTIONS: `--import ${fixture}` };
    const queued = JSON.parse(await run(join(ROOT, 'bin/firstmate'), ['github', 'intake', issue], { env: intakeEnv }));
    task = queued.id;
    assert.ok(task, 'GitHub issue queued in the native Firstmate backlog');
    const repeated = JSON.parse(await run(join(ROOT, 'bin/firstmate'), ['github', 'intake', issue], { env: intakeEnv }));
    assert.equal(repeated.id, task, 'Repeated intake preserves task identity');
    await run(join(resolve(source), 'bin/fm-contributions.sh'), ['enroll', task, pr], { env: { ...env, FM_HOME: fleet } });
    await write(join(fleet, 'state', `${task}.meta`), `harness=pi\nkind=ship\nworktree=${worktree}\nproject=${worktree}\nbranch=fix-fee\nspawn_gen=fixture-generation\nbackend=tmux\nwindow=fixture:1\n`);
    await write(join(fleet, 'state', `${task}.status`), 'working: awaiting review\n');
    const launch = async (model, session, task) => {
      const rpc = new PiCliRuntime({ logger, command: task ? [join(modules, '.bin/pi')] : paseoConfig.agents.providers.firstmate.command });
      return rpc.startSession({ cwd: task ? worktree : fleet, model: `fixture/${model}`, session,
        env: { ...env, ...(task ? { FM_TASK_ID: queued.id, FM_TASK_INBOX: join(fleet, 'state', `${queued.id}.inbox`) } : {}) },
        extraArgs: [...(task ? [] : ['--no-extensions']), '--extension', fixture] });
    };
    worker = await launch('worker', undefined, true);
    await worker.prompt('Continue the assigned fee task and wait for GitHub review.');
    await until(async () => (await fs.stat(join(fleet, 'data', task, 'github-session.json')).catch(() => null)), 'Pi owner registered');
    main = await launch('primary'); await main.prompt('Track the assigned fee task; keep this conversation available for steering.');
    await until(async () => requests.some(([, path]) => path.endsWith('/pulls/8')), 'Primary observes tracked GitHub objects');
    await until(async () => !(await worker.getState()).isStreaming, 'Initial worker event settles');
    const primaryState = await main.getState(), workerState = await worker.getState();
    assert.ok(primaryState.sessionFile && workerState.sessionFile);
    await worker.close(); worker = undefined; await main.close(); main = undefined;
    inline.push({ id: 12, body: 'The fee should be added, not subtracted. Please fix this and run the regression.', user: { login: 'lanej' },
      html_url: `${pr}#discussion_r12`, updated_at: '2026-11-02T01:02:00Z', commit_id: originalHead, path: 'price.mjs', line: 1 });
    comments.push({ id: 13, body: 'Keep this scoped to the fee calculation.', user: { login: 'lanej' }, html_url: `${issue}#issuecomment-13`, updated_at: '2026-11-02T01:02:01Z' });
    reviews.push({ id: 14, state: 'CHANGES_REQUESTED', body: '', user: { login: 'lanej' }, html_url: `${pr}#pullrequestreview-14`, submitted_at: '2026-11-02T01:02:00Z', commit_id: originalHead });
    main = await launch('primary', primaryState.sessionFile);
    await until(async () => (await main.getMessages()).some(message => JSON.stringify(message).includes('Firstmate recovery')), 'Unavailable owner escalates');
    worker = await launch('worker', workerState.sessionFile, true);
    await until(() => posted.length === 1, 'Recovered Pi owner revises and replies inline');
    await until(async () => (await fs.readFile(join(fleet, 'state', `${task}.status`), 'utf8')).includes('revised and verified'), 'Outcome reaches Firstmate task record');
    assert.equal((await worker.getState()).sessionId, workerState.sessionId, 'Recovered the recorded worker session');
    assert.equal((await main.getState()).sessionId, primaryState.sessionId, 'Recovered the existing Paseo primary');
    assert.match(execFileSync('node', ['--test'], { cwd: worktree, env: childEnv, encoding: 'utf8' }), /pass 1/);
    assert.match(posted[0].html_url, /discussion_r100/);
    assert.notEqual(remoteHead('fix-fee'), head, 'Worker published the revised task branch');
    assert.equal(remoteHead('main'), head, 'Delivery into the default branch remains unauthorized');
    await until(async () => (await fs.readdir(join(fleet, 'state', `${task}.inbox`))).filter(name => name.endsWith('.msg')).length === 0, 'Feedback acknowledged through native inbox');
    reviews.push({ id: 15, state: 'APPROVED', body: '', user: { login: 'lanej' }, html_url: `${pr}#pullrequestreview-15`, submitted_at: '2026-11-02T01:04:00Z', commit_id: remoteHead('fix-fee') });
    // Allow a full poll after the agent's own GitHub reply: no acknowledgment loop.
    await delay(11000);
    assert.equal(posted.length, 1);
    assert.equal(remoteHead('main'), head, 'Review approval does not authorize merging');
    assert.equal(requests.some(([method]) => !['GET', 'POST'].includes(method)), false, 'No merge API mutation');
    assert.deepEqual(errors, []);
    assert.ok(modelRequests.some(payload => payload.model === 'worker'));
  } finally {
    await worker?.close(); await main?.close();
    try { execFileSync('zellij', ['kill-session', `firstmate-github-${process.pid}`], { env: runtimeEnv, stdio: 'ignore' }); } catch {}
    server.closeAllConnections(); await new Promise(accept => server.close(accept));
    await fs.rm(directory, { recursive: true, force: true });
    if (errors.length) console.error(errors.join('\n'));
    if (testContext !== undefined) process.env.NODE_TEST_CONTEXT = testContext;
  }
});

test('Mobile chat dispatches a native Zellij scout, receives completion, and resumes one captain', { timeout: 120000 }, async () => {
  const runtime = process.env.FIRSTMATE_TEST_RUNTIME, source = resolve(process.env.FIRSTMATE_SOURCE);
  const modules = join(resolve(runtime), 'node_modules');
  const { PiCliRuntime } = await import(pathToFileURL(join(modules, '@getpaseo/server/dist/server/server/agent/providers/pi/cli-runtime.js')));
  const { PiRpcAgentClient } = await import(pathToFileURL(join(modules, '@getpaseo/server/dist/server/server/agent/providers/pi/agent.js')));
  const directory = await fs.mkdtemp('/tmp/firstmate-chat-'), home = join(directory, 'home');
  const fleet = join(directory, 'fleet'), project = join(directory, 'project'), session = `firstmate-chat-${process.pid}`;
  // Keep native panes and Treehouse's nested shell on the fixture-first PATH.
  const env = { ...process.env, HOME: home, SHELL: '/bin/sh', FIRSTMATE_HOME: fleet, FM_HOME: fleet, FM_ROOT_OVERRIDE: fleet,
    FM_ZELLIJ_SESSION: session, FM_POLL: '1', FM_SIGNAL_GRACE: '1', FM_WATCH_EXTENSION_LOG_KEEP_LINES: '100',
    PATH: `${join(home, '.local/bin')}:${join(modules, '.bin')}:${process.env.PATH}`,
    PI_CODING_AGENT_DIR: join(home, '.pi/agent'), PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0' };
  for (const key of ['NODE_TEST_CONTEXT', 'TMUX', 'TMUX_PANE', 'ZELLIJ', 'ZELLIJ_SESSION_NAME', 'ZELLIJ_PANE_ID', 'FM_TASK_ID']) delete env[key];
  const testContext = process.env.NODE_TEST_CONTEXT; delete process.env.NODE_TEST_CONTEXT;
  let captain, server, duplicate, orphanPid, rawCaptain, rpcInput, rpcOutput;
  const failures = [];
  const quote = text => `'${text.replaceAll("'", "'\\''")}'`;
  try {
    await fs.mkdir(home); await fs.mkdir(fleet); await fs.mkdir(project);
    const archive = join(directory, 'fleet.tar');
    execFileSync('git', ['-C', source, 'archive', '--format=tar', `--output=${archive}`, 'HEAD']);
    execFileSync('tar', ['-xf', archive, '-C', fleet]); await fs.unlink(archive);
    await write(join(fleet, 'config/backend'), 'tmux\n');
    await write(join(fleet, 'config/crew-harness'), 'codex\n');
    // WHY: Exercise the native Pi watcher; unrelated branch/turn-end policies have their own detectors.
    for (const name of ['fm-primary-turnend-guard', 'fm-branch-supervision']) {
      await write(join(fleet, '.pi/extensions', `${name}.ts`), 'export default function () {}\n');
    }
    await write(join(fleet, 'data/backlog.md'), '# Backlog\n\n## In flight\n\n## Queued\n\n## Done\n');
    await write(join(project, 'README.md'), 'MOBILE_CHAT_OK\n');
    const workerFixture = join(home, '.local/bin/codex');
    await write(workerFixture, `#!/usr/bin/env python3
import os,sys,time
from pathlib import Path
if '--help' in sys.argv or '--version' in sys.argv:
 print('--approve-for-me --model --config')
 raise SystemExit(0)
state=Path(os.environ['FM_HOME'])/'state'
(state/'chat-smoke.worker-pid').write_text(str(os.getpid()))
status=state/'chat-smoke.status'
status.write_text('working: bounded scout\\n')
while not (state/'chat-smoke.meta').exists(): time.sleep(.1)
time.sleep(5)
token=Path('README.md').read_text().strip()
status.write_text('done: '+token+'\\n')
for line in sys.stdin: pass
`);
    await fs.chmod(workerFixture, 0o700);
    execFileSync('git', ['-C', project, 'init', '-q', '-b', 'main']);
    execFileSync('git', ['-C', project, 'add', '.']);
    execFileSync('git', ['-C', project, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture']);
    execFileSync('make', ['firstmate-mobile-config', `FIRSTMATE_HOME=${fleet}`], { cwd: ROOT, env, stdio: 'pipe' });
    const fixture = join(directory, 'ownership.mjs');
    await write(fixture, `import {writeFileSync} from 'node:fs';export default function(pi){pi.on('session_start',()=>writeFileSync(${JSON.stringify(join(fleet, 'state/.lock'))},String(process.pid)));}\n`);
    let origin, calls = 0;
    server = createServer(async (request, response) => {
      try {
        let body = ''; for await (const chunk of request) body += chunk;
        const payload = JSON.parse(body);
        assert.ok(++calls < 40, 'Mobile model fixture did not converge');
        const text = message => typeof message.content === 'string' ? message.content : (message.content ?? []).filter(item => item.type === 'text').map(item => item.text).join('\n');
        const at = payload.messages.findLastIndex(message => message.role === 'user' &&
          !text(message).includes('This Firstmate home uses GitHub') && !text(message).includes('Use firstmate_peer_list/send/status'));
        const prompt = text(payload.messages[at]), outputs = payload.messages.slice(at + 1).filter(message => message.role === 'tool');
        const call = (name, args) => ({ tool_calls: [{ index: 0, id: `mobile-${calls}`, type: 'function', function: { name, arguments: JSON.stringify(args) } }] });
        let delta = { content: 'Captain ready; waiting for the crew.' };
        if (prompt.includes('Initialize this mobile captain') && !outputs.length) delta = call('fm_watch_arm_pi', {});
        else if (prompt.includes('Show my task board')) {
          if (!outputs.length) delta = call('firstmate_task_board', {});
          else delta = { content: 'Task board refreshed from native records.' };
        }
        else if (prompt.includes('Dispatch the bounded chat-smoke scout') && !outputs.length) {
          const fill = "from pathlib import Path;p=Path('data/chat-smoke/brief.md');p.write_text(p.read_text().replace('{TASK}','Read README and report its token.').replace('{FIRSTMATE_SPEC}','Scout only. No source edits or network.'))";
          delta = call('bash', { command: `bin/fm-tasks-axi.sh add chat-smoke 'Mobile chat scout' --kind scout && bin/fm-brief.sh chat-smoke ${quote(project)} --scout && python3 -c ${quote(fill)} && bin/fm-spawn.sh chat-smoke ${quote(project)} --scout`, timeout: 60 });
        } else if (prompt.includes('wake') || prompt.includes('signal:')) {
          if (!outputs.length) delta = call('bash', { command: 'cat state/chat-smoke.status' });
          else if (outputs.some(item => text(item).includes('done: MOBILE_CHAT_OK'))) delta = { content: 'Scout completed: MOBILE_CHAT_OK' };
        }
        response.writeHead(200, { 'Content-Type': 'text/event-stream' });
        response.end(`data: ${JSON.stringify({ choices: [{ index: 0, delta, finish_reason: null }] })}\n\ndata: ${JSON.stringify({ choices: [{ index: 0, delta: {}, finish_reason: delta.tool_calls ? 'tool_calls' : 'stop' }] })}\n\ndata: [DONE]\n\n`);
      } catch (error) { failures.push(error.stack); response.writeHead(500); response.end(); }
    });
    await new Promise(accept => server.listen(0, '127.0.0.1', accept));
    origin = `http://127.0.0.1:${server.address().port}`;
    await write(join(home, '.pi/agent/models.json'), JSON.stringify({ providers: { fixture: { baseUrl: `${origin}/v1`, apiKey: 'fixture', api: 'openai-completions',
      models: [{ id: 'mobile', name: 'mobile', reasoning: false, input: ['text'], contextWindow: 128000, maxTokens: 2048,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } }] } } }));
    const launch = sessionFile => new PiCliRuntime({ logger, command: [join(ROOT, 'bin/firstmate'), 'rpc'] }).startSession({
      cwd: fleet, env, model: 'fixture/mobile', session: sessionFile, extraArgs: ['--no-extensions', '--extension', fixture],
    });
    captain = await launch();
    await captain.prompt('Initialize this mobile captain');
    await until(async () => !(await captain.getState()).isStreaming, 'native mobile watcher armed');
    const before = await captain.getState();
    const ownerBeforeCatalog = await fs.readFile(join(fleet, 'state/.lock'), 'utf8');
    const sessionFiles = await fs.readdir(resolve(before.sessionFile, '..'));
    const catalogClient = new PiRpcAgentClient({ logger, runtime: new PiCliRuntime({
      logger, command: [join(ROOT, 'bin/firstmate'), 'rpc'], runtimeSettings: { env },
    }) });
    const catalog = await catalogClient.fetchCatalog({ scope: 'workspace', cwd: fleet, force: true });
    assert.ok(catalog.models.some(model => model.id === 'fixture/mobile'), 'The official provider refresh returns authenticated models while a captain runs');
    const injection = await catalogClient.prepareMcpInjection(fleet, { fixture: { type: 'http', url: `${origin}/mcp` } }, env, catalogClient.runtime);
    assert.equal(injection?.kind, 'builtin', 'The official bare-RPC capability probe preserves configured MCP injection');
    assert.equal(injection.servers.fixture.url, `${origin}/mcp`);
    assert.equal(await fs.readFile(join(fleet, 'state/.lock'), 'utf8'), ownerBeforeCatalog, 'Catalog refresh preserves the captain owner');
    assert.deepEqual(await fs.readdir(resolve(before.sessionFile, '..')), sessionFiles, 'Catalog refresh creates no persisted conversation');
    assert.equal((await captain.getState()).sessionId, before.sessionId);
    assert.equal(execFileSync('zellij', ['--session', session, 'action', 'list-clients'], { env, encoding: 'utf8' }).trim().split('\n').length, 2, 'Catalog refresh creates no crew viewport');
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['add', 'tracked-queue', 'Queued tracking example', '--kind', 'scout'], { env });
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['add', 'tracked-blocked', 'Wait for queued task', '--kind', 'scout'], { env });
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['block', 'tracked-blocked', '--by', 'tracked-queue'], { env });
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['add', 'tracked-decision', 'Choose the task scope', '--kind', 'scout'], { env });
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['hold', 'tracked-decision', '--kind', 'captain', '--reason', 'Choose a scope'], { env });
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['add', 'tracked-deferred', 'Wait until the planned date', '--kind', 'scout'], { env });
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['hold', 'tracked-deferred', '--kind', 'captain', '--reason', 'Scheduled later', '--until', '2099-01-01'], { env });
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['add', 'tracked-done', 'Completed tracking example', '--kind', 'scout'], { env });
    await write(join(fleet, 'data/tracked-done/report.md'), 'Tracking example completed.\n');
    await run(join(fleet, 'bin/fm-tasks-axi.sh'), ['done', 'tracked-done', '--report', 'data/tracked-done/report.md'], { env });
    await captain.prompt('Show my task board');
    await until(async () => !(await captain.getState()).isStreaming, 'task board tool finishes');
    const taskBoard = () => captain.getMessages().then(messages => messages.findLast(message => message.role === 'toolResult' && message.toolName === 'firstmate_task_board'));
    const queueBoard = await taskBoard();
    assert.equal(queueBoard.isError, false);
    assert.ok(queueBoard.details.gates.some(row => row.id === 'tracked-queue'));
    assert.ok(queueBoard.details.gates.some(row => row.id === 'tracked-blocked' && row.blocked_by === 'tracked-queue'), 'Unresolved blockers remain visible');
    assert.ok(queueBoard.details.decisions_open.some(row => row.id === 'tracked-decision'), 'A captain hold stays distinct from ordinary queued work');
    assert.ok(queueBoard.details.landed.some(row => row.id === 'tracked-done' && row.artifact === 'data/tracked-done/report.md'), 'Completed canonical records retain their outcome artifact');
    const desktopBoard = JSON.parse(await run(join(ROOT, 'bin/firstmate'), ['tasks', '--json'], { env }));
    assert.deepEqual(desktopBoard.gates, queueBoard.details.gates, 'Desktop and mobile read the same canonical queue');
    const expandedBoard = JSON.parse(await run(join(ROOT, 'bin/firstmate'), ['tasks', '--all', '--json'], { env }));
    assert.equal(expandedBoard.decisions_open.some(row => row.id === 'tracked-deferred'), false, 'An expanded board does not promote a deferred hold into an actionable decision');
    assert.ok(expandedBoard.gates.some(row => row.id === 'tracked-deferred' && row.reason.includes('2099-01-01')), 'The deferred date remains visible in the expanded queue');
    const unavailableSnapshot = { ...expandedBoard, gates: [...expandedBoard.gates,
      { id: 'tracked-blocked', owner: 'remote-cached', title: 'Independent remote task', reason: '-', blocked_by: 'remote-dependency' },
    ], secondmates: [
      { id: 'remote-unavailable', state: 'unknown', freshness: 'unavailable', provenance: 'parent-fallback',
        age_seconds: 120, reason: 'structured home unreadable', doing: '-', contradiction: false },
      { id: 'remote-cached', state: 'working', freshness: 'cached', provenance: 'remote-ledger-cache',
        age_seconds: 900, reason: '-', doing: 'cached task observation', contradiction: true },
    ] };
    const unavailableHome = renderBoard(unavailableSnapshot);
    assert.match(unavailableHome, /remote-unavailable.*unknown.*unavailable.*parent-fallback/);
    assert.match(unavailableHome, /structured home unreadable/);
    assert.match(unavailableHome, /remote-cached.*cached.*remote-ledger-cache/);
    assert.match(unavailableHome, /900 seconds/);
    assert.match(unavailableHome, /Conflicting observations require reconciliation/, 'Rendered output preserves uncertainty even when child rows show work');
    assert.match(unavailableHome, /remote-cached\/tracked-blocked/, 'A secondmate queue row displays its qualified home identity');
    assert.match(unavailableHome, /Blocked by in remote-cached: remote-dependency/, 'Native bounded blocker text retains its owning home');
    assert.deepEqual(localTaskObservations(unavailableSnapshot, 'tracked-blocked').gates.map(row => row.blocked_by), ['tracked-queue'], 'A same-named foreign task cannot contaminate local detail');
    await assert.rejects(run(join(ROOT, 'bin/firstmate'), ['tasks', 'show', 'absent-task'], { env }), /Archived records require the native archive/);
    await assert.rejects(run(join(ROOT, 'bin/firstmate'), ['tasks', 'show', 'other-home/child'], { env }), /Qualified secondmate task IDs belong to that operational home/);
    const requestsBeforeSlash = calls;
    await captain.prompt('/tasks');
    await until(async () => (await captain.getMessages()).some(message => message.role === 'custom' &&
      message.customType === 'firstmate-task-board' && String(message.content).includes('tracked-blocked')), 'slash task board displayed in the persisted conversation');
    assert.equal(calls, requestsBeforeSlash, 'Direct task board needs no model turn');
    duplicate = spawn(join(ROOT, 'bin/firstmate'), ['rpc', '--mode', 'rpc', '--model', 'fixture/mobile', '--extension', fixture], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let refusal = ''; duplicate.stderr.on('data', chunk => { refusal += chunk; });
    const duplicateCode = await new Promise(accept => duplicate.once('exit', accept));
    assert.notEqual(duplicateCode, 0);
    assert.match(refusal, /already running|live captain/);
    await captain.prompt('Dispatch the bounded chat-smoke scout');
    await until(async () => {
      const messages = await captain.getMessages();
      assert.equal(messages.some(message => message.role === 'toolResult' && message.isError), false, 'Native dispatch tools must succeed');
      return messages.some(message => message.role === 'assistant' && JSON.stringify(message).includes('Scout completed: MOBILE_CHAT_OK'));
    }, 'native completion returns to the same chat without another prompt');
    const meta = Object.fromEntries((await fs.readFile(join(fleet, 'state/chat-smoke.meta'), 'utf8')).split('\n').filter(line => line.includes('=')).map(line => {
      const at = line.indexOf('='); return [line.slice(0, at), line.slice(at + 1)];
    }));
    assert.equal(meta.backend, 'zellij'); assert.equal(meta.zellij_session, session);
    assert.equal(meta.harness, 'codex'); assert.notEqual(meta.worktree, project);
    assert.equal(await fs.readFile(join(fleet, 'config/backend'), 'utf8'), 'tmux\n', 'Desktop selection preserved');
    await captain.prompt('Show my task board');
    await until(async () => !(await captain.getState()).isStreaming, 'completed task board finishes');
    const completedBoard = await taskBoard();
    assert.equal(completedBoard.isError, false);
    assert.ok(completedBoard.details.in_flight.some(row => row.id === 'chat-smoke' && row.state === 'unknown'), 'The unverified harness fixture stays unknown despite its historical done event');
    assert.equal(completedBoard.details.landed.some(row => row.id === 'chat-smoke'), false, 'A wake event cannot invent landed work');
    const workerPid = Number(await fs.readFile(join(fleet, 'state/chat-smoke.worker-pid'), 'utf8'));
    const previousPiPid = (await fs.readFile(join(fleet, 'state/.lock'), 'utf8')).trim();
    await captain.close(); captain = await launch(before.sessionFile);
    await until(async () => (await fs.readFile(join(fleet, 'state/.lock'), 'utf8')).trim() !== previousPiPid, 'resumed captain acquires native ownership');
    assert.equal((await captain.getState()).sessionId, before.sessionId, 'Resume retains the original captain conversation');
    assert.doesNotThrow(() => process.kill(workerPid, 0), 'Captain resume retains the existing crew process');
    await captain.prompt('/tasks tracked-blocked');
    await until(async () => (await captain.getMessages()).some(message => message.role === 'custom' &&
      message.customType === 'firstmate-task-board' && message.details?.id === 'tracked-blocked'), 'resumed captain shows full task detail');
    const detail = (await captain.getMessages()).findLast(message => message.role === 'custom' && message.details?.id === 'tracked-blocked');
    assert.match(detail.details.record, /blocked_by: tracked-queue/, 'Reconnect retains the canonical task dependency');
    const piPid = Number((await fs.readFile(join(fleet, 'state/.lock'), 'utf8')).trim());
    const leasePid = Number(execFileSync('ps', ['-o', 'ppid=', '-p', String(piPid)], { encoding: 'utf8' }).trim());
    const wrapperPid = Number(execFileSync('ps', ['-o', 'ppid=', '-p', String(leasePid)], { encoding: 'utf8' }).trim());
    const privateClient = () => execFileSync('ps', ['-axo', 'pid=,ppid=,comm='], { encoding: 'utf8' }).split('\n').map(line => line.trim().split(/\s+/))
      .find(row => Number(row[1]) === wrapperPid && row[2]?.split('/').at(-1) === 'zellij')?.[0];
    const oldClient = privateClient();
    assert.ok(oldClient, 'Captain owns a private crew viewport');
    process.kill(Number(oldClient), 'SIGKILL');
    await until(() => privateClient() && privateClient() !== oldClient, 'lost viewport reattaches to the same crew');
    await until(async () => execFileSync('zellij', ['--session', session, 'action', 'list-clients'], { env, encoding: 'utf8' }).trim().split('\n').length === 2, 'one replacement viewport ready');
    assert.equal((await captain.getState()).sessionId, before.sessionId);
    await run(join(fleet, 'bin/fm-teardown.sh'), ['chat-smoke', '--force'], { env });
    const currentPiPid = (await fs.readFile(join(fleet, 'state/.lock'), 'utf8')).trim();
    await captain.close(); captain = undefined;
    const fifo = join(directory, 'rpc-input');
    execFileSync('mkfifo', [fifo]);
    rpcInput = await fs.open(fifo, 'r+'); rpcOutput = await fs.open(join(directory, 'rpc-output'), 'w');
    // WHY: Caller-owned descriptors keep Pi alive; Paseo normally closes RPC pipes when its launcher exits.
    rawCaptain = spawn(join(ROOT, 'bin/firstmate'), ['rpc', '--mode', 'rpc', '--model', 'fixture/mobile',
      '--session', before.sessionFile, '--no-extensions', '--extension', fixture],
      { env, stdio: [rpcInput.fd, rpcOutput.fd, rpcOutput.fd] });
    await until(async () => (await fs.readFile(join(fleet, 'state/.lock'), 'utf8')).trim() !== currentPiPid, 'raw resumed captain owns native lock');
    // WHY: Challenge wrapper loss in the native preclaim window while the actual Pi demonstrably survives.
    orphanPid = Number((await fs.readFile(join(fleet, 'state/.lock'), 'utf8')).trim());
    await fs.unlink(join(fleet, 'state/.lock'));
    rawCaptain.kill('SIGKILL');
    await new Promise(accept => rawCaptain.once('exit', accept));
    await rpcInput.write(JSON.stringify({ type: 'get_state', id: 'survival-probe' }) + '\n');
    await until(async () => (await fs.readFile(join(directory, 'rpc-output'), 'utf8')).includes('"id":"survival-probe"'),
      'surviving Pi answers RPC after outer wrapper loss');
    await assert.rejects(run(join(ROOT, 'bin/firstmate'), ['rpc', '--version'], { env }), /already running/);
    process.kill(orphanPid, 'SIGKILL'); orphanPid = undefined;
    assert.deepEqual(failures, []);
  } catch (error) {
    console.error(JSON.stringify({ messages: (await captain?.getMessages().catch(() => []) ?? []).slice(-8),
      status: await fs.readFile(join(fleet, 'state/chat-smoke.status'), 'utf8').catch(() => null),
      meta: await fs.readFile(join(fleet, 'state/chat-smoke.meta'), 'utf8').catch(() => null),
      watcher: await fs.readFile(join(fleet, 'state/.watch-extension.log'), 'utf8').catch(() => null),
      arm: await Promise.all((await fs.readdir(join(fleet, 'state')).catch(() => [])).filter(name => name.startsWith('.watch-arm-output'))
        .map(async name => [name, await fs.readFile(join(fleet, 'state', name), 'utf8')])),
      files: await fs.readdir(join(fleet, 'state')).catch(() => []), failures }));
    throw error;
  } finally {
    if (orphanPid) { try { process.kill(orphanPid, 'SIGKILL'); } catch {} }
    await captain?.close();
    if (rawCaptain?.exitCode === null && rawCaptain.signalCode === null) rawCaptain.kill('SIGTERM');
    await rpcInput?.close(); await rpcOutput?.close();
    await run(join(fleet, 'bin/fm-watch-arm.sh'), ['--stop'], { env }).catch(error => console.error(error.message));
    if (await fs.stat(join(fleet, 'state/chat-smoke.meta')).catch(() => null)) {
      await run(join(fleet, 'bin/fm-teardown.sh'), ['chat-smoke', '--force'], { env }).catch(error => console.error(error.message));
    }
    if (duplicate?.exitCode === null) duplicate.kill('SIGKILL');
    try { execFileSync('zellij', ['kill-session', session], { env, stdio: 'ignore' }); } catch {}
    if (server) { server.closeAllConnections(); await new Promise(accept => server.close(accept)); }
    await fs.rm(directory, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    if (testContext !== undefined) process.env.NODE_TEST_CONTEXT = testContext;
  }
});

test('Mobile lease parent allows graceful cleanup and reaps an unresponsive child before releasing its launch lock', { timeout: 30000 }, async () => {
  const directory = await fs.mkdtemp('/tmp/firstmate-lease-');
  try {
    const driver = `import fcntl,os,signal,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[1])
for graceful in (True,False):
 pid_file=root/('graceful.pid' if graceful else 'stubborn.pid')
 lock=open(root/'lease','a'); fcntl.flock(lock,fcntl.LOCK_EX)
 handler="lambda *_:(time.sleep(1),Path("+repr(str(root/'cleaned'))+").write_text('clean'),sys.exit(0))" if graceful else "signal.SIG_IGN"
 child_code="import os,signal,sys,time;from pathlib import Path;signal.signal(signal.SIGTERM,"+handler+");Path("+repr(str(pid_file))+").write_text(str(os.getpid()));time.sleep(60)"
 guardian=subprocess.Popen([sys.executable,sys.argv[2],'--hold-lease',str(lock.fileno()),sys.executable,'-c',child_code],pass_fds=(lock.fileno(),))
 lock.close(); pid=None
 try:
  deadline=time.monotonic()+5
  while not pid_file.exists():
   assert time.monotonic()<deadline, 'Child startup timeout'
   time.sleep(.05)
  pid=int(pid_file.read_text())
  with open(root/'lease','a') as probe:
   try: fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError: pass
   else: raise AssertionError('Lease released while child still lives')
  guardian.terminate(); guardian.wait(timeout=18)
  if graceful: assert (root/'cleaned').read_text()=='clean', 'Child lost its graceful cleanup interval'
  try: os.kill(pid,0)
  except ProcessLookupError: pass
  else: raise AssertionError('Guardian exited without reaping its child')
  with open(root/'lease','a') as probe: fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
 finally:
  if guardian.poll() is None:
   if pid:
    try: os.kill(pid,signal.SIGKILL)
    except ProcessLookupError: pass
   guardian.wait(timeout=5)
`;
    await run('python3', ['-c', driver, directory, join(ROOT, 'firstmate/mobile-rpc.py')]);
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
});
