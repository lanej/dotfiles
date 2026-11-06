import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import * as fs from 'node:fs/promises';
import { createServer } from 'node:http';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { run, atomicJSON, readJSON } from '../firstmate/github-feedback.mjs';
import { list, send, status, remote, acknowledge, notificationKey } from '../firstmate/peers.mjs';
import { installPeers } from '../pi/extensions/firstmate-peers.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const delay = ms => new Promise(accept => setTimeout(accept, ms));
async function until(predicate, message) {
  const end = Date.now() + 30000;
  while (Date.now() < end) { if (await predicate()) return; await delay(100); }
  throw new Error(`Timed out: ${message}`);
}
async function write(path, value) { await fs.mkdir(resolve(path, '..'), { recursive: true }); await fs.writeFile(path, value); }

test('Peer requests survive uncertain SSH delivery and reconnect, through a real terminal and authenticated Paseo agent API', { timeout: 120000 }, async () => {
  const runtime = process.env.FIRSTMATE_TEST_RUNTIME;
  assert.ok(runtime, 'Set FIRSTMATE_TEST_RUNTIME to official Paseo 0.15.1 and Pi 1.4.0');
  const directory = await fs.mkdtemp('/tmp/firstmate-peers-');
  const home = join(directory, 'captain'), boatHome = join(directory, 'boat'), fleet = join(home, 'fleet');
  const bin = join(directory, 'bin'), socket = join(directory, 'tmux.sock');
  let daemon, server;
  const channels = [];
  const childEnv = { ...process.env }; delete childEnv.NODE_TEST_CONTEXT;
  const env = { ...childEnv, HOME: home, FIRSTMATE_HOME: fleet, FIRSTMATE_SOURCE: process.env.FIRSTMATE_SOURCE,
    PATH: `${bin}:${join(resolve(runtime), 'node_modules/.bin')}:${process.env.PATH}` };
  const boatEnv = { ...env, HOME: boatHome, PASEO_HOME: join(boatHome, '.paseo'),
    PI_CODING_AGENT_DIR: join(boatHome, '.pi/agent'), TMUX: `${socket},0,0` };
  let logs = '';
  let inventory;
  const originalPath = process.env.PATH;
  let closeBridge, messages = [];
  const calls = [], failures = [];
  try {
    await fs.mkdir(home, { recursive: true }); await fs.mkdir(boatHome, { recursive: true }); await fs.mkdir(bin);
    await fs.mkdir(join(fleet, 'config'), { recursive: true });
    await atomicJSON(join(fleet, 'config/peers.json'), { pollSeconds: 5, boats: { dev: { ssh: 'dev' }, dev2: { ssh: 'dev2' } } });
    for (const [source, name] of [['peer-helper.py', 'helper.py'], ['peer-paseo.mjs', 'paseo.mjs']]) {
      await write(join(boatHome, '.local/share/firstmate-peer', name), await fs.readFile(join(root, 'firstmate', source)));
    }
    // REF: This controlled SSH boundary exercises argv/stdin and lost receipts; live SSH authentication is separate acceptance.
    await write(join(home, '.ssh/config'), 'Host dev dev2\n ProxyJump admindev\nHost admindev\n HostName auth.invalid\n');
    await write(join(bin, 'ssh'), `#!/usr/bin/env python3
import json,os,sys
args=sys.argv[1:]
assert args[:1] == ['-F'] and args[2] == '-T' and args[3] in ['dev','dev2'], args
env=json.loads(${JSON.stringify(JSON.stringify(boatEnv))})
os.execve('/bin/sh',['/bin/sh','-c',args[4]],env)
`);
    await fs.chmod(join(bin, 'ssh'), 0o700);
    process.env.PATH = env.PATH;
    const terminalAgent = join(directory, 'terminal/pi');
    const source = join(directory, 'terminal/fixture.c');
    await write(source, `#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
int main(int argc, char **argv) {
  puts("Working (esc to interrupt)"); fflush(stdout);
  while (access(${JSON.stringify(join(directory, 'idle'))}, F_OK)) usleep(50000);
  if (strstr(argv[0], "codex")) {
    fputs("\\033[2J\\033[H› \\033[2mAsk Codex to do anything\\033[0m\\n\\n  GPT fixture · project", stdout);
    fputs(argc > 1 ? " · Main [default] · ← for agents\\033[1;5H" : "\\n  ← for agents · ? for shortcuts\\033[1;5H", stdout); fflush(stdout);
    while (access(${JSON.stringify(join(directory, 'codex-ready'))}, F_OK)) usleep(50000);
    fputs("\\033[1;3H", stdout); fflush(stdout);
  } else { puts("\\033[2J\\033[H>"); fflush(stdout); }
  char line[70000], id[81], command[300];
  while (fgets(line, sizeof(line), stdin)) {
    char *start = strstr(line, "Firstmate peer request ");
    if (!start || sscanf(start, "Firstmate peer request %80[a-zA-Z0-9_.-]", id) != 1) continue;
    snprintf(command, sizeof(command), "python3 \\"$HOME/.local/share/firstmate-peer/helper.py\\" reply %s", id);
    FILE *pipe = popen(command, "w");
    if (!pipe) return 2;
    fputs(strstr(argv[0], "codex") ? (argc > 1 ? "Compact Codex peer answered" : "Codex peer answered") : "Terminal peer answered", pipe);
    if (pclose(pipe)) return 3;
  }
  return 0;
}
`);
    execFileSync('cc', [source, '-o', terminalAgent]);
    execFileSync('tmux', ['-S', socket, 'new-session', '-d', '-s', 'peer', terminalAgent], { env: boatEnv });
    execFileSync('tmux', ['-S', socket, 'new-window', '-d', '-t', 'peer', '-n', 'background-agent', 'bash', '-c', `${terminalAgent} & printf '>\\n'; exec bash`], { env: boatEnv });
    const nativeCodex = join(directory, 'terminal/codex'), nodeLauncher = join(directory, 'terminal/@openai/codex/bin/codex.js');
    await fs.copyFile(terminalAgent, nativeCodex); await fs.chmod(nativeCodex, 0o700);
    await write(nodeLauncher, `const {spawn}=require('node:child_process');const child=spawn(${JSON.stringify(nativeCodex)},[],{stdio:'inherit'});child.on('exit',code=>process.exit(code??1));\n`);
    const nodeLink = join(directory, 'terminal/npm-bin/codex');
    await fs.mkdir(resolve(nodeLink, '..')); await fs.symlink(nodeLauncher, nodeLink);
    execFileSync('tmux', ['-S', socket, 'new-window', '-d', '-t', 'peer', '-n', 'node-launcher', 'node', nodeLink], { env: boatEnv });
    execFileSync('tmux', ['-S', socket, 'new-window', '-d', '-t', 'peer', '-n', 'compact-codex', nativeCodex, '--compact'], { env: boatEnv });
    server = createServer(async (request, response) => {
      let body = ''; for await (const chunk of request) body += chunk;
      try {
        const payload = JSON.parse(body);
        const prompts = payload.messages.filter(message => message.role === 'user').map(message => typeof message.content === 'string' ? message.content : message.content.filter(item => item.type === 'text').map(item => item.text).join(''));
        const id = /Firstmate peer request ([A-Za-z0-9_.-]+)/.exec(prompts.at(-1) ?? '')?.[1];
        if (prompts.at(-1) === 'Keep doing independent work') {
          response.writeHead(200, { 'Content-Type': 'text/event-stream' });
          response.write(`data: ${JSON.stringify({ choices: [{ index: 0, delta: { content: 'Independent work continues' }, finish_reason: null }] })}\n\n`);
          return;
        }
        const text = id ? `FIRSTMATE_PEER_REPLY ${id}\nPaseo peer answered\nFIRSTMATE_PEER_REPLY_END ${id}` : 'Peer ready';
        response.writeHead(200, { 'Content-Type': 'text/event-stream' });
        response.end(`data: ${JSON.stringify({ id: 'fixture', object: 'chat.completion.chunk', choices: [{ index: 0, delta: { content: text }, finish_reason: null }] })}\n\ndata: ${JSON.stringify({ choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] })}\n\ndata: [DONE]\n\n`);
      } catch (error) { failures.push(error.stack); response.writeHead(500); response.end(); }
    });
    await new Promise(accept => server.listen(0, '127.0.0.1', accept));
    await atomicJSON(join(boatHome, '.pi/agent/models.json'), { providers: { fixture: {
      baseUrl: `http://127.0.0.1:${server.address().port}/v1`, apiKey: 'fixture', api: 'openai-completions',
      models: [{ id: 'peer', name: 'peer', reasoning: false, input: ['text'], contextWindow: 128000, maxTokens: 2048, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } }],
    } } });
    await atomicJSON(join(boatHome, '.paseo/config.json'), { agents: { providers: { pi: { enabled: true, command: [join(resolve(runtime), 'node_modules/.bin/pi'), '--no-extensions'] } } } });
    daemon = spawn(join(resolve(runtime), 'node_modules/.bin/paseo'), ['daemon', 'run', '--home', boatEnv.PASEO_HOME],
      { env: { ...boatEnv, PASEO_LISTEN: `unix://${join(directory, 'paseo.sock')}`, PASEO_RELAY_ENABLED: 'false' }, stdio: ['ignore', 'pipe', 'pipe'] });
    daemon.stdout.on('data', chunk => { logs += chunk; }); daemon.stderr.on('data', chunk => { logs += chunk; });
    await until(() => fs.stat(join(directory, 'paseo.sock')).catch(() => false), 'isolated Paseo daemon');
    const created = JSON.parse(await run('paseo', ['run', '--provider', 'pi/fixture/peer', '--cwd', boatHome, '--no-wait', '--json', 'Be ready for a fixture peer message'], { env: boatEnv }));
    const agentId = created.agentId;
    assert.ok(agentId, JSON.stringify(created));
    for (const name of ['dev', 'dev2']) {
      const channel = spawn('python3', [join(root, 'firstmate/peer-channel.py'), fleet, name, name], { env, stdio: ['ignore', 'pipe', 'pipe'] });
      channel.stderr.on('data', chunk => { logs += chunk; });
      channels.push(channel);
      await until(() => fs.stat(join(fleet, 'state/peers/channels', `${name}.sock`)).catch(() => false), 'persistent SSH channel');
      const config = join(fleet, 'state/peers/channels', `${name}.ssh-config`);
      for (const host of [name, 'admindev']) {
        const resolved = execFileSync('/usr/bin/ssh', ['-G', '-F', config, host], { encoding: 'utf8', env, stdio: ['ignore', 'pipe', 'ignore'] });
        assert.match(resolved, /controlmaster false/);
        assert.doesNotMatch(resolved, /^controlpath (?!none)/m);
        assert.match(resolved, /connectionattempts 1/);
      }
    }
    const transport = async (boat, payload) => {
      calls.push({ boat: boat.ssh, payload });
      return remote(boat, payload);
    };
    await until(async () => {
      inventory = await list(fleet, transport);
      return inventory[0].peers.some(peer => peer.supported && peer.address.includes('/tmux:'))
        && inventory[1].peers.some(peer => peer.address === `dev2/paseo:${agentId}`);
    }, 'both terminal and Paseo peers discovered');
    const terminal = inventory[0].peers.find(peer => peer.supported && peer.harness === 'pi' && peer.endpoint.startsWith('tmux:'));
    const codex = inventory[0].peers.find(peer => peer.supported && peer.harness === 'codex' && peer.identity.launcherPid !== null);
    assert.ok(codex, 'Recognized npm symlink launcher delegates foreground input to its native Codex child');
    const compact = inventory[0].peers.find(peer => peer.supported && peer.harness === 'codex' && peer.identity.launcherPid === null);
    assert.ok(compact);
    assert.ok(inventory[0].peers.find(peer => peer.endpoint.startsWith('tmux:') && !peer.supported), `Background harness does not authorize foreground shell input: ${JSON.stringify(inventory)}`);
    await assert.rejects(send(fleet, terminal.address, '\x1b[201~dangerous', 'unsafe-terminal', transport), /control characters/);
    const queued = await send(fleet, terminal.address, 'Please confirm receipt', 'terminal-question', transport);
    assert.equal(queued.state, 'queued', 'Busy peer is queued without interrupting its task');
    assert.equal((await send(fleet, codex.address, 'Please confirm receipt', 'codex-question', transport)).state, 'queued');
    assert.equal((await send(fleet, compact.address, 'Please confirm receipt', 'compact-question', transport)).state, 'queued');
    const lost = async (boat, payload) => {
      const accepted = await transport(boat, payload);
      if (payload.action === 'send') throw new Error('SSH receipt lost');
      return accepted;
    };
    const paseo = await send(fleet, `dev2/paseo:${agentId}`, 'Please confirm receipt', 'paseo-question', lost);
    assert.equal(paseo.state, 'unknown', `Lost receipt preserves uncertainty locally: ${JSON.stringify(paseo)}`);
    await until(async () => JSON.parse(await run('paseo', ['agent', 'inspect', agentId, '--json'], { env: boatEnv })).Status === 'idle', 'peer answer completes');
    await run('paseo', ['send', agentId, '--no-wait', 'Keep doing independent work'], { env: boatEnv });
    await until(async () => JSON.parse(await run('paseo', ['agent', 'inspect', agentId, '--json'], { env: boatEnv })).Status === 'running', 'peer continues an independent turn');
    assert.equal((await status(fleet, 'paseo-question', transport))[0].state, 'replied', 'A completed reply remains deliverable during later independent peer work');
    await fs.writeFile(join(directory, 'idle'), '');
    await delay(200);
    for (let poll = 0; poll < 2; poll++) {
      assert.equal((await status(fleet, 'codex-question', transport))[0].state, 'queued', 'Placeholder with a displaced input cursor is not an empty composer');
      assert.equal((await status(fleet, 'compact-question', transport))[0].state, 'queued');
    }
    await fs.writeFile(join(directory, 'codex-ready'), '');
    const events = {};
    const pi = { registerTool() {}, on(name, handler) { events[name] = handler; }, sendMessage(message, options) { messages.push({ message, options }); } };
    installPeers(pi, { home: fleet, intervalMs: 100, owns: async () => true, transport });
    closeBridge = () => events.session_shutdown();
    await events.session_start({}, { cwd: fleet });
    await until(() => messages.some(item => item.message.content.includes('Paseo peer answered'))
      && messages.some(item => item.message.content.includes('Terminal peer answered'))
      && messages.some(item => item.message.content.includes('Codex peer answered'))
      && messages.some(item => item.message.content.includes('Compact Codex peer answered')), 'replies surface in the same captain chat without prompting');
    assert.ok(messages.every(item => item.options.triggerTurn && item.options.deliverAs === 'followUp'));
    closeBridge();
    await events.session_start({}, { cwd: fleet });
    await until(() => messages.filter(item => item.message.content.includes('Terminal peer answered')).length === 2, 'resume retains peer reply evidence');
    const settled = await status(fleet, undefined, transport);
    assert.deepEqual(settled.map(record => record.state).sort(), ['replied', 'replied', 'replied', 'replied']);
    for (const record of settled) await acknowledge(fleet, record.id, notificationKey(record));
    closeBridge();
    const count = messages.length;
    await events.session_start({}, { cwd: fleet });
    await delay(1000);
    assert.equal(messages.length, count, 'Acknowledged historical results do not trigger another turn after reconnect');
    assert.equal(calls.filter(call => call.payload.action === 'send' && call.payload.id === 'paseo-question').length, 1, 'Unknown submission reconciles rather than resending');
    await assert.rejects(send(fleet, terminal.address, 'Different intent', 'terminal-question', transport), /different intent/);
    const changed = await send(fleet, terminal.address, 'Another question', 'changed-terminal', transport);
    assert.equal(changed.state, 'queued');
    execFileSync('tmux', ['-S', socket, 'kill-session', '-t', 'peer']);
    const gone = (await status(fleet, 'changed-terminal', transport))[0];
    assert.equal(gone.state, 'failed', 'Changed terminal cannot receive a queued request');
    assert.deepEqual(failures, []);
  } catch (error) {
    const files = await fs.readdir(join(fleet, 'state/peers/requests')).catch(() => []);
    const records = await Promise.all(files.filter(name => name.endsWith('.json')).map(async name => {
      const record = await readJSON(join(fleet, 'state/peers/requests', name), null);
      return { id: record.id, state: record.state, error: record.error, reply: record.reply };
    }));
    console.error(JSON.stringify({ records, notifications: messages.map(item => item.message.content) }));
    error.message += `\nPaseo fixture log:\n${logs.slice(-1500)}`;
    throw error;
  } finally {
    closeBridge?.();
    for (const channel of channels) {
      channel.kill('SIGTERM');
      await new Promise(accept => channel.once('close', accept));
    }
    process.env.PATH = originalPath;
    try { execFileSync('tmux', ['-S', socket, 'kill-server'], { stdio: 'ignore' }); } catch {}
    if (daemon && daemon.exitCode === null) {
      daemon.kill('SIGTERM');
      await Promise.race([new Promise(accept => daemon.once('close', accept)), delay(5000)]);
      if (daemon.exitCode === null) { daemon.kill('SIGKILL'); await new Promise(accept => daemon.once('close', accept)); }
    }
    if (server) { server.closeAllConnections(); await new Promise(accept => server.close(accept)); }
    await fs.rm(directory, { recursive: true, force: true });
  }
});
