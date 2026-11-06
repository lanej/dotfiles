import * as fs from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

// WHY: Reuse the installed official CLI's authenticated client and home selection.
let client;
try {
  const executable = execFileSync('which', ['paseo'], { encoding: 'utf8' }).trim();
  const root = dirname(dirname(await fs.realpath(executable)));
  const { connectToDaemon } = await import(pathToFileURL(join(root, 'dist/utils/client.js')));
  let body = '';
  for await (const chunk of process.stdin) body += chunk;
  const input = JSON.parse(body);
  const { selectDaemonTarget } = await import(pathToFileURL(join(root, 'dist/utils/daemon-target.js')));
  client = await connectToDaemon({ target: selectDaemonTarget({}) });
  if (input.action === 'list') {
    const agents = [];
    let cursor;
    for (let page = 0; page < 100; page++) {
      const payload = await client.fetchAgents({ filter: { includeArchived: false }, page: { limit: 100, cursor } });
      agents.push(...payload.entries);
      if (!payload.pageInfo.hasMore) break;
      cursor = payload.pageInfo.nextCursor;
      if (!cursor || page === 99) throw new Error('Paseo agent inventory bound reached');
    }
    console.log(JSON.stringify(agents.map(({ agent }) => ({
      endpoint: `paseo:${agent.id}`, identity: { id: agent.id, provider: agent.provider, cwd: agent.cwd, createdAt: agent.createdAt },
      title: agent.title, harness: agent.provider, busy: agent.status === 'running', supported: true,
    }))));
  } else {
    const found = await client.fetchAgent({ agentId: input.identity.id });
    const agent = found?.agent;
    if (!agent || agent.id !== input.identity.id || agent.provider !== input.identity.provider ||
        agent.cwd !== input.identity.cwd || agent.createdAt !== input.identity.createdAt || agent.archivedAt) {
      throw new Error('Paseo peer identity changed or is unavailable');
    }
    const rows = [];
    let cursor;
    for (let page = 0; page < 100; page++) {
      const timeline = await client.fetchAgentTimeline(agent.id, { direction: cursor ? 'before' : 'tail', cursor, limit: 100, projection: 'projected' });
      if (timeline.error) throw new Error(timeline.error);
      rows.unshift(...timeline.entries);
      if (timeline.gap || timeline.staleCursor || timeline.reset) throw new Error('Paseo history changed; submission remains uncertain');
      if (!timeline.hasOlder) break;
      cursor = timeline.startCursor;
      if (!cursor || page === 99) throw new Error('Paseo history bound reached; submission remains uncertain');
    }
    const request = rows.findIndex(row => row.item.type === 'user_message' && row.item.text === input.prompt);
    const marker = `FIRSTMATE_PEER_REPLY ${input.id}\n`;
    const endMarker = `\nFIRSTMATE_PEER_REPLY_END ${input.id}`;
    const response = request < 0 ? undefined : rows.slice(request + 1).find(row =>
      row.item.type === 'assistant_message' && row.item.text.startsWith(marker) &&
      row.item.text.includes(endMarker, marker.length));
    const reply = response?.item.text.slice(marker.length, response.item.text.indexOf(endMarker, marker.length));
    // WHY: A complete persisted answer remains deliverable during a later independent turn.
    if (reply?.trim()) console.log(JSON.stringify({ state: 'replied', reply }));
    else if (request >= 0) console.log(JSON.stringify({ state: 'submitted' }));
    else if (input.action === 'submit') {
      if (agent.status !== 'idle' || agent.pendingPermissions.length) console.log(JSON.stringify({ state: 'queued' }));
      else {
        await client.sendAgentMessage(agent.id, input.prompt, { activeTurnBehavior: 'steer' });
        console.log(JSON.stringify({ state: 'submitted' }));
      }
    } else console.log(JSON.stringify({ state: 'unknown' }));
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally { await client?.close(); }
