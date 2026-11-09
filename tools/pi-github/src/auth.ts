import { readFile, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { getAgentDir, ModelRuntime } from "@earendil-works/pi-coding-agent";
import type { CredentialStore, Credential, CredentialInfo, AuthOperationOptions } from "@earendil-works/pi-ai";

export class CodexSessionReference implements CredentialStore {
  constructor(private directory: string, private now: () => number = Date.now) {}
  async read(providerId: string, options?: AuthOperationOptions): Promise<Credential | undefined> {
    options?.signal?.throwIfAborted();
    if (providerId !== "openai-codex") return undefined;
    const path = join(this.directory, "auth.json");
    let raw: unknown;
    try {
      if ((await stat(path)).size > 1024 * 1024) throw new Error("Oversized authentication file");
      raw = JSON.parse(await readFile(path, "utf8"));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return undefined;
      throw new Error("Existing Codex authentication could not be read");
    }
    options?.signal?.throwIfAborted();
    const document = raw as { auth_mode?: unknown; tokens?: { access_token?: unknown } } | null;
    if (document?.auth_mode !== "chatgpt" || typeof document.tokens?.access_token !== "string") return undefined;
    const access = document.tokens.access_token;
    let expires: number;
    try {
      const claims = JSON.parse(Buffer.from(access.split(".")[1] ?? "", "base64url").toString("utf8")) as { exp?: unknown };
      if (typeof claims.exp !== "number" || !Number.isFinite(claims.exp)) throw new Error("Missing expiry");
      expires = claims.exp * 1000;
    } catch { throw new Error("Existing Codex authentication has an unsupported access token"); }
    // WHY: Codex alone owns refresh-token rotation. Never hand its refresh token to Pi or pretend an expired token is valid.
    if (expires <= this.now() + 5 * 60 * 1000) throw new Error("Existing Codex authentication needs refreshing through Codex");
    return { type: "oauth", access, refresh: "", expires };
  }
  async list(options?: AuthOperationOptions): Promise<readonly CredentialInfo[]> {
    return await this.read("openai-codex", options) ? [{ providerId: "openai-codex", type: "oauth" }] : [];
  }
  async modify(): Promise<never> { throw new Error("Codex authentication is read-only; Codex owns refresh and login"); }
  async delete(): Promise<never> { throw new Error("Codex authentication is read-only; sign out through Codex"); }
}

export async function createWorkerRuntime(options: { piAgentDir?: string; codexHome?: string; now?: () => number } = {}): Promise<{ runtime: ModelRuntime; source: "pi" | "codex" }> {
  const piAgentDir = options.piAgentDir ?? getAgentDir();
  const piPath = join(piAgentDir, "auth.json");
  if (existsSync(piPath)) {
    const runtime = await ModelRuntime.create({ authPath: piPath, modelsPath: null, allowModelNetwork: false });
    if (runtime.hasConfiguredAuth("openai-codex")) return { runtime, source: "pi" };
  }
  const credentials = new CodexSessionReference(options.codexHome ?? process.env.CODEX_HOME ?? join(homedir(), ".codex"), options.now);
  if (!await credentials.read("openai-codex")) throw new Error("No existing ChatGPT authentication found in Pi or Codex");
  const runtime = await ModelRuntime.create({ credentials, modelsPath: null, allowModelNetwork: false });
  if (!runtime.hasConfiguredAuth("openai-codex")) throw new Error("Existing Codex authentication is unavailable");
  return { runtime, source: "codex" };
}
