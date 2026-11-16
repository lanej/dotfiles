// Experimental Pi governance steel thread. This is a workflow adapter, NOT a security boundary.
// Run distinct Pi processes with PI_GOVERNANCE_ROLE set to executive, judicial, or legislative.
import { mkdir, readFile, writeFile, readdir, rename } from 'node:fs/promises';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { randomUUID } from 'node:crypto';

const roles = ['executive', 'judicial', 'legislative'];
const schema = (properties, required = []) => ({ type: 'object', properties, required, additionalProperties: false });
const string = description => ({ type: 'string', description });
const reply = value => ({ content: [{ type: 'text', text: JSON.stringify(value) }], details: value });
const root = new URL('../governance/', import.meta.url);

export function makeGovernance(pi, options = {}) {
  const role = options.role ?? process.env.PI_GOVERNANCE_ROLE;
  if (!roles.includes(role)) return;
  const state = options.state ?? join(process.env.XDG_STATE_HOME ?? join(homedir(), '.local/state'), 'pi-governance');
  const configFile = options.configFile ?? new URL('budgets.json', root);
  const readConfig = async () => JSON.parse(await readFile(configFile, 'utf8'));
  const directory = join(state, 'proposals');
  const constitutionFile = options.constitutionFile ?? new URL('constitution.md', root);
  const filename = id => {
    if (!/^[a-f0-9-]{36}$/.test(id)) throw new Error('Invalid proposal ID');
    return join(directory, id + '.json');
  };
  async function readProposal(id) { return JSON.parse(await readFile(filename(id), 'utf8')); }
  async function publish(record) {
    await mkdir(directory, { recursive: true, mode: 0o700 });
    const path = filename(record.id);
    const next = path + '.' + randomUUID() + '.tmp';
    await writeFile(next, JSON.stringify(record, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
    await rename(next, path);
  }
  pi.registerTool({
    name: 'governance_status', label: 'Governance status',
    description: 'Show branch identity, fixed configured budget (not enforced), and proposed amendments.',
    parameters: schema({}),
    async execute() {
      const config = await readConfig();
      await mkdir(directory, { recursive: true, mode: 0o700 });
      const ids = (await readdir(directory)).filter(name => /^[a-f0-9-]{36}\.json$/.test(name));
      const proposals = await Promise.all(ids.map(name => readProposal(name.slice(0, -5))));
      return reply({ role, weeklyBudgetUsd: config.budgetsUsd[role], sessions: config.sessions, enforcement: 'not implemented', scheduling: 'manual', proposals });
    },
  });
  if (role === 'legislative') pi.registerTool({
    name: 'governance_propose', label: 'Propose a system amendment',
    description: 'Record a proposed improvement to the Pi system. Does not implement, approve, or deploy it.',
    parameters: schema({ title: string('Short title'), problem: string('Observed problem'), change: string('Concrete system change'), validation: string('How to establish improvement') }, ['title', 'problem', 'change', 'validation']),
    async execute(_id, params) {
      if (Object.values(params).some(value => typeof value !== 'string' || !value.trim())) throw new Error('All proposal fields are required');
      const proposal = { id: randomUUID(), state: 'proposed', createdAt: new Date().toISOString(), ...params, review: null };
      await publish(proposal);
      return reply(proposal);
    },
  });
  if (role === 'judicial') pi.registerTool({
    name: 'governance_review', label: 'Review a proposed amendment',
    description: 'Record independent findings on a legislative proposal. This does not authorize deployment.',
    parameters: schema({ proposalId: string('UUID of proposal'), verdict: { type: 'string', enum: ['pass', 'fail'] }, evidence: string('Evidence supporting the verdict') }, ['proposalId', 'verdict', 'evidence']),
    async execute(_id, params) {
      if (!params.evidence.trim()) throw new Error('Review requires evidence');
      const proposal = await readProposal(params.proposalId);
      if (proposal.state !== 'proposed') throw new Error('Proposal has already been reviewed');
      const updated = { ...proposal, state: 'reviewed', review: { verdict: params.verdict, evidence: params.evidence, reviewedAt: new Date().toISOString() } };
      await publish(updated);
      return reply(updated);
    },
  });
  pi.on('before_agent_start', async event => {
    const config = await readConfig();
    const constitution = await readFile(constitutionFile, 'utf8');
    const instructions = {
      executive: 'Implement requested changes only in isolated candidate branches. Never deploy or merge a system amendment without explicit human authorization.',
      judicial: 'Independently examine evidence and record a pass/fail review. You do not approve deployment.',
      legislative: 'Identify systematic failures and propose concrete changes using governance_propose. Do not modify the running system.',
    };
    return { systemPrompt: event.systemPrompt + '\n\nPi governance experimental role: ' + role + '. Weekly budget: 
  });
}

export default function governance(pi) { makeGovernance(pi); }
 + config.budgetsUsd[role] + ' (informational only, not enforced). ' + instructions[role] + '\n\nThe constitution follows; it is guidance until enforced by a trusted controller. Do not advance ordinary systemic changes automatically. Judicial docket: ' + config.sessions.judicial.cadence + '; legislative session: ' + config.sessions.legislative.cadence + '; observe changes for at least ' + config.sessions.adoption.minObservationDays + ' days.\n\n' + constitution };
  });
}

export default function governance(pi) { makeGovernance(pi); }
