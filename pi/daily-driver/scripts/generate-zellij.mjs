import { execFileSync } from "node:child_process";
import { mkdtemp, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = fileURLToPath(new URL("../", import.meta.url));
const revision = (await readFile(new URL("../zellij-revision", import.meta.url), "utf8")).trim();
if (!/^[a-f0-9]{40}$/u.test(revision)) throw new Error("Invalid pinned Zellij revision");
const sources = [
  "app_control.proto", "client_to_server.proto", "common_types.proto",
  "pane_mirror.proto", "server_to_client.proto",
];
const upstream = "zellij-utils/src/client_server_contract/";
const localSource = process.env["ZELLIJ_PROTO_CHECKOUT"];
const readSource = async (path) => {
  if (localSource !== undefined)
    return execFileSync("git", ["-C", localSource, "show", `${revision}:${path}`]);
  const response = await fetch(`https://raw.githubusercontent.com/lanej/zellij/${revision}/${path}`, {
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`Could not fetch pinned Zellij schema: ${response.status} ${path}`);
  return Buffer.from(await response.arrayBuffer());
};

const work = await mkdtemp(join(tmpdir(), "pi-zellij-codegen-"));
try {
  const input = join(work, "proto");
  const build = join(work, "generated");
  await mkdir(input);
  await Promise.all(sources.map(async (file) => {
    await writeFile(join(input, file), await readSource(upstream + file));
  }));
  execFileSync(process.execPath, [join(packageRoot, "node_modules", ".bin", "buf"),
    "generate", input, "--template", JSON.stringify({
      version: "v2",
      plugins: [{
        local: [process.execPath, join(packageRoot, "node_modules", ".bin", "protoc-gen-es")],
        out: build,
        opt: ["target=ts", "import_extension=js"],
      }],
    }),
  ], { cwd: work, stdio: "inherit" });

  const output = join(packageRoot, "generated", "zellij");
  const generated = new Map(await Promise.all((await readdir(build)).map(async (file) =>
    [file, Buffer.from((await readFile(join(build, file), "utf8")).replace(/\n+$/u, "\n"))])));
  generated.set("LICENSE.md", await readSource("LICENSE.md"));
  generated.set("SOURCE", Buffer.from(`lanej/zellij ${revision} ${upstream}\n`));
  if (process.argv.includes("--check")) {
    const current = await readdir(output);
    if (current.length !== generated.size) throw new Error("Unexpected Zellij generated files");
    for (const [file, content] of generated)
      if (!(await readFile(join(output, file))).equals(content))
        throw new Error(`Zellij bindings are stale: ${file}. Run bun run generate:zellij`);
  } else {
    await mkdir(output, { recursive: true });
    for (const [file, content] of generated) await writeFile(join(output, file), content);
  }
} finally {
  await rm(work, { recursive: true, force: true });
}
