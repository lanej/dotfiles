import {
  create,
  fromBinary,
  toBinary,
  type MessageInitShape,
} from "@bufbuild/protobuf";
import { createHash } from "node:crypto";
import { lstatSync } from "node:fs";
import { createConnection } from "node:net";
import { homedir, tmpdir } from "node:os";
import { isAbsolute, join } from "node:path";
import { Database } from "bun:sqlite";
import { z } from "zod";
import { ClientToServerMsgSchema } from "./generated/zellij/client_to_server_pb.js";
import type { ActionSchema } from "./generated/zellij/common_types_pb.js";
import { ServerToClientMsgSchema } from "./generated/zellij/server_to_client_pb.js";

const frameLimit = 4 * 1024 * 1024;
const namespace = "contract_version_1";
const uint32 = z.number().int().min(0).max(0xffffffff);
const panes = z.array(
  z.object({
    id: uint32,
    tab_id: uint32,
    is_plugin: z.boolean(),
    exited: z.boolean(),
    terminal_command: z.string().nullish(),
    pane_cwd: z.string().nullish(),
  }),
);

function absolute(value: string | undefined): string | undefined {
  return value !== undefined && isAbsolute(value) ? value : undefined;
}

function sessionSocket(
  session: string,
  uid: number,
  cacheDirectory?: string,
): string {
  const override = process.env["ZELLIJ_SOCKET_DIR"];
  if (override !== undefined && !isAbsolute(override))
    throw new Error("Zellij socket directory must be absolute");
  const linux = process.platform === "linux";
  if (!linux && process.platform !== "darwin")
    throw new Error("Zellij socket discovery supports macOS and Linux");
  const runtime = linux ? absolute(process.env["XDG_RUNTIME_DIR"]) : undefined;
  const sockets = join(
    override ??
      (runtime === undefined
        ? join(tmpdir(), `zellij-${String(uid)}`)
        : join(runtime, "zellij")),
    namespace,
  );
  const cache =
    cacheDirectory ??
    (linux
      ? join(
          absolute(process.env["XDG_CACHE_HOME"]) ?? join(homedir(), ".cache"),
          "zellij",
        )
      : join(homedir(), "Library", "Caches", "org.Zellij-Contributors.Zellij"));
  const index =
    override === undefined
      ? "session_index.sqlite"
      : `session_index-${createHash("sha256").update(sockets).digest("hex").slice(0, 12)}.sqlite`;
  const database = new Database(join(cache, namespace, index), {
    readonly: true,
  });
  try {
    database.run("PRAGMA busy_timeout=100");
    const { id } = z
      .object({ id: z.string().regex(/^(?!\.{1,2}$)[^/\0]+$/u) })
      .parse(
        database
          .prepare(
            "SELECT COALESCE(id, name) AS id FROM sessions WHERE name = ?",
          )
          .get(session),
      );
    return join(sockets, id);
  } finally {
    database.close();
  }
}

function socketIdentity(path: string, uid: number): string {
  const info = lstatSync(path, { bigint: true });
  if (!info.isSocket() || info.uid !== BigInt(uid))
    throw new Error("Zellij session socket is not owned by this user");
  return JSON.stringify([
    path,
    String(info.dev),
    String(info.ino),
    String(info.ctimeNs),
  ]);
}

export function tabId(value: string): number {
  if (!/^\d+$/u.test(value)) throw new Error("Use a numeric Zellij tab ID");
  return uint32.parse(Number(value));
}

function terminalPane(pane: number) {
  return { paneType: { case: "terminal", value: pane } } as const;
}

export class Zellij {
  readonly identity: string;
  private readonly uid: number;
  private readonly path: string;
  private readonly terminal: number | undefined;

  constructor(
    private readonly session: string,
    private readonly cacheDirectory?: string,
  ) {
    const uid = process.getuid?.();
    if (uid === undefined) throw new Error("Zellij requires a Unix user ID");
    this.uid = uid;
    this.path = sessionSocket(session, uid, this.cacheDirectory);
    this.identity = socketIdentity(this.path, uid);
    const terminal = /^(?:terminal_)?(\d+)$/u.exec(
      process.env["ZELLIJ_PANE_ID"] ?? "",
    )?.[1];
    this.terminal = terminal === undefined ? undefined : tabId(terminal);
  }

  private validate(): void {
    if (
      sessionSocket(this.session, this.uid, this.cacheDirectory) !==
        this.path ||
      socketIdentity(this.path, this.uid) !== this.identity
    )
      throw new Error("Zellij session now belongs to a different server");
  }

