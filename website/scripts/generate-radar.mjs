import { readFile, writeFile, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { parse } from 'yaml';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkStringify from 'remark-stringify';
import { visit } from 'unist-util-visit';
import GithubSlugger from 'github-slugger';

const repo = fileURLToPath(new URL('../../', import.meta.url));
const defaultRegistry = resolve(repo, 'docs/radar.yaml');
const defaultOutput = resolve(repo, 'docs/radar.md');
const iconDirectory = resolve(repo, 'website/public/radar');
const ringDefinitions = [
  { id: 'adopt', name: 'Adopt', meaning: 'In active use; recommended' },
  { id: 'trial', name: 'Trial', meaning: 'Being evaluated; promising enough to run in real workflows' },
  { id: 'assess', name: 'Assess', meaning: 'Worth watching; not yet trialed' },
  { id: 'hold', name: 'Hold', meaning: 'Not adopted; rationale documented' },
];
const markdown = unified().use(remarkParse).use(remarkGfm).use(remarkStringify);
const text = (value) => ({ type: 'text', value });
const heading = (depth, value) => ({ type: 'heading', depth, children: [text(value)] });

function keys(value, allowed, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label}: expected an object`);
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) throw new Error(`${label}: unknown field "${key}"`);
  }
}

function requiredString(value, label) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label}: expected a nonempty string`);
  return value.trim();
}

/** Validate registry records and produce the shared prose and diagram model without I/O. */
export function renderRadar(registry) {
  keys(registry, ['version', 'entries'], 'radar');
  if (registry.version !== 1) throw new Error('radar.version: expected 1');
  if (!Array.isArray(registry.entries)) throw new Error('radar.entries: expected an array');
  const ids = new Set();
  const entries = registry.entries.map((entry, index) => {
    const label = `radar.entries[${index}]`;
    keys(entry, ['id', 'name', 'ring', 'icon', 'rationale'], label);
    const id = requiredString(entry.id, `${label}.id`);
    if (!/^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/.test(id)) throw new Error(`${label}.id: use a lowercase slug`);
    if (ids.has(id)) throw new Error(`${label}.id: duplicate ID "${id}"`);
    ids.add(id);
    const name = requiredString(entry.name, `${label}.name`);
    if (/[\r\n]/.test(name)) throw new Error(`${label}.name: expected one line`);
    if (!ringDefinitions.some((ring) => ring.id === entry.ring)) throw new Error(`${label}.ring: unknown ring "${entry.ring}"`);
    const icon = entry.icon === undefined ? 'tool.svg' : requiredString(entry.icon, `${label}.icon`);
    if (!/^[a-z0-9][a-z0-9-]*\.(?:png|svg)$/.test(icon)) throw new Error(`${label}.icon: expected a local PNG or SVG filename`);
    const rationale = requiredString(entry.rationale, `${label}.rationale`);
    const body = markdown.parse(rationale).children;
    visit({ type: 'root', children: body }, (node) => {
      if (typeof node.identifier === 'string') {
        node.identifier = `${id}--${node.identifier}`;
        node.label = node.identifier;
        if (node.type === 'linkReference' || node.type === 'imageReference') node.referenceType = 'full';
      }
      if (node.type === 'text') node.value = node.value.replace(/\r?\n/g, ' ');
      if (node.type === 'heading' || node.type === 'html') throw new Error(`${label}.rationale: use Markdown without headings or HTML`);
    });
    return { id, name, ring: entry.ring, icon, body };
  });
  const tree = markdown.parse('# Tech Radar\n\nTool and technology decisions, organized by ring.\n');
  tree.children.push({ type: 'table', align: [null, null], children: [
    { type: 'tableRow', children: ['Ring', 'Meaning'].map((value) => ({ type: 'tableCell', children: [text(value)] })) },
    ...ringDefinitions.map((ring) => ({ type: 'tableRow', children: [ring.name, ring.meaning].map((value, index) => ({ type: 'tableCell', children: [index === 0 ? { type: 'strong', children: [text(value)] } : text(value)] })) })),
  ] });
  const slugger = new GithubSlugger();
  const rings = ringDefinitions.map((ring) => {
    tree.children.push({ type: 'thematicBreak' }, heading(2, ring.name));
    slugger.slug(ring.name);
    const grouped = entries.filter((entry) => entry.ring === ring.id).map((entry) => {
      tree.children.push(heading(3, entry.name), ...entry.body);
      return { id: entry.id, name: entry.name, anchor: slugger.slug(entry.name), icon: entry.icon };
    });
    if (!grouped.length) tree.children.push({ type: 'paragraph', children: [{ type: 'emphasis', children: [text('Nothing here yet.')] }] });
    return { name: ring.name, entries: grouped };
  });
  tree.children.splice(1, 0, { type: 'html', value: '<!-- Generated from radar.yaml. Edit the registry, then run: npm --prefix website run radar -->' });
  return { rings, markdown: markdown.stringify(tree) };
}

export async function loadRadar(registryPath = defaultRegistry) {
  const result = renderRadar(parse(await readFile(registryPath, 'utf8')));
  for (const icon of new Set(result.rings.flatMap((ring) => ring.entries.map((entry) => entry.icon)))) {
    try { if (!(await stat(resolve(iconDirectory, icon))).isFile()) throw new Error('Expected a file'); }
    catch { throw new Error(`Radar icon not found: ${icon}`); }
  }
  return result;
}

export async function generateRadar({ registryPath = defaultRegistry, outputPath = defaultOutput, check = false } = {}) {
  const result = await loadRadar(registryPath);
  if (check) {
    let existing;
    try { existing = await readFile(outputPath, 'utf8'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (existing !== result.markdown) throw new Error(`${outputPath} is stale; run npm --prefix website run radar`);
  } else {
    await writeFile(outputPath, result.markdown);
  }
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const { values } = parseArgs({ options: { registry: { type: 'string' }, output: { type: 'string' }, check: { type: 'boolean', default: false } } });
    const result = await generateRadar({ registryPath: values.registry && resolve(values.registry), outputPath: values.output && resolve(values.output), check: values.check });
    console.log(`${values.check ? 'Verified' : 'Generated'} radar: ${result.rings.reduce((total, ring) => total + ring.entries.length, 0)} decisions.`);
  } catch (error) {
    console.error(`radar: ${error.message}`);
    process.exitCode = 1;
  }
}
