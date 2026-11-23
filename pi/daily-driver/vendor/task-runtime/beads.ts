import createClient from "openapi-fetch";
import { fetchBeads } from "./fetch.mjs";
import { z } from "zod";
import type { paths } from "./generated/beads.ts";
export type { components } from "./generated/beads.ts";

export class BeadsError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly problem: unknown,
  ) {
    super(message);
  }
}

export class BeadsHttp {
  protected readonly client;
  constructor(
    readonly url: string,
    readonly authority: string,
    token?: string,
  ) {
    const target = new URL(url);
    if (
      !["http:", "https:"].includes(target.protocol) ||
      target.username !== "" ||
      target.password !== "" ||
      target.search !== "" ||
      target.hash !== "" ||
      target.pathname !== "/"
    )
      throw new Error(
        "Beads URL must name an HTTP(S) service origin without credentials",
      );
    if (
      target.protocol === "http:" &&
      !["127.0.0.1", "localhost", "[::1]"].includes(target.hostname)
    )
      throw new Error(
        "Non-loopback Beads endpoints require HTTPS; use a loopback tunnel for private HTTP services",
      );
    z.uuid().parse(authority);
    this.client = createClient<paths>({
      baseUrl: target.origin,
      headers: {
        "Bd-Project-Id": authority,
        ...(token !== undefined && token !== ""
          ? { Authorization: `Bearer ${token}` }
          : {}),
      },
      fetch: fetchBeads,
    });
  }
  protected async result<T>(
    pending: Promise<{ data?: T; error?: unknown; response: Response }>,
  ): Promise<T> {
    const response = await pending;
    if (!response.response.ok || response.data === undefined) {
      const problem = z
        .object({ code: z.string().optional(), reason: z.string().optional() })
        .loose()
        .safeParse(response.error);
      throw new BeadsError(
        `Beads HTTP ${String(response.response.status)}${problem.success ? `: ${problem.data.code ?? "unknown"} ${problem.data.reason ?? ""}` : ""}`,
        response.response.status,
        response.error,
      );
    }
    return response.data;
  }
  async verifyAuthority() {
    const context = await this.result(this.client.GET("/v0/beads/context"));
    if (
      context.project_id !== this.authority ||
      context.backend !== "dolt" ||
      context.dolt_mode !== "server"
    )
      throw new Error(
        "Beads authority differs from configured service project; refusing foreign or embedded storage",
      );
    for (const capability of [
      "project.enforce",
      "issues.get",
      "issues.create",
      "issues.update",
    ])
      if (!context.capabilities.includes(capability))
        throw new Error(
          `Beads service lacks required capability: ${capability}`,
        );
  }
}
