#!/usr/bin/env node
// One entrypoint locally and in CI. Installation and source rewriting are explicit.
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import {
  existsSync, lstatSync, readFileSync, renameSync, unlinkSync,
  writeFileSync,
} from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tools = path.join(root, '.typescript-quality');
const baselinePath = '.typescript-quality-baseline.json';
const require = createRequire(path.join(tools, 'package.json'));
const [mode = 'all', ...args] = process.argv.slice(2);
const modes = new Set(['all', 'lint', 'typecheck', 'fmt', 'test', 'audit', 'tools', 'baseline', 'ratchet']);
const sourcePattern = /\.(?:ts|tsx|mts|cts)$/u;
const declarationPattern = /\.d\.(?:ts|mts|cts)$/u;
const readJSON = (file) => JSON.parse(readFileSync(file, 'utf8'));
const fail = (message) => { throw new Error(message); };

function run(command, capture = false) {
  if (!Array.isArray(command) || command.length === 0 ||
      command.some((value) => typeof value !== 'string' || value.length === 0)) {
    fail('Each quality command must be a nonempty argv array.');
  }
  const env = { ...process.env, DOTFILES_TYPESCRIPT_QUALITY_ACTIVE: root };
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR']) delete env[key];
  const result = spawnSync(command[0], command.slice(1), {
    cwd: root, env, encoding: 'utf8', stdio: capture ? 'pipe' : 'inherit',
    maxBuffer: 64 * 1024 * 1024,
  });
  if (result.error || result.status !== 0) {
    fail(`${command.join(' ')} failed: ${result.error?.message ?? result.stderr ?? result.status}`);
  }
  return result.stdout ?? '';
}

function safePath(relative, mustExist = true) {
  if (typeof relative !== 'string' || relative === '' || path.isAbsolute(relative) ||
      relative.split(/[\\/]/u).some((part) => part === '..' || part === '.' || part === '')) {
    fail(`Expected a repository-relative path: ${relative}`);
  }
  const absolute = path.resolve(root, relative);
  for (let current = absolute; current !== root; current = path.dirname(current)) {
    if (existsSync(current) || (() => { try { return lstatSync(current).isSymbolicLink(); } catch { return false; } })()) {
      if (lstatSync(current).isSymbolicLink()) fail(`Refusing linked path: ${relative}`);
    }
  }
  if (mustExist && !existsSync(absolute)) fail(`Missing file: ${relative}`);
  return absolute;
}

function relativePath(file) {
  const relative = path.relative(root, path.resolve(file)).split(path.sep).join('/');
  if (relative.startsWith('../') || path.isAbsolute(relative)) fail(`Source outside repository: ${file}`);
  return relative;
}

function policy() {
  const result = readJSON(safePath('.typescript-quality.json'));
  if (result.version !== 1 || !['strict', 'ratchet'].includes(result.rollout) ||
      !Array.isArray(result.projects) || result.projects.length === 0 ||
      new Set(result.projects).size !== result.projects.length || !Array.isArray(result.exclude) ||
      !result.commands || !Array.isArray(result.commands.legacy)) fail('Invalid TypeScript quality policy.');
  for (const project of result.projects) safePath(project);
  for (const exclusion of result.exclude) {
    safePath(exclusion.path, false);
    if (typeof exclusion.reason !== 'string' || exclusion.reason.trim().length < 10) {
      fail('Each excluded source path needs a concrete reason (at least 10 characters).');
    }
  }
  return result;
}

function toolsReady() {
  const manifest = readJSON(path.join(tools, 'package.json'));
  if (!existsSync(path.join(tools, 'package-lock.json'))) fail('Run the tools command, then review and commit .typescript-quality/package-lock.json.');
  const lock = readJSON(safePath('.typescript-quality/package-lock.json'));
  if (lock.lockfileVersion !== 3) fail('Regenerate the quality tool lockfile with npm on Node 22+.');
  for (const [name, version] of Object.entries(manifest.dependencies)) {
    const installed = readJSON(path.join(tools, 'node_modules', name, 'package.json')).version;
    if (installed !== version || lock.packages?.['']?.dependencies?.[name] !== version) {
      fail(`Quality tool ${name} must be ${version}; run the tools command and review the lockfile.`);
    }
  }
}