  private async request(
    actionType: NonNullable<
      MessageInitShape<typeof ActionSchema>["actionType"]
    >,
    expectOutput = true,
  ): Promise<string> {
    this.validate();
    const payload = toBinary(
      ClientToServerMsgSchema,
      create(ClientToServerMsgSchema, {
        message: {
          case: "action",
          value: {
            action: { actionType },
            terminalId: this.terminal,
            isCliClient: true,
          },
        },
      }),
    );
    if (payload.length > frameLimit)
      throw new Error("Zellij request exceeds the frame limit");
    const size = Buffer.alloc(4);
    size.writeUInt32LE(payload.length);
    const frame = Buffer.concat([size, payload]);
    return await new Promise<string>((resolve, reject) => {
      const socket = createConnection({ path: this.path });
      const timer = setTimeout(() => {
        socket.destroy(
          new Error("Zellij action timed out. Its outcome may be unknown"),
        );
      }, 5_000);
      let pending = Buffer.alloc(0);
      function complete(value: string): void {
        resolve(value);
        socket.destroy();
      }
      socket.once("connect", () => {
        try {
          this.validate();
          socket.write(frame);
        } catch (error) {
          socket.destroy(
            error instanceof Error ? error : new Error(String(error)),
          );
        }
      });
      socket.on("data", (chunk: Buffer) => {
        try {
          pending = Buffer.concat([pending, chunk]);
          while (pending.length >= 4) {
            const bytes = pending.readUInt32LE();
            if (bytes > frameLimit)
              throw new Error("Zellij response exceeds the frame limit");
            if (pending.length < 4 + bytes) return;
            const { message } = fromBinary(
              ServerToClientMsgSchema,
              pending.subarray(4, 4 + bytes),
            );
            pending = pending.subarray(4 + bytes);
            if (message.case === "log") {
              complete(message.value.lines.join("\n"));
              return;
            }
            if (message.case === "unblockInputThread" && !expectOutput) {
              complete("");
              return;
            }
            if (message.case === "logError")
              throw new Error(message.value.lines.join("\n"));
            if (message.case === "exit")
              throw new Error(
                "Zellij exited while processing the action. Its outcome may be unknown",
              );
          }
        } catch (error) {
          socket.destroy(
            error instanceof Error ? error : new Error(String(error)),
          );
        }
      });
      socket.once("error", reject);
      socket.once("close", () => {
        clearTimeout(timer);
        reject(
          new Error(
            "Zellij connection closed without a reply. Its outcome may be unknown",
          ),
        );
      });
    });
  }

  async paneListing(): Promise<string> {
    return await this.request({
      case: "listPanes",
      value: { showAll: true, outputJson: true },
    });
  }

  async panes(): Promise<z.infer<typeof panes>> {
    return panes.parse(JSON.parse(await this.paneListing()));
  }

  async capture(pane: number, full: boolean, ansi: boolean): Promise<string> {
    return await this.request({
      case: "dumpScreen",
      value: {
        paneId: terminalPane(pane),
        dumpToStdout: true,
        includeScrollback: full,
        ansi,
      },
    });
  }

  async writeText(pane: number, text: string): Promise<void> {
    await this.request(
      {
        case: "writeCharsToPaneId",
        value: { paneId: terminalPane(pane), chars: text },
      },
      false,
    );
  }

  async writeBytes(pane: number, bytes: number[]): Promise<void> {
    await this.request(
      {
        case: "writeToPaneId",
        value: { paneId: terminalPane(pane), bytes },
      },
      false,
    );
  }

  async launchTab(explicit?: number): Promise<number> {
    const candidates = await this.panes();
    const tab =
      explicit ??
      candidates.find(
        (pane) => pane.id === this.terminal && !pane.is_plugin && !pane.exited,
      )?.tab_id;
    if (tab === undefined || !candidates.some((pane) => pane.tab_id === tab))
      throw new Error(
        "Start from a live Zellij pane or select an existing tab with --tab-id",
      );
    return tab;
  }

  async launch(
    tab: number,
    name: string,
    cwd: string,
    args: string[],
  ): Promise<number> {
    const reply = await this.request({
      case: "newTiledPane",
      value: {
        tabId: tab,
        paneName: name,
        noFocus: true,
        command: { command: "/usr/bin/env", args, cwd },
      },
    });
    const terminal = /^terminal_(\d+)$/u.exec(reply.trim())?.[1];
    if (terminal === undefined)
      throw new Error("Zellij did not confirm a terminal pane identity");
    return tabId(terminal);
  }

  async focus(pane: number): Promise<void> {
    await this.request(
      {
        case: "focusPaneByPaneId",
        value: { paneId: terminalPane(pane) },
      },
      false,
    );
  }
}
