#!/usr/bin/env bun
import { createHash } from 'node:crypto';
import { cpSync, existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, readlinkSync, renameSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = fileURLToPath(new URL('../', import.meta.url));
const prefix = resolve(process.env.PI_DRIVER_PREFIX ?? join(homedir(), '.local'));
const store = join(prefix, 'share/pi-driver');
const launcher = join(prefix, 'bin/pi-driver');
const version = readFileSync(join(root, '.bun-version'), 'utf8').trim();
const action = process.argv[2];
function run(argv, cwd = root, capture = false) {
  const result = spawnSync(argv[0], argv.slice(1), { cwd, encoding: 'utf8', stdio: capture ? 'pipe' : ['inherit', 'inherit', 'inherit'] });
  if (result.error || result.status !== 0) throw new Error(`${argv[0]} failed: ${result.error?.message ?? result.stderr ?? result.status}`);
  return result.stdout?.trim() ?? '';
}
// Source identity includes local edits and portable resources, never installed dependencies.
function files() {
  return JSON.parse(run(['python3', join(root, 'scripts/source_files.py')], root, true));
}
function installedFiles(directory, relative = '') {
  return readdirSync(directory, { withFileTypes: true }).sort((a,b) => a.name.localeCompare(b.name)).flatMap(entry => {
    if (entry.name === 'installation.json' && relative === '') return [];
    const name = join(relative, entry.name);
    return entry.isDirectory() ? installedFiles(join(directory, entry.name), name) : [name];
  });
}
function digest(directory, names) {
  const hash = createHash('sha256');
  for (const name of names) {
    const file = join(directory, name);
    const info = lstatSync(file);
    hash.update(name).update('\0').update(String(info.mode & 0o777)).update(info.isSymbolicLink() ? 'link' : 'file').update('\0').update(info.isSymbolicLink() ? readlinkSync(file) : readFileSync(file)).update('\0');
  }
  return hash.digest('hex');
}
function status() {
  let record = null;
  try {
    const release = dirname(dirname(readlinkSync(launcher)));
    const value = JSON.parse(readFileSync(join(release, 'installation.json'), 'utf8'));
    if (value.platform === process.platform && value.arch === process.arch && value.sha256 === digest(release, value.files)) record = value;
  } catch { /* A replaced or missing installation has unknown identity. */ }
  return { installed_binary: existsSync(launcher) ? launcher : null, installed_revision: record?.revision ?? null,
    installed_fingerprint: record?.fingerprint ?? null, running_revision: null,
    activation: 'Reload or relaunch Pi to load the installed extension; existing sessions remain active.' };
}
try {
  if (action === 'status') { console.log(JSON.stringify(status())); process.exit(0); }
  if (!['build', 'restart'].includes(action)) throw new Error('Usage: bun scripts/lifecycle.mjs build|restart|status');
  if (process.versions.bun !== version) throw new Error(`Use Bun ${version}, found ${process.versions.bun}`);
  const names = files();
  const fingerprint = digest(root, names);
  if (action === 'restart') {
    if (status().installed_fingerprint !== fingerprint) throw new Error('Build and install this source before activation.');
    console.error(status().activation);
    process.exit(3);
  }
  if (existsSync(launcher) && !lstatSync(launcher).isSymbolicLink()) throw new Error(`Preserving local executable: ${launcher}`);
  mkdirSync(store, { recursive: true });
  const lock = join(store, 'install.lock');
  mkdirSync(lock); // Fail visibly rather than race another installation.
  let stage;
  try {
    const releases = join(store, 'releases');
    mkdirSync(releases, { recursive: true });
    const destination = join(releases, `${fingerprint}-${process.platform}-${process.arch}`);
    stage = join(releases, `.stage-${process.pid}`);
    mkdirSync(stage);
    for (const name of names) {
      mkdirSync(dirname(join(stage, name)), { recursive: true });
      cpSync(join(root, name), join(stage, name));
    }
    writeFileSync(join(stage, "source-files.json"), JSON.stringify([...new Set([...names, "source-files.json"])].sort()) + "\n");
    // Pin the host runtime alongside the extension so PATH cannot select Node or a different Bun.
    mkdirSync(join(stage, 'runtime'));
    cpSync(process.execPath, join(stage, 'runtime/bun'));
    const bun = join(stage, 'runtime/bun');
    run([bun, 'install', '--frozen-lockfile', '--ignore-scripts'], stage);
    run([bun, 'scripts/prepare-delegation.mjs'], stage);
    run([bun, 'scripts/build-aot.mjs'], stage);
    let revision = null;
    try {
      if (run(['git', 'status', '--porcelain', '--untracked-files=all', '--', '.'], root, true) === '')
        revision = run(['git', 'rev-parse', 'HEAD'], root, true);
    } catch { /* A source export can be installed before its first commit. */ }
    const manifest = installedFiles(stage);
    const installed = { revision, fingerprint, platform: process.platform, arch: process.arch, files: manifest, sha256: digest(stage, manifest) };
    writeFileSync(join(stage, 'installation.json'), JSON.stringify(installed) + '\n');
    if (existsSync(destination)) {
      const previous = JSON.parse(readFileSync(join(destination, 'installation.json'), 'utf8'));
      if (previous.sha256 !== digest(destination, previous.files)) throw new Error('Existing release was modified; preserving it.');
      rmSync(stage, { recursive: true });
    } else renameSync(stage, destination);
    stage = undefined;
    run(['python3', join(destination, 'scripts/configure.py'), destination]);
    mkdirSync(dirname(launcher), { recursive: true });
    const link = `${launcher}.stage-${process.pid}`;
    try {
      symlinkSync(join(destination, 'scripts/pi-driver'), link);
      renameSync(link, launcher);
    } finally { rmSync(link, { force: true }); }
    console.error(`Installed pi-driver at ${launcher}. Reload or relaunch Pi when ready.`);
  } finally {
    if (stage !== undefined) rmSync(stage, { recursive: true, force: true });
    rmSync(lock, { recursive: true });
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
