import { spawn } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { readFile, realpath } from "node:fs/promises";
import { extname } from "node:path";
import {
  CancellationTokenSource,
  createProtocolConnection,
  StreamMessageReader,
  StreamMessageWriter,
  InitializeRequest,
  InitializedNotification,
  DidOpenTextDocumentNotification,
  DidChangeTextDocumentNotification,
  DidSaveTextDocumentNotification,
  DidCloseTextDocumentNotification,
  PublishDiagnosticsNotification,
  ShutdownRequest,
  ExitNotification,
  TextDocumentSyncKind,
  type ServerCapabilities,
  type Diagnostic,
} from "vscode-languageserver-protocol/node";

export enum ServerState {
  Starting = "initializing",
  Ready = "ready",
  Failed = "failed",
  Stopped = "stopped",
}
export interface ServerSpec {
  name: string;
  command: string;
  args: string[];
  languageId: string;
}
const scriptLanguages: Record<string, string> = {
  ".js": "javascript",
  ".jsx": "javascriptreact",
  ".mjs": "javascript",
  ".cjs": "javascript",
  ".tsx": "typescriptreact",
};
interface Document {
  text: string;
  version: number;
}
export interface Diagnostics {
  version: number;
  freshness: "versioned" | "unversioned";
  items: Diagnostic[];
}

export class LspClient {
  private readonly process;
  private readonly connection;
  private readonly documents = new Map<string, Document>();
  private readonly diagnostics = new Map<string, Diagnostics>();
  private readonly listeners = new Set<() => void>();
  private readonly observers = new Set<
    (path: string, diagnostics: Diagnostics) => void
  >();
  private readonly ready: Promise<void>;
  private capabilities: ServerCapabilities = {};
  private stderr = "";
  state = ServerState.Starting;
  failure: string | undefined;