function excluded(file, settings) {
  return file.split('/').some((part) => ['node_modules', '.git', '.agents', '.typescript-quality'].includes(part)) ||
    settings.exclude.some(({ path: prefix }) => file === prefix || file.startsWith(`${prefix}/`));
}

function inventory(settings) {
  return [...new Set(run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], true)
    .split('\0').filter((file) => sourcePattern.test(file) && !excluded(file, settings)))].sort();
}

function diagnostic(ts, item, tool = 'tsc') {
  if (!item.file || item.start === undefined) fail(ts.flattenDiagnosticMessageText(item.messageText, '\n'));
  const position = item.file.getLineAndCharacterOfPosition(item.start);
  return {
    file: relativePath(item.file.fileName), tool, rule: `TS${item.code}`,
    message: ts.flattenDiagnosticMessageText(item.messageText, '\n'),
    source: item.file.text.split(/\r?\n/u)[position.line]?.trim() ?? '',
    line: position.line + 1,
  };
}

function programs(settings, files, ts) {
  const strict = readJSON(path.join(tools, 'tsconfig.strict.json')).compilerOptions;
  const built = [];
  const findings = [];
  const covered = new Set();
  const fatal = (items) => {
    if (items.length) fail(ts.formatDiagnosticsWithColorAndContext(items, {
      getCurrentDirectory: () => root, getCanonicalFileName: (name) => name,
      getNewLine: () => '\n',
    }));
  };
  for (const project of settings.projects) {
    const configPath = safePath(project);
    const loaded = ts.readConfigFile(configPath, ts.sys.readFile);
    if (loaded.error) fatal([loaded.error]);
    const parsed = ts.parseJsonConfigFileContent(loaded.config, ts.sys, path.dirname(configPath), undefined, configPath);
    fatal(parsed.errors);
    if (parsed.projectReferences?.length) fail(`${project}: list leaf projects; reference builds must remain an independent project gate.`);
    if (parsed.options.noCheck) fail(`${project}: noCheck cannot establish a valid pre-existing compiler gate.`);
    if (parsed.fileNames.length === 0) fail(`${project}: no source files are configured.`);
    const original = ts.createProgram({ rootNames: parsed.fileNames, options: { ...parsed.options, noEmit: true } });
    // A stricter-options retrofit may grandfather additional semantic findings,
    // never an already broken project, parser, module resolution or config.
    fatal(ts.getPreEmitDiagnostics(original));
    const program = ts.createProgram({
      rootNames: parsed.fileNames, options: { ...parsed.options, ...strict }, oldProgram: original,
    });
    fatal([...program.getConfigFileParsingDiagnostics(), ...program.getOptionsDiagnostics(),
      ...program.getGlobalDiagnostics(), ...program.getSyntacticDiagnostics()]);
    const semantic = program.getSemanticDiagnostics();
    fatal(semantic.filter((item) => [2307, 2688, 2792, 6053].includes(item.code)));
    findings.push(...semantic.map((item) => diagnostic(ts, item)));
    for (const source of program.getSourceFiles()) {
      if (program.isSourceFileDefaultLibrary(source) || program.isSourceFileFromExternalLibrary(source)) continue;
      const file = relativePath(source.fileName);
      if (sourcePattern.test(file) && !excluded(file, settings)) {
        safePath(file);
        covered.add(file);
      }
    }
    built.push(program);
  }
  for (const file of files) {
    safePath(file);
    if (!covered.has(file)) fail(`Source is outside the configured projects: ${file}`);
  }
  // Includes ignored source that the compiler actually loads. It must not escape
  // baseline cleanliness checks just because Git ignores its path.
  return { programs: built, findings, files: [...covered].sort() };
}

