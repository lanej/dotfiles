import { fromBinary } from "@bufbuild/protobuf";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { createServer } from "node:net";
import { dirname, join } from "node:path";
import { Database } from "bun:sqlite";
import { test } from "node:test";
import { ClientToServerMsgSchema } from "../generated/zellij/client_to_server_pb.js";
import { Zellij } from "../zellij.ts";

await test("a lost pane launch is sent once and a replaced server is never focused", async (t) => {
  const root = await mkdtemp("/tmp/pi-zellij-test-");
  t.after(async () => {
    await rm(root, { recursive: true, force: true });
  });
  const sockets = join(root, "contract_version_1");
  const cache = join(
    root,
    process.platform === "darwin"
      ? "Library/Caches/org.Zellij-Contributors.Zellij"
      : "zellij",
    "contract_version_1",
  );
  await mkdir(cache, { recursive: true });
  await mkdir(sockets);
  const environment = {
    ZELLIJ_SOCKET_DIR: root,
    ZELLIJ_PANE_ID: "terminal_0",
  };
  const previous = Object.entries(environment).map(
    ([key]) => [key, process.env[key]] as const,
  );
  Object.assign(process.env, environment);
  t.after(() => {
    for (const [key, value] of previous) {
      if (value === undefined) Reflect.deleteProperty(process.env, key);
      else process.env[key] = value;
    }
  });

  const suffix = createHash("sha256")
    .update(sockets)
    .digest("hex")
    .slice(0, 12);
  const index = new Database(join(cache, `session_index-${suffix}.sqlite`));
  index.run(
    "CREATE TABLE sessions (id TEXT, name TEXT); INSERT INTO sessions VALUES ('one', 'test');",
  );
  index.close();
  const path = join(sockets, "one");
  let launches = 0;
  const first = createServer((socket) => {
    let pending = Buffer.alloc(0);
    socket.on("data", (chunk: Buffer) => {
      pending = Buffer.concat([pending, chunk]);
      if (pending.length < 4 || pending.length < 4 + pending.readUInt32LE())
        return;
      const { message } = fromBinary(
        ClientToServerMsgSchema,
        pending.subarray(4),
      );
      assert.equal(message.case, "action");
      assert.equal(message.value.terminalId, 0);
      const action = message.value.action?.actionType;
      assert.equal(action?.case, "newTiledPane");
      assert.equal(action.value.noFocus, true);
      assert.equal(action.value.tabId, 3);
      launches++;
      socket.destroy();
    });
  });
  await new Promise<void>((resolve, reject) => {
    first.once("error", reject);
    first.listen(path, resolve);
  });
  let zellij: Zellij;
  try {
    zellij = new Zellij("test", dirname(cache));
    await assert.rejects(
      zellij.launch(3, "trial", "/tmp", ["pi"]),
      /outcome may be unknown/u,
    );
    assert.equal(launches, 1);
  } finally {
    await new Promise<void>((resolve) => {
      first.close(() => {
        resolve();
      });
    });
  }
  let replacementConnections = 0;
  const replacement = createServer((socket) => {
    replacementConnections++;
    socket.destroy();
  });
  await new Promise<void>((resolve, reject) => {
    replacement.once("error", reject);
    replacement.listen(path, resolve);
  });
  try {
    await assert.rejects(zellij.focus(17), /different server/u);
    assert.equal(replacementConnections, 0);
  } finally {
    await new Promise<void>((resolve) => {
      replacement.close(() => {
        resolve();
      });
    });
  }
});
