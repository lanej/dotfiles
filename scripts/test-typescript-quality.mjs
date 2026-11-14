// Real compiler + ESLint regression detector. Only project test/audit commands
// are simulated; they verify forwarding and failure propagation, not scanning.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const source = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const toolInstallation = process.env.TYPESCRIPT_QUALITY_TOOLS;
assert.ok(toolInstallation, 'Set TYPESCRIPT_QUALITY_TOOLS to a directory installed from the profile package.json.');

function execute(root, argv, expected = 0) {
  const result = spawnSync(argv[0], argv.slice(1), { cwd: root, encoding: 'utf8', timeout: 120_000 });
  assert.ifError(result.error);
  const output = `${result.stdout}\n${result.stderr}`;
  if (expected === 0) assert.equal(result.status, 0, output);
  else assert.notEqual(result.status, 0, output);
  return output;
}

function fixture(t, text, rollout = 'strict') {
  const root = mkdtempSync(path.join(os.tmpdir(), 'typescript-quality-'));
  t.after(() => rmSync(root, { force: true, recursive: true }));
  const put = (file, value) => { mkdirSync(path.dirname(path.join(root, file)), { recursive: true }); writeFileSync(path.join(root, file), value); };
  const git = (...args) => execute(root, ['git', ...args]);
  const commit = () => { git('add', '.'); git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'); };
  git('init', '-q');
  put('package.json', JSON.stringify({ private: true, type: 'module', scripts: {
    lint: 'node -e "process.exit(0)"', test: 'node -e "process.exit(0)"',
  } }));
  put('tsconfig.json', JSON.stringify({ compilerOptions: { target: 'ES2022', module: 'NodeNext', strict: false, strictNullChecks: false }, include: ['src'] }));
  put('src/main.ts', text);
  commit();
  execute(root, ['python3', path.join(source, 'bin/source-code'), 'setup', '--repo', root,
    '--skills', 'typescript', '--agents', 'codex', '--pr-template', 'none', '--no-go',
    '--typescript', '--typescript-rollout', rollout]);
  symlinkSync(path.join(toolInstallation, 'node_modules'), path.join(root, '.typescript-quality/node_modules'), 'dir');
  cpSync(path.join(toolInstallation, 'package-lock.json'), path.join(root, '.typescript-quality/package-lock.json'));
  const settingsPath = path.join(root, '.typescript-quality.json');
  const settings = JSON.parse(readFileSync(settingsPath, 'utf8'));
  settings.commands.audit = ['node', '-e', 'process.exit(0)'];
  writeFileSync(settingsPath, JSON.stringify(settings));
  const check = (mode = 'all', expected = 0, ...files) => execute(root, ['node', 'scripts/check-typescript.mjs', mode, ...files], expected);
  return { root, put, git, commit, check, settings, settingsPath };
}

const clean = 'export const value = 1;\n';
const indexDebt = 'export function first(values: string[]) {\n  return values[0].toUpperCase();\n}\n';

test('lifecycle stages change generated gates and preserve inherited gates', (t) => {
  const f = fixture(t, clean);
  const policyPath = path.join(f.root, '.source-code.json');
  const policy = JSON.parse(readFileSync(policyPath, 'utf8'));
  const stage = (value, expected = 0) => {
    writeFileSync(policyPath, JSON.stringify({ ...policy, stage: value }));
    return execute(f.root, ['python3', 'scripts/check-source-code.py', 'typescript'], expected);
  };
  f.settings.commands.test = ['node', '-e', 'process.exit(7)'];
  f.settings.commands.audit = ['node', '-e', 'process.exit(9)'];
  writeFileSync(f.settingsPath, JSON.stringify(f.settings));
  stage('research');
  stage('alpha', 7);
  f.settings.commands.test = ['node', '-e', 'process.exit(0)'];
  writeFileSync(f.settingsPath, JSON.stringify(f.settings));
  stage('alpha');
  stage('beta', 9);
  stage('production', 9);
  f.settings.commands.legacy = [['node', '-e', 'process.exit(5)']];
  writeFileSync(f.settingsPath, JSON.stringify(f.settings));
  stage('research', 5);
});

test('strict mode rejects real unsafe operations and suppression bypasses', (t) => {
  const f = fixture(t, clean);
  f.check();
  const cases = [
    ['export function unsafe(value: any) {\n  return value.name;\n}\n', 'no-explicit-any'],
    ['export function fire(): void {\n  void Promise.resolve(1);\n}\n', 'no-floating-promises'],
    ['export function cast(value: unknown): string {\n  return value as string;\n}\n', 'no-unsafe-type-assertion'],
    ['export function label(value: "a" | "b"): string {\n  switch (value) {\n    case "a":\n      return "a";\n    default:\n      return "other";\n  }\n}\n', 'switch-exhaustiveness-check'],
    ['// eslint-disable-next-line @typescript-eslint/no-explicit-any\nexport function unsafe(value: any) { return value; }\n', 'description'],
    ['// @ts-nocheck\nexport const bad: number = "not a number";\n', 'ts-nocheck'],
    [indexDebt, 'TS2532'],
  ];
  for (const [code, expected] of cases) {
    f.put('src/main.ts', code);
    assert.ok(f.check('all', 1).includes(expected), expected);
  }
});

test('retrofit budgets shrink; new files and untouched consumers have no exemption', (t) => {
  const f = fixture(t, indexDebt, 'ratchet');
  f.put('src/state.ts', 'export type State = "a" | "b";\n');
  f.put('src/consumer.ts', 'import type { State } from "./state.js";\n\nexport function label(state: State): string {\n  switch (state) {\n    case "a":\n      return "a";\n    case "b":\n      return "b";\n    default:\n      throw new Error("Invalid state");\n  }\n}\n');
  f.commit();
  const beforeSource = readFileSync(path.join(f.root, 'src/main.ts'), 'utf8');
  f.check('baseline');
  assert.equal(readFileSync(path.join(f.root, 'src/main.ts'), 'utf8'), beforeSource);
  f.check();
  const baseline = path.join(f.root, '.typescript-quality-baseline.json');
  const original = readFileSync(baseline, 'utf8');
  assert.match(f.check('baseline', 1), /already exists/u);
  f.put('src/main.ts', '// Existing index lookup.\n' + indexDebt);
  f.check(); // Moving a finding does not consume a new allowance.
  f.put('src/new.ts', indexDebt);
  assert.match(f.check('ratchet', 1), /cannot grow/u);
  assert.equal(readFileSync(baseline, 'utf8'), original);
  rmSync(path.join(f.root, 'src/new.ts'));
  f.put('src/state.ts', 'export type State = "a" | "b" | "c";\n');
  assert.match(f.check('lint', 1), /switch-exhaustiveness-check/u);
  f.put('src/state.ts', 'export type State = "a" | "b";\n');
  f.put('src/main.ts', 'export function first(values: string[]) {\n  return values[0]?.toUpperCase();\n}\n');
  f.check('lint'); // Lint-only checks do not prune compiler allowances.
  assert.match(f.check('typecheck', 1), /Resolved allowances/u);
  f.check('ratchet');
  assert.equal(JSON.parse(readFileSync(baseline, 'utf8')).findings.length, 0);
  f.check();
});

test('baseline refuses dirty source, broken original compilation, and uncovered files', (t) => {
  const f = fixture(t, indexDebt, 'ratchet');
  f.put('src/main.ts', '// Dirty source.\n' + indexDebt);
  assert.match(f.check('baseline', 1), /git diff/u);
  f.put('src/main.ts', 'export const bad: number = "not a number";\n');
  f.commit();
  assert.match(f.check('baseline', 1), /TS2322/u);
  f.put('src/main.ts', clean);
  f.put('orphan.ts', clean);
  f.commit();
  assert.match(f.check('baseline', 1), /outside the configured projects/u);
  rmSync(path.join(f.root, 'orphan.ts'));
  f.git('add', '-u');
  f.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'remove orphan');
  f.put('tsconfig.json', '{ invalid json');
  assert.match(f.check('baseline', 1), /TS\d+/u);
});

