import { snapshot, type DiagnosticSnapshot } from "./diagnostics.ts";
import { access, lstat, readFile, realpath, stat } from "node:fs/promises";
import { createPatch } from "diff";
import { randomUUID } from "node:crypto";
import {
  dirname,
  extname,
  isAbsolute,
  relative,
  resolve,
  sep,
} from "node:path";
import { fileURLToPath } from "node:url";
import { z } from "zod";
import { LspClient, type ServerSpec } from "./client.ts";

export enum Lookup {
  Definition = "definition",
  References = "references",
  Implementation = "implementation",
  Hover = "hover",
  DocumentSymbols = "documentSymbols",
  WorkspaceSymbols = "workspaceSymbols",
  Diagnostics = "diagnostics",
}
const servers: Record<string, ServerSpec & { manifests: string[] }> = {
  go: {
    name: "Go",
    command: "gopls",
    args: [],
    languageId: "go",
    manifests: ["go.work", "go.mod"],
  },
  rs: {
    name: "Rust",
    command: "rust-analyzer",
    args: [],
    languageId: "rust",
    manifests: ["Cargo.toml"],
  },
  ts: {
    name: "TypeScript",
    command: "typescript-language-server",
    args: ["--stdio"],
    languageId: "typescript",
    manifests: ["tsconfig.json", "jsconfig.json", "package.json"],
  },
};
const aliases: Record<string, string> = {
  tsx: "ts",
  js: "ts",
  jsx: "ts",
  mjs: "ts",
  cjs: "ts",
  mts: "ts",
  cts: "ts",
};
const positionSchema = z.object({
  line: z.number().int().nonnegative(),
  character: z.number().int().nonnegative(),
});
const editSchema = z.object({
  range: z.object({ start: positionSchema, end: positionSchema }),
  newText: z.string(),
});
const workspaceEditSchema = z
  .object({
    changes: z.record(z.string(), z.array(editSchema)).optional(),
    documentChanges: z
      .array(
        z.object({
          textDocument: z.object({
            uri: z.string(),
            version: z.number().int().nullable().optional(),
          }),
          edits: z.array(editSchema),
        }),
      )
      .optional(),
  })
  .refine(
    (value) =>
      value.changes === undefined || value.documentChanges === undefined,
    "Ambiguous workspace edit",
  );
export interface RenameFile {
  path: string;
  before: string;
  after: string;
}
export interface RenamePreview {
  token: string;
  expires: number;
  files: RenameFile[];
}

function present(value: unknown): unknown {
  if (Array.isArray(value)) return value.map((item: unknown) => present(item));
  const position = positionSchema.strict().safeParse(value);
  if (position.success)
    return {
      line: position.data.line + 1,
      column: position.data.character + 1,
    };
  const object = z.record(z.string(), z.unknown()).safeParse(value);
  if (!object.success) return value;
  return Object.fromEntries(
    Object.entries(object.data).map(([key, item]) => {
      if (
        (key === "uri" || key === "targetUri") &&
        typeof item === "string" &&
        item.startsWith("file:")
      )
        return [key === "uri" ? "path" : "targetPath", fileURLToPath(item)];
      return [key, present(item)];
    }),
  );
}

export function offset(
  text: string,
  position: z.infer<typeof positionSchema>,
): number {
  const lines = text.split("\n");
  const line = lines[position.line];
  if (
    line === undefined ||
    position.character > line.replace(/\r$/u, "").length
  )
    throw new Error("Invalid LSP text position");
  const prefix = lines.slice(0, position.line).join("\n");
  const result =
    prefix.length + (position.line === 0 ? 0 : 1) + position.character;
  const previous = text.charCodeAt(result - 1);
  const next = text.charCodeAt(result);
  if (
    previous >= 0xd800 &&
    previous <= 0xdbff &&
    next >= 0xdc00 &&
    next <= 0xdfff
  )
    throw new Error("LSP position splits a Unicode character");
  return result;
}

export async function safePath(cwd: string, path: string): Promise<string> {
  const root = await realpath(cwd);
  const target = resolve(root, path);
  const within = relative(root, target);
  if (
    within === "" ||
    isAbsolute(within) ||
    within === ".." ||
    within.startsWith(`..${sep}`) ||
    within.split(sep).includes(".git")
  )
    throw new Error(
      "LSP paths must stay inside the active checkout and outside .git",
    );
  for (let current = target; current !== root; current = dirname(current)) {
    if ((await lstat(current)).isSymbolicLink())
      throw new Error("LSP paths cannot follow symbolic links");
  }
  return target;
}