async function lint(files, built) {
  const targets = files.filter((file) => !declarationPattern.test(file));
  if (!targets.length) return [];
  const { ESLint } = require('eslint');
  const { default: config } = await import(pathToFileURL(path.join(tools, 'eslint.config.mjs')));
  const eslint = new ESLint({ cwd: root, overrideConfigFile: true, overrideConfig: config(root, built),
    ignore: false, fix: false, cache: false });
  const findings = [];
  for (const report of await eslint.lintFiles(targets)) {
    const file = relativePath(report.filePath);
    const lines = readFileSync(report.filePath, 'utf8').split(/\r?\n/u);
    for (const item of report.messages) {
      // Infrastructure and suppression hygiene are never legacy debt allowances.
      if (item.fatal || !item.ruleId || item.ruleId.startsWith('eslint-comments/') ||
          item.ruleId === '@typescript-eslint/ban-ts-comment') {
        fail(`${file}:${item.line ?? 1}: ${item.message}`);
      }
      findings.push({ file, tool: 'eslint', rule: item.ruleId, message: item.message,
        source: lines[(item.line ?? 1) - 1]?.trim() ?? '', line: item.line ?? 1 });
    }
  }
  return findings;
}

async function formatting(files, write = false) {
  const prettier = require('prettier');
  const findings = [];
  for (const file of files) {
    const absolute = safePath(file);
    const text = readFileSync(absolute, 'utf8');
    const options = { ...(await prettier.resolveConfig(absolute, { editorconfig: true })), filepath: absolute };
    if (write) {
      writeFileSync(absolute, await prettier.format(text, options));
    } else if (!await prettier.check(text, options)) {
      findings.push({ file, tool: 'format', rule: 'prettier', message: 'Formatting differs', source: '', line: 1 });
    }
  }
  return findings;
}

function signature({ file, tool, rule, message, source }) {
  return JSON.stringify({ file, tool, rule, message, source });
}

function counts(findings) {
  const result = new Map();
  // Different programs can produce the identical diagnostic at the same site.
  const unique = new Map(findings.map((item) => [JSON.stringify(item), item]));
  for (const item of unique.values()) result.set(signature(item), (result.get(signature(item)) ?? 0) + 1);
  return result;
}

function readBaseline() {
  const document = readJSON(safePath(baselinePath));
  if (document.version !== 1 || !Array.isArray(document.findings)) fail('Invalid TypeScript baseline.');
  const result = new Map();
  for (const item of document.findings) {
    if (!item || !Number.isSafeInteger(item.count) || item.count <= 0 ||
        !['tsc', 'eslint', 'format'].includes(item.tool) ||
        ['file', 'rule', 'message', 'source'].some((key) => typeof item[key] !== 'string')) fail('Invalid baseline entry.');
    safePath(item.file, false);
    const key = signature(item);
    if (result.has(key)) fail('Duplicate baseline signature.');
    result.set(key, item.count);
  }
  return result;
}

function writeBaseline(findings, create = false) {
  const value = JSON.stringify({ version: 1, findings: [...findings].sort(([a], [b]) => a.localeCompare(b))
    .map(([key, count]) => ({ ...JSON.parse(key), count })) }, null, 2) + '\n';
  const target = safePath(baselinePath, false);
  if (create) {
    writeFileSync(target, value, { flag: 'wx' });
  } else {
    const temporary = `${target}.${process.pid}.tmp`;
    try {
      writeFileSync(temporary, value, { flag: 'wx' });
      renameSync(temporary, target);
    } finally {
      if (existsSync(temporary)) unlinkSync(temporary);
    }
  }
}

