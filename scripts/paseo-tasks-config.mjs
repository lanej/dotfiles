import { readFile, writeFile, mkdir, rename, rm } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { randomUUID } from 'node:crypto';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
export async function configureQuestions(path) {
  let saved = {};
  try { saved = JSON.parse(await readFile(path, 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (saved.extensions !== undefined && (!Array.isArray(saved.extensions) ||
      saved.extensions.some(value => typeof value !== 'string'))) throw new Error('Preserve and reconcile the existing Pi extension settings');
  saved.extensions ??= [];
  for (const name of ['paseo-questions.mjs', 'paseo-router.mjs']) {
    const extension = join(root, 'pi/extensions', name);
    if (!saved.extensions.includes(extension)) saved.extensions.push(extension);
  }
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = `${path}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporary, JSON.stringify(saved, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
    await rename(temporary, path);
  } finally { await rm(temporary, { force: true }); }
}
export async function configureModels(path) {
  let saved = {};
  try { saved = JSON.parse(await readFile(path, 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const template = JSON.parse(await readFile(join(root, 'pi/paseo-tasks.models.json'), 'utf8'));
  saved.providers ??= {};
  if (typeof saved.providers !== 'object' || Array.isArray(saved.providers)) throw new Error('Preserve and reconcile the existing Pi model registry');
  for (const [name, provider] of Object.entries(template.providers)) {
    if (saved.providers[name] && JSON.stringify(saved.providers[name]) !== JSON.stringify(provider)) {
      throw new Error(`Existing ${name} differs; preserve and reconcile it before configuring task workers`);
    }
    saved.providers[name] = provider;
  }
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = `${path}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporary, JSON.stringify(saved, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
    await rename(temporary, path);
  } finally { await rm(temporary, { force: true }); }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const [path, models] = process.argv.slice(2);
  if (!path || !models) throw new Error('Usage: node scripts/paseo-tasks-config.mjs <Pi settings.json> <Pi models.json>');
  await configureQuestions(path);
  await configureModels(models);
}
