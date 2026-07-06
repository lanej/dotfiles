export const meta = {
  name: 'team-leader',
  description: 'Decompose a scenario into 2-6 sub-problems, execute them in parallel, and synthesize a unified result',
  phases: [
    { title: 'Classify', detail: 'assess scenario complexity to pick a model tier for decompose/synthesize', model: 'haiku' },
    { title: 'Decompose', detail: 'break the scenario into bounded, non-overlapping sub-problems' },
    { title: 'Execute', detail: 'run each sub-problem through Explore or general-purpose agents in parallel' },
    { title: 'Apply', detail: 'sequentially apply collected patches when sub-problems share a file' },
    { title: 'Synthesize', detail: 'integrate all sub-problem outputs into one coherent answer' },
  ],
}

const CLASSIFY_SCHEMA = {
  type: 'object',
  properties: {
    complexity: { type: 'string', enum: ['simple', 'complex'] },
    reason: { type: 'string' },
  },
  required: ['complexity', 'reason'],
}

const DECOMPOSE_SCHEMA = {
  type: 'object',
  properties: {
    subproblems: {
      type: 'array',
      minItems: 2,
      maxItems: 6,
      items: {
        type: 'object',
        properties: {
          label: { type: 'string' },
          agentType: { type: 'string', enum: ['Explore', 'general-purpose'] },
          prompt: { type: 'string' },
        },
        required: ['label', 'agentType', 'prompt'],
      },
    },
    sameFileConflict: { type: 'boolean' },
    applyPrompt: { type: ['string', 'null'] },
  },
  required: ['subproblems', 'sameFileConflict', 'applyPrompt'],
}

phase('Classify')

const scenario = args

const classification = await agent(
  `Classify this scenario's complexity for choosing which model tier should run its decomposition and synthesis in a multi-agent workflow.

Mark "complex" if ANY of the following apply: multi-stage coherence needed across 5+ files or components, novel architecture tradeoffs, subtle concurrency or correctness bugs, high cost-of-rework if the decomposition or synthesis is wrong, or complex data modeling. Otherwise mark "simple".

Scenario: ${scenario}`,
  { schema: CLASSIFY_SCHEMA, model: 'haiku', phase: 'Classify' }
)
const tierModel = classification.complexity === 'complex' ? 'opus' : undefined
log(`Complexity: ${classification.complexity} (${classification.reason}) — decompose/synthesize on ${tierModel || 'session default'}`)

phase('Decompose')

const decomposePrompt = `Decompose the following scenario into 2-6 distinct, bounded sub-problems that can be worked independently in parallel.

Scenario: ${scenario}

Rules:
- Each sub-problem must have a clear, bounded scope with no overlap with the others.
- Each sub-problem must produce a concrete, specific output (findings, code, analysis, plan, recommendation).
- Assign agentType "Explore" for read-only research/codebase discovery/investigation, or "general-purpose" for analysis, coding, or writing.
- Each prompt must be fully self-contained: include the overall scenario for context, the specific sub-problem this agent owns, the exact output format expected, and any constraints or relevant background — the sub-agent has no memory of this conversation.
- If two or more sub-problems would need to edit the SAME file, do not spawn parallel write agents against it (they will clobber each other's edits). Instead: set sameFileConflict to true, make those sub-problems read-only "Explore" agents that each return an exact old_string/new_string patch for their piece, and write an applyPrompt describing how to apply all the collected patches to that file sequentially in one pass. Otherwise set sameFileConflict to false and applyPrompt to null.`

const decomposed = await agent(decomposePrompt, { schema: DECOMPOSE_SCHEMA, model: tierModel, phase: 'Decompose' })

log(`Decomposed into ${decomposed.subproblems.length} sub-problems`)

phase('Execute')

const results = await parallel(decomposed.subproblems.map(sp => () =>
  agent(sp.prompt, { label: sp.label, phase: 'Execute', agentType: sp.agentType })
    .then(output => ({ label: sp.label, output }))
))
const findings = results.filter(Boolean)

let applied = null
if (decomposed.sameFileConflict && decomposed.applyPrompt) {
  phase('Apply')
  const patchSummary = findings.map(f => `### ${f.label}\n${f.output}`).join('\n\n')
  applied = await agent(`${decomposed.applyPrompt}\n\nCollected patches:\n\n${patchSummary}`, { phase: 'Apply' })
}

phase('Synthesize')

const findingsText = findings.map(f => `### ${f.label}\n${f.output}`).join('\n\n')
const synthesizePrompt = `Original scenario: ${scenario}

Sub-problem findings:

${findingsText}
${applied ? `\nApply-stage result:\n${applied}\n` : ''}
Synthesize these into one coherent, unified answer. Surface connections and conflicts across sub-problems, draw conclusions that require integrating multiple findings, and flag any gaps or unresolved tensions explicitly. Do not just concatenate the sub-problem outputs.`

const synthesis = await agent(synthesizePrompt, { model: tierModel, phase: 'Synthesize' })

return synthesis
