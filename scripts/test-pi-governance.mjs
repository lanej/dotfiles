import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { makeGovernance } from '../pi/extensions/governance.mjs';

test('legislative proposal → independent judicial review; no approval or deployment tool', async () => {
  const state = await mkdtemp(join(tmpdir(), 'pi-governance-'));
  const configFile = new URL('../pi/governance/budgets.json', import.meta.url);
  const createPi = () => {
    const tools = new Map();
    const events = new Map();
    return { tools, events, registerTool(tool) { tools.set(tool.name, tool); }, on(name, handler) { events.set(name, handler); } };
  };
  try {
    const legislative = createPi();
    const judicial = createPi();
    const executive = createPi();
    for (const [pi, role] of [[legislative, 'legislative'], [judicial, 'judicial'], [executive, 'executive']]) {
      makeGovernance(pi, { role, state, configFile });
    }
    assert(legislative.tools.has('governance_propose'));
    assert(!legislative.tools.has('governance_review'));
    assert(judicial.tools.has('governance_review'));
    assert(!judicial.tools.has('governance_propose'));
    assert(!executive.tools.has('governance_review'));
    assert(!executive.tools.has('governance_propose'));
    const proposed = (await legislative.tools.get('governance_propose').execute('1', {
      title: 'Reduce handoff context loss',
      problem: 'Workers lose accepted outcome context',
      change: 'Persist a concise task outcome artifact',
      validation: 'Replay known lost-handoff cases',
    })).details;
    assert.equal(proposed.state, 'proposed');
    const reviewed = (await judicial.tools.get('governance_review').execute('2', {
      proposalId: proposed.id, verdict: 'pass', evidence: 'Manual review of replay fixtures',
    })).details;
    assert.equal(reviewed.state, 'reviewed');
    assert.equal(reviewed.review.verdict, 'pass');
    await assert.rejects(judicial.tools.get('governance_review').execute('3', {
      proposalId: proposed.id, verdict: 'pass', evidence: 'duplicate',
    }), /already been reviewed/);
    const status = (await executive.tools.get('governance_status').execute()).details;
    assert.equal(status.weeklyBudgetUsd, 50);
    assert.equal(status.sessions.judicial.cadence, 'weekly');
    assert.equal(status.sessions.legislative.cadence, 'monthly');
    assert.equal(status.sessions.legislative.maxOrdinaryAmendments, 1);
    assert.equal(status.sessions.adoption.minObservationDays, 14);
    const prompt = await executive.events.get('before_agent_start')({ systemPrompt: 'Base context' });
    assert.match(prompt.systemPrompt, /Article I — Integrity/);
    assert.match(prompt.systemPrompt, /Do not advance ordinary systemic changes automatically/);
    assert.deepEqual(JSON.parse(await readFile(join(state, 'proposals', proposed.id + '.json'), 'utf8')), reviewed);
    for (const pi of [legislative, judicial, executive]) {
      assert(![...pi.tools.keys()].some(name => /merge|deploy|approve/.test(name)));
    }
  } finally {
    await rm(state, { recursive: true, force: true });
  }
});
