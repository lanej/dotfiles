// Adapted from Smart Plan src/plan-validate.ts at 3e51e33acd63a7743391e21598042438746aafa0.
// Copyright (c) 2026 Jacopo Nardiello. See LICENSE.smart-plan.
interface GraphTask {
  key: string;
  blockedBy: string[];
  owns: string[];
}

function ownsOverlap(a: string, b: string): boolean {
  return a === b || a.startsWith(`${b}/`) || b.startsWith(`${a}/`);
}

/** Assign each task to one plus the longest prerequisite chain. */
export function taskWaves(tasks: GraphTask[]): Map<string, number> {
  const byKey = new Map(tasks.map((task) => [task.key, task]));
  const layers = new Map<string, number>();
  const visiting = new Set<string>();
  if (byKey.size !== tasks.length) throw new Error("Task keys must be unique");

  function layerOf(key: string): number {
    const cached = layers.get(key);
    if (cached !== undefined) return cached;
    if (visiting.has(key))
      throw new Error("The task dependency graph contains a cycle");
    const task = byKey.get(key);
    if (task === undefined) throw new Error(`Unknown blocker ${key}`);
    if (new Set(task.blockedBy).size !== task.blockedBy.length)
      throw new Error(`List each blocker for ${key} once`);
    visiting.add(key);
    const wave = 1 + Math.max(0, ...task.blockedBy.map(layerOf));
    visiting.delete(key);
    layers.set(key, wave);
    return wave;
  }
  for (const task of tasks) layerOf(task.key);
  for (const [index, task] of tasks.entries()) {
    for (const other of tasks.slice(index + 1)) {
      if (layers.get(task.key) !== layers.get(other.key)) continue;
      if (task.owns.some((a) => other.owns.some((b) => ownsOverlap(a, b))))
        throw new Error(
          `${task.key} and ${other.key} own overlapping paths in the same wave`,
        );
    }
  }
  return layers;
}
