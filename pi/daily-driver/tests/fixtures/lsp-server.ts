import {
  createProtocolConnection,
  StreamMessageReader,
  StreamMessageWriter,
  InitializeRequest,
  DidOpenTextDocumentNotification,
  DidChangeTextDocumentNotification,
  DidCloseTextDocumentNotification,
  PublishDiagnosticsNotification,
  ShutdownRequest,
  ExitNotification,
  TextDocumentSyncKind,
  type InitializeResult,
} from "vscode-languageserver-protocol/node";
import { z } from "zod";
const connection = createProtocolConnection(
  new StreamMessageReader(process.stdin),
  new StreamMessageWriter(process.stdout),
);
const documents = new Map<string, { text: string; version: number }>();
connection.onRequest(
  InitializeRequest.type,
  (): InitializeResult => ({
    capabilities: {
      positionEncoding: process.argv[2] === "encoding" ? "utf-8" : "utf-16",
      textDocumentSync:
        process.argv[2] === "no-sync"
          ? TextDocumentSyncKind.None
          : TextDocumentSyncKind.Incremental,
      definitionProvider: true,
      renameProvider: true,
    },
  }),
);
const publish = async (uri: string, version: number, text: string) => {
  if (text.includes("SILENT")) return;
  await connection.sendNotification(PublishDiagnosticsNotification.type, {
    uri,
    version,
    diagnostics: text.includes("BAD")
      ? [
          {
            range: {
              start: { line: 0, character: 0 },
              end: { line: 0, character: 3 },
            },
            severity: 1,
            message: "Fixture error",
          },
        ]
      : [],
  });
};
connection.onNotification(
  DidOpenTextDocumentNotification.type,
  async ({ textDocument }) => {
    documents.set(textDocument.uri, textDocument);
    await publish(textDocument.uri, textDocument.version, textDocument.text);
  },
);
connection.onNotification(
  DidChangeTextDocumentNotification.type,
  async ({ textDocument, contentChanges }) => {
    const change = contentChanges[0];
    if (change === undefined) throw new Error("Missing synchronization change");
    if (!("range" in change))
      throw new Error("Expected negotiated incremental synchronization");
    const text = change.text;
    documents.set(textDocument.uri, { text, version: textDocument.version });
    await publish(textDocument.uri, textDocument.version - 1, "BAD");
    await publish(textDocument.uri, textDocument.version, text);
  },
);
connection.onNotification(
  DidCloseTextDocumentNotification.type,
  ({ textDocument }) => {
    documents.delete(textDocument.uri);
  },
);
connection.onRequest("fixture/openDocuments", () => [...documents.keys()]);
connection.onRequest("textDocument/definition", (params: unknown) => {
  const request = z
    .object({ textDocument: z.object({ uri: z.string() }) })
    .parse(params);
  return [
    {
      uri: request.textDocument.uri,
      range: {
        start: { line: 0, character: 0 },
        end: { line: 0, character: 3 },
      },
    },
  ];
});
connection.onRequest("textDocument/rename", (params: unknown): unknown => {
  const request = z
    .object({
      textDocument: z.object({ uri: z.string() }),
      newName: z.string(),
    })
    .parse(params);
  if (request.newName === "resource")
    return {
      documentChanges: [{ kind: "delete", uri: request.textDocument.uri }],
    };
  const uri =
    request.newName === "escape"
      ? new URL("../outside.ts", request.textDocument.uri).href
      : request.textDocument.uri;
  const edit = {
    range: { start: { line: 0, character: 0 }, end: { line: 0, character: 3 } },
    newText: request.newName,
  };
  return {
    changes: { [uri]: request.newName === "overlap" ? [edit, edit] : [edit] },
  };
});
connection.onRequest("hang", () => new Promise<never>(() => undefined));
connection.onRequest(ShutdownRequest.type, () => undefined);
connection.onNotification(ExitNotification.type, () => {
  process.exit(0);
});
connection.listen();