export class CodeIntelligence {
  constructor(
    private readonly startClient: (
      root: string,
      spec: ServerSpec,
    ) => LspClient = (root, spec) => new LspClient(root, spec),
  ) {}

  private readonly observers = new Set<
    (snapshot: DiagnosticSnapshot) => void
  >();
  private readonly subscriptions: (() => void)[] = [];
  onDiagnostics(observer: (snapshot: DiagnosticSnapshot) => void): () => void {
    this.observers.add(observer);
    return () => {
      this.observers.delete(observer);
    };
  }

  private readonly clients = new Map<string, LspClient>();
  private readonly previews = new Map<string, RenamePreview>();
  private readonly unavailable = new Map<string, string>();
  private queue: Promise<unknown> = Promise.resolve();
  enabled = true;

  serial<T>(operation: () => Promise<T>): Promise<T> {
    const result = this.queue.then(operation);
    this.queue = result.catch(() => undefined);
    return result;
  }

  async client(
    cwd: string,
    path: string,
  ): Promise<{ client: LspClient; path: string }> {
    if (!this.enabled) throw new Error("LSP disabled by lsp.enabled");
    const target = await safePath(cwd, path);
    const extension = extname(target).slice(1);
    const spec = servers[aliases[extension] ?? extension];
    if (spec === undefined)
      throw new Error(`LSP unavailable for .${extension}`);
    const checkout = await realpath(cwd);
    let root = dirname(target);
    for (;;) {
      const found = await Promise.all(
        spec.manifests.map(async (manifest) => {
          try {
            await access(resolve(root, manifest));
            return true;
          } catch {
            return false;
          }
        }),
      );
      if (found.some(Boolean) || root === checkout) break;
      root = dirname(root);
    }
    const key = `${checkout}:${root}:${spec.command}`;
    let client = this.clients.get(key);
    if (client === undefined) {
      const entries = (process.env["PATH"] ?? "").split(
        sep === "/" ? ":" : ";",
      );
      let executable = false;
      for (const entry of entries) {
        try {
          await access(resolve(entry, spec.command), 1);
          executable = true;
          break;
        } catch {
          /* Try the next PATH entry. */
        }
      }
      if (!executable) {
        const message = `${spec.command} is not installed on PATH; use text search or install it through the existing tool setup`;
        this.unavailable.set(spec.command, message);
        throw new Error(message);
      }
      this.unavailable.delete(spec.command);
      client = this.startClient(root, spec);
      this.clients.set(key, client);
      this.subscriptions.push(
        client.onDiagnostics((path, result) => {
          for (const observer of this.observers)
            observer(snapshot(path, result));
        }),
      );
    }
    await client.refresh();
    await client.sync(target);
    return { client, path: target };
  }

  async lookup(
    cwd: string,
    action: Lookup,
    path: string,
    line: number,
    column: number,
    query: string,
    signal?: AbortSignal,
  ): Promise<unknown> {
    const { client, path: target } = await this.client(cwd, path);
    if (action === Lookup.Diagnostics) return this.diagnostics(cwd, target);
    const methods: Record<
      Exclude<Lookup, Lookup.Diagnostics>,
      [string, Parameters<LspClient["supports"]>[0]]
    > = {
      [Lookup.Definition]: ["textDocument/definition", "definitionProvider"],
      [Lookup.References]: ["textDocument/references", "referencesProvider"],
      [Lookup.Implementation]: [
        "textDocument/implementation",
        "implementationProvider",
      ],
      [Lookup.Hover]: ["textDocument/hover", "hoverProvider"],
      [Lookup.DocumentSymbols]: [
        "textDocument/documentSymbol",
        "documentSymbolProvider",
      ],
      [Lookup.WorkspaceSymbols]: [
        "workspace/symbol",
        "workspaceSymbolProvider",
      ],
    };
    const [method, capability] = methods[action];
    if (!client.supports(capability))
      throw new Error(`Server does not support ${action}`);
    const { uri } = await client.sync(target);
    const position = { line: line - 1, character: column - 1 };
    if (action !== Lookup.DocumentSymbols && action !== Lookup.WorkspaceSymbols)
      offset(await readFile(target, "utf8"), position);
    return present(
      await client.request(
        method,
        action === Lookup.WorkspaceSymbols
          ? { query }
          : {
              textDocument: { uri },
              position,
              ...(action === Lookup.References
                ? { context: { includeDeclaration: true } }
                : {}),
            },
        signal,
      ),
    );
  }

