import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, rename, rm } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const version = (await readFile(join(root, ".bun-version"), "utf8")).trim();
let observed;
try {
  observed = execFileSync(process.execPath, ["--version"], { encoding: "utf8" }).trim();
} catch {
  console.error(`Building pi-driver requires Bun ${version} on PATH.`);
  process.exit(1);
}
if (observed !== version) {
  console.error(`Building pi-driver requires Bun ${version}. Found ${observed}.`);
  process.exit(1);
}

const destination = join(root, ".aot");
await mkdir(destination, { recursive: true });
const staging = await mkdtemp(join(destination, "build-"));
try {
  const output = join(staging, "pi-driver");
  execFileSync(process.execPath, [
    "build", "--compile", "--aot",
    "--no-compile-autoload-dotenv", "--no-compile-autoload-bunfig",
    "cli.ts", "--outfile", output,
  ], { cwd: root, stdio: "inherit" });
  await rename(output, join(destination, "pi-driver"));
} finally {
  await rm(staging, { recursive: true, force: true });
}