  constructor(
    readonly root: string,
    readonly spec: ServerSpec,
  ) {
    this.process = spawn(spec.command, spec.args, {
      cwd: root,
      detached: true,
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.connection = createProtocolConnection(
      new StreamMessageReader(this.process.stdout),
      new StreamMessageWriter(this.process.stdin),
    );
    this.process.stderr.on("data", (chunk: Buffer) => {
      this.stderr = (this.stderr + chunk.toString()).slice(-2000);
    });
    this.process.on("error", (error) => {
      this.fail(error.message);
    });
    this.process.on("exit", (code) => {
      if (this.state !== ServerState.Stopped)
        this.fail(`Server exited (${String(code)}). ${this.stderr}`);
    });
    this.connection.onError(([error]) => {
      this.fail(error.message);
    });
    this.connection.onClose(() => {
      if (this.state !== ServerState.Stopped)
        this.fail("Server connection closed");
    });
    this.connection.onNotification(
      PublishDiagnosticsNotification.type,
      (event) => {
        const document = this.documents.get(event.uri);
        if (
          document === undefined ||
          (event.version !== undefined && event.version !== document.version)
        )
          return;
        const diagnostics: Diagnostics = {
          version: document.version,
          freshness: event.version === undefined ? "unversioned" : "versioned",
          items: event.diagnostics,
        };
        this.diagnostics.set(event.uri, diagnostics);
        for (const observer of this.observers)
          observer(fileURLToPath(event.uri), diagnostics);
        for (const listener of this.listeners) listener();
      },
    );
    this.connection.onRequest(
      "workspace/configuration",
      (params: { items: unknown[] }) => params.items.map(() => ({})),
    );
    this.connection.onRequest("workspace/applyEdit", () => ({
      applied: false,
      failureReason: "Use driver_lsp_rename",
    }));
    this.connection.listen();
    this.ready = this.initialize();
    // Lazy startup is observed by requests; retain a failed status without an unhandled rejection.
    this.ready.catch(() => undefined);
  }

  onDiagnostics(
    observer: (path: string, diagnostics: Diagnostics) => void,
  ): () => void {
    this.observers.add(observer);
    return () => {
      this.observers.delete(observer);
    };
  }

  private terminate(signal: NodeJS.Signals): void {
    const pid = this.process.pid;
    if (pid === undefined) return;
    try {
      process.kill(-pid, signal);
    } catch {
      /* The owned process group may already have exited. */
    }
  }

  private fail(message: string): void {
    if (this.state === ServerState.Stopped || this.state === ServerState.Failed)
      return;
    this.state = ServerState.Failed;
    this.failure = `${this.spec.command}: ${message}`;
    this.connection.dispose();
    this.terminate("SIGTERM");
    const timer = setTimeout(() => {
      this.terminate("SIGKILL");
    }, 1000);
    timer.unref();
  }

  private async initialize(): Promise<void> {
    try {
      const response = await this.bounded((token) =>
        this.connection.sendRequest(
          InitializeRequest.type,
          {
            processId: process.pid,
            // eslint-disable-next-line @typescript-eslint/no-deprecated -- Required by InitializeParams and older installed servers.
            rootUri: pathToFileURL(this.root).href,
            workspaceFolders: [
              { uri: pathToFileURL(this.root).href, name: this.root },
            ],
            capabilities: {
              general: { positionEncodings: ["utf-16"] },
              textDocument: { publishDiagnostics: { versionSupport: true } },
              workspace: { configuration: true, workspaceFolders: true },
            },
          },
          token,
        ),
      );
      if (
        response.capabilities.positionEncoding !== undefined &&
        response.capabilities.positionEncoding !== "utf-16"
      )
        throw new Error("Server did not negotiate UTF-16 positions");
      if (this.state === ServerState.Stopped)
        throw new Error("Server stopped during initialization");
      this.capabilities = response.capabilities;
      await this.connection.sendNotification(InitializedNotification.type, {});
      this.state = ServerState.Ready;
    } catch (error) {
      this.fail(error instanceof Error ? error.message : String(error));
      throw new Error(this.failure ?? "Server stopped");
    }
  }

  private async bounded<T>(
    operation: (token: CancellationTokenSource["token"]) => Promise<T>,
    signal?: AbortSignal,
    timeoutMs = 10_000,
  ): Promise<T> {
    const cancellation = new CancellationTokenSource();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let abort: (() => void) | undefined;
    try {
      return await Promise.race([
        operation(cancellation.token),
        new Promise<never>((_resolve, reject) => {
          abort = () => {
            cancellation.cancel();
            reject(new Error("LSP request cancelled"));
          };
          timer = setTimeout(() => {
            cancellation.cancel();
            reject(
              new Error(`LSP request timed out after ${String(timeoutMs)}ms`),
            );
          }, timeoutMs);
          signal?.addEventListener("abort", abort, { once: true });
          if (signal?.aborted === true) abort();
        }),
      ]);
    } finally {
      clearTimeout(timer);
      if (abort !== undefined) signal?.removeEventListener("abort", abort);
      cancellation.dispose();
    }
  }

  async sync(path: string): Promise<{ uri: string; version: number }> {
    await this.ready;
    if (this.state !== ServerState.Ready)
      throw new Error(this.failure ?? "Server stopped");
    const uri = pathToFileURL(path).href;
    const text = await readFile(path, "utf8");
    const previous = this.documents.get(uri);
    if (previous?.text === text) return { uri, version: previous.version };
    const sync = this.capabilities.textDocumentSync;
    const kind = typeof sync === "number" ? sync : sync?.change;
    if (
      previous !== undefined &&
      (kind === TextDocumentSyncKind.None || kind === undefined)
    )
      throw new Error("Server does not support document synchronization");
    const version = (previous?.version ?? 0) + 1;
    this.documents.set(uri, { text, version });
    this.diagnostics.delete(uri);
    if (previous === undefined) {
      await this.connection.sendNotification(
        DidOpenTextDocumentNotification.type,
        {
          textDocument: {
            uri,
            version,
            languageId:
              this.spec.command === "typescript-language-server"
                ? (scriptLanguages[extname(path)] ?? this.spec.languageId)
                : this.spec.languageId,
            text,
          },
        },
      );
    } else {
      const lines = previous.text.split("\n");
      const contentChanges =
        kind === TextDocumentSyncKind.Incremental
          ? [
              {
                range: {
                  start: { line: 0, character: 0 },
                  end: {
                    line: lines.length - 1,
                    character: lines.at(-1)?.length ?? 0,
                  },
                },
                text,
              },
            ]
          : [{ text }];
      await this.connection.sendNotification(
        DidChangeTextDocumentNotification.type,
        {
          textDocument: { uri, version },
          contentChanges,
        },
      );
    }
    if (
      typeof sync === "object" &&
      sync.save !== undefined &&
      sync.save !== false
    )
      await this.connection.sendNotification(
        DidSaveTextDocumentNotification.type,
        {
          textDocument: { uri },
          ...(typeof sync.save === "object" && sync.save.includeText === true
            ? { text }
            : {}),
        },
      );
    return { uri, version };
  }

  async refresh(): Promise<void> {
    for (const uri of this.documents.keys()) {
      const path = fileURLToPath(uri);
      try {
        if ((await realpath(path)) !== path)
          throw new Error("An opened LSP document became a symbolic link");
        await this.sync(path);
      } catch (error) {
        if (
          !(
            error instanceof Error &&
            "code" in error &&
            error.code === "ENOENT"
          )
        )
          throw error;
        this.documents.delete(uri);
        this.diagnostics.delete(uri);
        await this.connection.sendNotification(
          DidCloseTextDocumentNotification.type,
          { textDocument: { uri } },
        );
      }
    }
  }

  async request(
    method: string,
    params: unknown,
    signal?: AbortSignal,
  ): Promise<unknown> {
    await this.ready;
    if (this.state !== ServerState.Ready)
      throw new Error(this.failure ?? "Server stopped");
    return this.bounded(
      (token) => this.connection.sendRequest<unknown>(method, params, token),
      signal,
    );
  }

  supports(capability: keyof ServerCapabilities): boolean {
    const value: unknown = this.capabilities[capability];
    return value !== undefined && value !== false && value !== null;
  }

  async getDiagnostics(
    path: string,
    waitMs = 1000,
  ): Promise<Diagnostics | undefined> {
    const { uri, version } = await this.sync(path);
    if (!this.diagnostics.has(uri)) {
      await new Promise<void>((resolve) => {
        const finish = () => {
          if (this.diagnostics.get(uri)?.version !== version) return;
          clearTimeout(timer);
          this.listeners.delete(finish);
          resolve();
        };
        const timer = setTimeout(() => {
          this.listeners.delete(finish);
          resolve();
        }, waitMs);
        this.listeners.add(finish);
      });
    }
    return this.diagnostics.get(uri);
  }

  async stop(): Promise<void> {
    if (this.state === ServerState.Stopped) return;
    const ready = this.state === ServerState.Ready;
    this.state = ServerState.Stopped;
    try {
      if (ready) {
        await this.bounded(
          (token) => this.connection.sendRequest(ShutdownRequest.type, token),
          undefined,
          2000,
        );
        await this.connection.sendNotification(ExitNotification.type);
      }
    } catch {
      // A broken server still needs its streams and process released.
    } finally {
      this.connection.dispose();
      this.terminate("SIGTERM");
      if (
        this.process.pid !== undefined &&
        this.process.exitCode === null &&
        this.process.signalCode === null
      ) {
        await new Promise<void>((resolve) => {
          const finished = () => {
            clearTimeout(timer);
            this.process.off("exit", finished);
            resolve();
          };
          const timer = setTimeout(finished, 1000);
          this.process.once("exit", finished);
        });
      }
      // Complete cleanup before Pi exits, including children whose server parent has stopped.
      this.terminate("SIGKILL");
    }
  }
}
