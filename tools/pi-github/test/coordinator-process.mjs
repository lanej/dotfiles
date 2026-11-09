import { Coordinator } from '../dist/coordinator.js';
const coordinator = new Coordinator(process.argv[2], { workerPath: new URL('./fake-worker.mjs', import.meta.url).pathname, workerEnv: { PG_TEST_MODE: process.argv[3] ?? 'hang' } });
const save = coordinator.store.save.bind(coordinator.store);
coordinator.store.save = (job, kind, detail) => {
  if (kind === 'worker_started' && process.argv[3] === 'crash-before-pid') process.kill(process.pid, 'SIGKILL');
  save(job, kind, detail);
  if (kind === 'worker_started' && process.argv[3] === 'crash-after-pid') process.kill(process.pid, 'SIGKILL');
};
await coordinator.start();
console.log('ready');
process.on('SIGTERM', () => { void coordinator.close().then(() => process.exit(0)); });