  async diagnostics(cwd: string, path: string): Promise<DiagnosticSnapshot> {
    const { client, path: target } = await this.client(cwd, path);
    const result = await client.getDiagnostics(target);
    return snapshot(target, result);
  }

  async preview(
    cwd: string,
    path: string,
    line: number,
    column: number,
    newName: string,
    signal?: AbortSignal,
  ): Promise<RenamePreview> {
    this.previews.clear();
    const { client, path: target } = await this.client(cwd, path);
    if (!client.supports("renameProvider"))
      throw new Error("Server does not support semantic rename");
    const { uri } = await client.sync(target);
    const beforeRequest = await readFile(target, "utf8");
    const position = { line: line - 1, character: column - 1 };
    offset(beforeRequest, position);
    // Filesystem timestamps can have finer resolution than Date.now().
    const requestedAt = Date.now() + 1;
    const response = await client.request(
      "textDocument/rename",
      { textDocument: { uri }, position, newName },
      signal,
    );
    const edit = workspaceEditSchema.parse(response);
    const changes =
      edit.documentChanges ??
      Object.entries(edit.changes ?? {}).map(([uri, edits]) => ({
        textDocument: { uri, version: null },
        edits,
      }));
    if (changes.length === 0 || changes.length > 100)
      throw new Error("Rename must change between 1 and 100 files");
    const seen = new Set<string>();
    const files: RenameFile[] = [];
    for (const change of changes) {
      const path = await safePath(cwd, fileURLToPath(change.textDocument.uri));
      if (seen.has(path))
        throw new Error("Rename contains duplicate file entries");
      seen.add(path);
      if ((await stat(path)).mtimeMs > requestedAt)
        throw new Error("File changed while preparing rename");
      const before = await readFile(path, "utf8");
      if (path === target && before !== beforeRequest)
        throw new Error("File changed while preparing rename");
      const snapshot = await client.sync(path);
      if (
        change.textDocument.version !== null &&
        change.textDocument.version !== undefined &&
        change.textDocument.version !== snapshot.version
      )
        throw new Error("Rename contains stale document versions");
      const edits = change.edits
        .map((item) => ({
          start: offset(before, item.range.start),
          end: offset(before, item.range.end),
          text: item.newText,
        }))
        .sort((a, b) => b.start - a.start);
      let after = before;
      let boundary = before.length + 1;
      for (const item of edits) {
        if (
          item.end < item.start ||
          item.end > boundary ||
          item.start === boundary
        )
          throw new Error("Rename contains overlapping edits");
        after = after.slice(0, item.start) + item.text + after.slice(item.end);
        boundary = item.start;
      }
      files.push({ path, before, after });
    }
    const preview = {
      token: randomUUID(),
      expires: Date.now() + 300_000,
      files,
    };
    if (JSON.stringify(this.describe(preview)).length > 20_000)
      throw new Error("Rename diff exceeds preview limit; narrow the change");
    this.previews.set(preview.token, preview);
    return preview;
  }

  describe(preview: RenamePreview) {
    return {
      token: preview.token,
      expires: preview.expires,
      files: preview.files.map((file) => ({
        path: file.path,
        diff: createPatch(file.path, file.before, file.after),
      })),
    };
  }

  async consume(cwd: string, token: string): Promise<RenamePreview> {
    const preview = this.previews.get(token);
    this.previews.delete(token);
    if (preview === undefined || preview.expires < Date.now())
      throw new Error("Rename preview expired; prepare it again");
    for (const file of preview.files) {
      await safePath(cwd, file.path);
      if ((await readFile(file.path, "utf8")) !== file.before)
        throw new Error(`Rename preview is stale: ${file.path}`);
    }
    return preview;
  }

  status(): string {
    if (!this.enabled) return "LSP disabled";
    return [
      "LSP: installed servers start on demand",
      ...this.unavailable.values(),
      ...[...this.clients.values()].map(
        (client) =>
          `${client.spec.name}: ${client.state} (${client.root})${client.failure === undefined ? "" : `: ${client.failure}`}`,
      ),
    ].join("\n");
  }

  async stop(): Promise<void> {
    this.previews.clear();
    for (const unsubscribe of this.subscriptions.splice(0)) unsubscribe();
    const clients = [...this.clients.values()];
    this.clients.clear();
    this.unavailable.clear();
    await Promise.all(clients.map((client) => client.stop()));
  }
}
