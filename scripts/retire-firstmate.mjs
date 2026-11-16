import { readFile, writeFile, rename, lstat, readlink, unlink } from 'node:fs/promises';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const home = resolve(process.argv[2] ?? process.env.HOME);
async function edit(file, change) {
  let value;
  try { value = JSON.parse(await readFile(file, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return; throw error; }
  if (!change(value)) return;
  const temporary = file + '.' + randomUUID() + '.tmp';
  await writeFile(temporary, JSON.stringify(value, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
  await rename(temporary, file);
}
await edit(join(home, '.pi/agent/settings.json'), value => {
  if (value.extensions === undefined) return false;
  if (!Array.isArray(value.extensions) || value.extensions.some(item => typeof item !== 'string')) throw new Error('Invalid Pi extensions; preserve and reconcile settings');
  const retired = ['github','peers','tasks'].map(name => join(root, 'pi/extensions/firstmate-' + name + '.mjs'));
  const next = value.extensions.filter(item => !retired.includes(item));
  if (next.length === value.extensions.length) return false;
  value.extensions = next; return true;
});
await edit(join(process.env.PASEO_HOME ?? join(home, '.paseo'), 'config.json'), value => {
  const provider = value.agents?.providers?.firstmate;
  if (!Array.isArray(provider?.command) || provider.command[0] !== join(root, 'bin/firstmate')) return false;
  delete value.agents.providers.firstmate; return true;
});
const launcher = join(home, '.local/bin/firstmate');
try {
  if ((await lstat(launcher)).isSymbolicLink() && await readlink(launcher) === join(root, 'bin/firstmate')) await unlink(launcher);
} catch (error) { if (error.code !== 'ENOENT') throw error; }
