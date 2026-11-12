import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import { toHast } from 'mdast-util-to-hast';
import { visit } from 'unist-util-visit';
import { layoutRadar } from '../src/components/radar-layout.mjs';
import { renderRadar, loadRadar } from './generate-radar.mjs';

const registry = () => ({ version: 1, entries: [
  { id: 'terminal', name: 'Terminal & tools', ring: 'trial', icon: 'kitty.png', rationale: 'Try **keyboard** navigation.\n\n```sh\nprintf "hello"\n```' },
  { id: 'old-tool', name: 'Old tool', ring: 'hold', rationale: 'Retired from daily use.' },
] });

test('one registry generates prose, grouped decisions, heading links, and an icon default', () => {
  const result = renderRadar(registry());
  assert.deepEqual(result.rings.map((ring) => [ring.name, ring.entries.length]), [['Adopt', 0], ['Trial', 1], ['Assess', 0], ['Hold', 1]]);
  assert.deepEqual(result.rings[1].entries[0], { id: 'terminal', name: 'Terminal & tools', anchor: 'terminal--tools', icon: 'kitty.png' });
  assert.equal(result.rings[3].entries[0].icon, 'tool.svg');
  assert.match(result.markdown, /### Terminal & tools/);
  assert.match(result.markdown, /Try \*\*keyboard\*\* navigation\./);
  assert.match(result.markdown, /```sh\nprintf "hello"\n```/);
  assert.ok(result.markdown.indexOf('## Hold') < result.markdown.indexOf('### Old tool'));
});

test('invalid decisions are rejected instead of silently producing an incomplete radar', () => {
  const invalid = [
    [data => data.entries.push({ ...data.entries[0] }), /duplicate ID/],
    [data => data.entries[0].ring = 'retired', /unknown ring/],
    [data => data.entries[0].icon = '../private.png', /local PNG or SVG/],
    [data => data.entries[0].rationale = '## Another ring', /without headings or HTML/],
    [data => data.entries[0].rationale = '<script>ignored</script>', /without headings or HTML/],
    [data => data.entries[0].icons = 'typo.svg', /unknown field/],
  ];
  for (const [change, error] of invalid) { const data = registry(); change(data); assert.throws(() => renderRadar(data), error); }
});

test('CLI regenerates after a ring change, checks stale output, and preserves output on invalid input', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'radar-registry-'));
  const input = join(directory, 'radar.yaml');
  const output = join(directory, 'radar.md');
  const script = fileURLToPath(new URL('./generate-radar.mjs', import.meta.url));
  const run = (...args) => spawnSync(process.execPath, [script, '--registry', input, '--output', output, ...args], { encoding: 'utf8' });
  const data = registry();
  try {
    await writeFile(input, JSON.stringify(data));
    assert.equal(run().status, 0);
    assert.equal(run('--check').status, 0);
    const original = await readFile(output, 'utf8');
    data.entries[0].ring = 'assess';
    await writeFile(input, JSON.stringify(data));
    const stale = run('--check');
    assert.equal(stale.status, 1);
    assert.match(stale.stderr, /is stale/);
    assert.equal(await readFile(output, 'utf8'), original);
    assert.equal(run().status, 0);
    const updated = await readFile(output, 'utf8');
    assert.ok(updated.indexOf('## Assess') < updated.indexOf('### Terminal & tools'));
    data.entries[0].icon = 'does-not-exist.svg';
    await writeFile(input, JSON.stringify(data));
    const missing = run();
    assert.equal(missing.status, 1);
    assert.match(missing.stderr, /Radar icon not found: does-not-exist.svg/);
    assert.equal(await readFile(output, 'utf8'), updated);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('the migrated registry retains the accepted decisions and links', async () => {
  const { rings } = await loadRadar();
  assert.deepEqual(rings.map((ring) => ring.entries.map((entry) => entry.id)), [
    ['fzf', 'kitty', 'yabai', 'zellij'], ['mergiraf', 'paseo', 'viewrule'], ['pi', 'aerospace'],
    ['firstmate-through-paseo-and-github', 'superpowers', 'opencode', 'ghostty', 'andrej-karpathy-skills', 'sccache'],
  ]);
  assert.equal(rings[1].entries[2].icon, 'viewrule.png');
  assert.equal(rings[3].entries[0].anchor, 'firstmate-through-paseo-and-github');
});


test('reference links with the same label keep each tool’s destination', () => {
  const data = registry();
  data.entries[0].rationale = '[Docs][docs]\n\n[docs]: https://a.example/';
  data.entries[1].rationale = '[Docs][docs]\n\n[docs]: https://b.example/';
  const result = renderRadar(data);
  const tree = toHast(unified().use(remarkParse).use(remarkGfm).parse(result.markdown));
  const destinations = [];
  visit(tree, 'element', (node) => { if (node.tagName === 'a') destinations.push(node.properties.href); });
  assert.deepEqual(destinations, ['https://a.example/', 'https://b.example/']);
});

test('registry growth expands the layout and keeps icon targets apart', async () => {
  const { rings } = await loadRadar();
  const initialSize = layoutRadar(rings).size;
  rings[0].entries.push({ id: 'third', name: 'Third', anchor: 'third', icon: 'tool.svg' }, { id: 'fourth', name: 'Fourth', anchor: 'fourth', icon: 'tool.svg' });
  const layout = layoutRadar(rings);
  assert.ok(layout.size > initialSize);
  const points = layout.rings.flatMap((ring) => ring.entries);
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 1; j < points.length; j++) {
      assert.ok(Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y) >= 58, `${points[i].name} overlaps ${points[j].name}`);
    }
  }
});
