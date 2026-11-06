import { DaemonClient } from "@getpaseo/client/internal/daemon-client";
import { createHostChannelTransport } from "@getpaseo/client/internal/hosts";
import { createPaseoApi } from "@getpaseo/client";
import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { join } from "node:path";
import type { Router } from "./service";

export class Connection implements Router {
  readonly raw: DaemonClient;
  constructor(home: string) {
    const config = JSON.parse(readFileSync(join(home, "config.json"), "utf8"));
    const listen = config.daemon?.listen;
    if (typeof listen !== "string" || !/^(127\.0\.0\.1|localhost|\[::1\]):[0-9]+$/.test(listen)) {
      throw new Error("Tasks requires an explicit loopback daemon listener; configure its authenticated Paseo connection");
    }
    // NOTE: These official SDK exports are pinned to 0.15.1 because PaseoApi has no plugin-RPC method.
    this.raw = new DaemonClient({
      url: `ws://${listen}/ws`, clientId: `tasks-${randomUUID()}`,
      password: process.env.PASEO_PASSWORD, reconnect: { enabled: true },
    });
  }
  async open() {
    await this.raw.connect();
    const info = this.raw.getLastServerInfoMessage();
    if (!info?.serverId) throw new Error("Paseo did not establish this host's identity");
    return { serverId: info.serverId, paseo: createPaseoApi(this.raw) };
  }
  async call(serverId: string, method: string, input: unknown) {
    const self = this.raw.getLastServerInfoMessage()?.serverId;
    if (serverId === self) return this.raw.invokePluginRpc("tasks", method, input);
    const scopeId = randomUUID();
    const routeId = await this.raw.openHostRoute(serverId, scopeId);
    const remote = new DaemonClient({
      url: "ws://routed-host/ws", clientId: scopeId, reconnect: { enabled: false },
      transportFactory: createHostChannelTransport(this.raw, serverId, scopeId, routeId),
    });
    try {
      await remote.connect();
      if (remote.getLastServerInfoMessage()?.serverId !== serverId) throw new Error("Remote host identity mismatch");
      return await remote.invokePluginRpc("tasks", method, input);
    } finally { await remote.close(); }
  }
  close() { return this.raw.close(); }
}
