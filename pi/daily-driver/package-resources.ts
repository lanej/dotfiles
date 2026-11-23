import { access } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const modulePath = fileURLToPath(import.meta.url);
// Compiled commands resolve host-loaded extensions from the installed bundle.
export const packageRoot = modulePath.startsWith("/$bunfs/")
  ? dirname(dirname(process.execPath))
  : dirname(modulePath);

export function diffExtension(): string {
  // The pinned 0.1.1 package exposes this TypeScript entrypoint to the external Pi host.
  return join(packageRoot, "node_modules/pi-git-diff/src/extension.ts");
}

export async function inspectPackageResources() {
  try {
    const paths = [
      diffExtension(),
      join(packageRoot, "worker-extension.ts"),
      join(packageRoot, "scripts/pi"),
      join(packageRoot, "resources/theme.json"),
      join(packageRoot, "resources/bunfig.toml"),
      join(packageRoot, "resources/socrates/references/dialogue.txt"),
      join(
        packageRoot,
        "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js",
      ),
    ];
    await Promise.all(paths.map((path) => access(path)));
    return { available: true, paths };
  } catch (cause) {
    return {
      available: false,
      error: cause instanceof Error ? cause.message : String(cause),
    };
  }
}