test('original gates, test and audit failures remain blocking; formatting is scoped', (t) => {
  const f = fixture(t, clean);
  f.settings.commands.legacy = [['node', '-e', 'process.exit(7)']];
  writeFileSync(f.settingsPath, JSON.stringify(f.settings));
  assert.match(f.check('lint', 1), /failed/u);
  f.settings.commands.legacy = [['node', 'scripts/check-typescript.mjs', 'lint']];
  writeFileSync(f.settingsPath, JSON.stringify(f.settings));
  assert.match(f.check('lint', 1), /Recursive quality command/u);
  f.settings.commands.legacy = [];
  f.settings.commands.audit = ['node', '-e', 'process.exit(8)'];
  writeFileSync(f.settingsPath, JSON.stringify(f.settings));
  assert.match(f.check('all', 1), /failed/u);
  assert.match(f.check('audit', 1), /failed/u);
  f.settings.commands.test = ['node', '-e', 'process.exit(9)'];
  writeFileSync(f.settingsPath, JSON.stringify(f.settings));
  assert.match(f.check('test', 1), /failed/u);
  assert.match(f.check('fmt', 1), /explicit TypeScript/u);
  f.put('src/main.ts', 'export const value=1;\n');
  f.put('src/other.ts', 'export const other=2;\n');
  f.check('fmt', 0, 'src/main.ts');
  assert.equal(readFileSync(path.join(f.root, 'src/main.ts'), 'utf8'), clean);
  assert.equal(readFileSync(path.join(f.root, 'src/other.ts'), 'utf8'), 'export const other=2;\n');
});


test('Biome is required and cannot be hidden by a retrofit baseline', (t) => {
  const f = fixture(t, 'export const value = 1;\n', 'ratchet');
  f.commit();
  f.check('baseline');
  f.put('src/main.ts', 'debugger;\nexport const value = 1;\n');
  assert.match(f.check('lint', 1), /noDebugger/);
  f.commit();
  assert.match(f.check('ratchet', 1), /noDebugger/);
});
