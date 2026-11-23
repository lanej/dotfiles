import assert from "node:assert/strict";
import {
  mkdtemp,
  readFile,
  realpath,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { LspClient, ServerState } from "../code-intelligence/client.ts";
import {
  Lookup,
  CodeIntelligence,
  offset,
  safePath,
} from "../code-intelligence/service.ts";

const fixtureServer = fileURLToPath(
  new URL("fixtures/lsp-server.ts", import.meta.url),
);

await test("LSP synchronizes edits, rejects stale diagnostics, cancels requests and shuts down", async () => {
  const root = await realpath(await mkdtemp(join(tmpdir(), "pi-lsp-client-")));
  const client = new LspClient(root, {
    name: "fixture",
    languageId: "typescript",
    command: process.execPath,
    args: [fixtureServer],
  });
  const path = join(root, "test.ts");
  try {
    const publications: string[] = [];
    const unsubscribe = client.onDiagnostics((path, result) => {
      publications.push(`${path}:${String(result.items.length)}`);
    });
    await writeFile(path, "BAD");
    const initial = await client.getDiagnostics(path);
    assert.equal(initial?.items.length, 1);
    assert.ok(publications.includes(`${path}:1`));
    unsubscribe();
    await writeFile(path, "good");
    const fixed = await client.getDiagnostics(path);
    assert.equal(fixed?.version, 2);
    assert.deepEqual(fixed.items, []);
    const unrelated = join(root, "unrelated.ts");
    await writeFile(unrelated, "unrelated");
    await client.sync(unrelated);
    const retained = await client.getDiagnostics(path, 20);
    assert.deepEqual(
      retained?.items,
      [],
      "opening another file must preserve diagnostics for an unchanged document",
    );
    await rm(unrelated);
    await client.refresh();
    assert.deepEqual(
      (await client.getDiagnostics(path, 20))?.items,
      [],
      "closing a deleted file must preserve unrelated diagnostics",
    );
    await writeFile(path, "SILENT");
    await client.sync(path);
    assert.equal(
      await client.getDiagnostics(path, 20),
      undefined,
      "old-version errors cannot masquerade as fresh results",
    );
    const abort = new AbortController();
    const pending = client.request("hang", {}, abort.signal);
    abort.abort();
    await assert.rejects(pending, /cancelled/u);
    const response = await client.request("textDocument/definition", {
      textDocument: { uri: new URL(`file://${path}`).href },
    });
    assert.ok(Array.isArray(response));
    await symlink(path, join(root, "link.ts"));
    await assert.rejects(safePath(root, "link.ts"), /symbolic/u);
    await assert.rejects(safePath(root, "../outside.ts"), /inside/u);
    const intelligence = new CodeIntelligence();
    intelligence.enabled = false;
    await assert.rejects(intelligence.client(root, path), /disabled/u);
    assert.equal(offset("😀 abc\r\nvalue", { line: 1, character: 2 }), 10);
    assert.throws(() => offset("😀", { line: 0, character: 1 }), /Unicode/u);
    assert.equal(await readFile(path, "utf8"), "SILENT");
    const remaining = join(root, "remaining.ts");
    await writeFile(remaining, "good");
    await client.sync(remaining);
    await rm(path);
    await client.refresh();
    const opened = await client.request("fixture/openDocuments", {});
    assert.deepEqual(opened, [new URL(`file://${remaining}`).href]);
    await writeFile(path, "external replacement");
    await rm(remaining);
    await symlink(path, remaining);
    await assert.rejects(client.refresh(), /symbolic link/u);
  } finally {
    await client.stop();
    assert.equal(client.state, ServerState.Stopped);
    await rm(root, { recursive: true, force: true });
  }
});

await test("LSP reports failed startup and unsupported position encoding", async () => {
  const root = await realpath(await mkdtemp(join(tmpdir(), "pi-lsp-failure-")));
  await writeFile(join(root, "test.ts"), "test");
  for (const args of [[], [fixtureServer, "encoding"]]) {
    const client = new LspClient(root, {
      name: "fixture",
      languageId: "typescript",
      command:
        args.length === 0 ? join(root, "not-installed") : process.execPath,
      args,
    });
    try {
      await assert.rejects(
        client.sync(join(root, "test.ts")),
        args.length === 0 ? /ENOENT/u : /UTF-16/u,
      );
      assert.equal(client.state, ServerState.Failed);
    } finally {
      await client.stop();
    }
  }
  await rm(root, { recursive: true, force: true });
});

await test("semantic rename rejects unsafe edits and stale previews before any write", async () => {
  const root = await realpath(await mkdtemp(join(tmpdir(), "pi-lsp-rename-")));
  const previousPath = process.env["PATH"];
  await symlink(process.execPath, join(root, "typescript-language-server"));
  process.env["PATH"] = root;
  const client = new LspClient(root, {
    name: "fixture",
    languageId: "typescript",
    command: process.execPath,
    args: [fixtureServer],
  });
  const intelligence = new CodeIntelligence(() => client);
  const path = join(root, "test.ts");
  try {
    await writeFile(path, "old value\n");
    for (const newName of ["resource", "escape", "overlap"]) {
      await assert.rejects(intelligence.preview(root, path, 1, 1, newName));
      assert.equal(await readFile(path, "utf8"), "old value\n");
    }
    await assert.rejects(
      intelligence.lookup(root, Lookup.Implementation, path, 1, 1, ""),
      /does not support/u,
    );
    const navigation = await intelligence.lookup(
      root,
      Lookup.Definition,
      path,
      1,
      1,
      "",
    );
    assert.match(JSON.stringify(navigation), /"line":1,"column":1/u);
    const stale = await intelligence.preview(root, path, 1, 1, "new");
    assert.match(
      intelligence.describe(stale).files[0]?.diff ?? "",
      /-old value\n\+new value/u,
    );
    await writeFile(path, "operator edit\n");
    await assert.rejects(intelligence.consume(root, stale.token), /stale/u);
    await assert.rejects(intelligence.consume(root, stale.token), /expired/u);
    const fresh = await intelligence.preview(root, path, 1, 1, "new");
    const change = await intelligence.consume(root, fresh.token);
    assert.equal(change.files[0]?.after, "newrator edit\n");
    assert.equal(
      await readFile(path, "utf8"),
      "operator edit\n",
      "preview and validation are read-only",
    );
    await intelligence.stop();
    await assert.rejects(intelligence.consume(root, fresh.token), /expired/u);
    process.env["PATH"] = "";
    await assert.rejects(
      new CodeIntelligence().client(root, path),
      /not installed/u,
    );
  } finally {
    if (previousPath === undefined) delete process.env["PATH"];
    else process.env["PATH"] = previousPath;
    await intelligence.stop();
    await client.stop();
    await rm(root, { recursive: true, force: true });
  }
});

await test("servers without change synchronization keep rejecting unsent edits", async () => {
  const root = await realpath(await mkdtemp(join(tmpdir(), "pi-lsp-no-sync-")));
  const client = new LspClient(root, {
    name: "fixture",
    languageId: "typescript",
    command: process.execPath,
    args: [fixtureServer, "no-sync"],
  });
  const path = join(root, "test.ts");
  try {
    await writeFile(path, "original");
    await client.sync(path);
    await writeFile(path, "changed");
    await assert.rejects(client.sync(path), /synchronization/u);
    await assert.rejects(client.sync(path), /synchronization/u);
  } finally {
    await client.stop();
    await rm(root, { recursive: true, force: true });
  }
});