function cleanBaselineSource(files) {
  run(['git', 'rev-parse', '--verify', 'HEAD'], true);
  const tracked = new Set(run(['git', 'ls-files', '-z'], true).split('\0'));
  for (const file of files) {
    if (!tracked.has(file)) fail(`Baseline requires committed source: ${file}`);
  }
  if (files.length) run(['git', 'diff', '--exit-code', 'HEAD', '--', ...files], true);
}

function enforce(findings, settings) {
  const current = counts(findings);
  for (const finding of findings) {
    console.log(`${finding.file}:${finding.line}: ${finding.rule}: ${finding.message}`);
  }
  if (mode === 'baseline') {
    if (settings.rollout !== 'ratchet') fail('Baseline creation requires rollout=ratchet.');
    writeBaseline(current, true);
    return;
  }
  if (settings.rollout === 'strict') {
    if (mode === 'ratchet') fail('Ratchet requires rollout=ratchet.');
    if (current.size) fail('Strict TypeScript checks failed.');
    return;
  }
  const previous = readBaseline();
  const checkedTools = mode === 'typecheck' ? ['tsc'] : mode === 'lint' ? ['eslint', 'format'] : ['tsc', 'eslint', 'format'];
  for (const [key, count] of current) {
    if (count > (previous.get(key) ?? 0)) fail(`New finding (baseline cannot grow): ${key}`);
  }
  const stale = [...previous].some(([key, count]) =>
    checkedTools.includes(JSON.parse(key).tool) && count > (current.get(key) ?? 0));
  if (mode === 'ratchet') writeBaseline(current);
  else if (stale) fail('Resolved allowances remain: run ratchet and commit the reduction.');
}

async function main() {
  process.chdir(root);
  if (process.env.DOTFILES_TYPESCRIPT_QUALITY_ACTIVE === root) fail('Recursive quality command: preserve the original project gate instead of calling this runner from it.');
  if (!modes.has(mode) || (mode !== 'fmt' && args.length)) fail('Usage: node scripts/check-typescript.mjs [all|lint|typecheck|fmt FILE...|test|audit|tools|baseline|ratchet]');
  if (Number(process.versions.node.split('.')[0]) < 22) fail('TypeScript quality requires Node 22+.');
  if (mode === 'tools') {
    run(['npm', existsSync(path.join(tools, 'package-lock.json')) ? 'ci' : 'install',
      '--prefix', tools, '--ignore-scripts', '--no-audit', '--no-fund']);
    console.log('Review and commit .typescript-quality/package-lock.json with the profile.');
    return;
  }
  const settings = policy();
  if (mode === 'test' || mode === 'audit') { run(settings.commands[mode]); return; }
  toolsReady();
  if (mode === 'fmt') {
    if (!args.length || args.some((file) => !sourcePattern.test(file))) fail('fmt requires explicit TypeScript file paths.');
    for (const file of args) {
      if (excluded(file, settings)) fail(`Refusing to format excluded source: ${file}`);
      safePath(file);
    }
    await formatting(args, true);
    return;
  }
  for (const command of settings.commands.legacy) run(command);
  if (mode === 'baseline' && existsSync(path.join(root, baselinePath))) fail('Baseline already exists; use ratchet.');
  const ts = require('typescript');
  const built = programs(settings, inventory(settings), ts);
  if (mode === 'baseline') cleanBaselineSource(built.files);
  const findings = mode === 'lint' ? [] : built.findings;
  if (mode !== 'typecheck') {
    if (built.files.length) run([process.execPath, require.resolve('@biomejs/biome/bin/biome'), 'lint', '--config-path', path.join(tools, 'biome.json'), '--error-on-warnings', ...built.files]);
    findings.push(...await lint(built.files, built.programs), ...await formatting(built.files));
  }
  enforce(findings, settings);
  if (mode === 'all') {
    run(settings.commands.test);
    run(settings.commands.audit);
  }
  console.log(`TypeScript quality: ${mode} passed (${settings.rollout}).`);
}

main().catch((error) => {
  console.error(`TypeScript quality: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
});
