import { createInterface } from "node:readline";
import { z } from "zod";
import { Zellij } from "../zellij.ts";

const session = process.argv[2];
if (session === undefined) throw new Error("Missing fixture Zellij session");

const pane = z.number().int().min(0).max(0xffffffff);
const request = z.discriminatedUnion("action", [
  z.object({ action: z.literal("panes") }),
  z.object({
    action: z.literal("capture"),
    pane,
    full: z.boolean(),
    ansi: z.boolean(),
  }),
  z.object({ action: z.literal("focus"), pane }),
  z.object({ action: z.literal("text"), pane, text: z.string() }),
  z.object({
    action: z.literal("keys"),
    pane,
    bytes: z.array(z.number().int().min(0).max(255)),
  }),
]);

type Request = z.infer<typeof request>;

async function dispatch(zellij: Zellij, input: Request): Promise<string> {
  switch (input.action) {
    case "panes":
      return await zellij.paneListing();
    case "capture":
      return await zellij.capture(input.pane, input.full, input.ansi);
    case "focus":
      await zellij.focus(input.pane);
      return "";
    case "text":
      await zellij.writeText(input.pane, input.text);
      return "";
    case "keys":
      await zellij.writeBytes(input.pane, input.bytes);
      return "";
  }
}

let zellij: Zellij | undefined;
for await (const line of createInterface({ input: process.stdin })) {
  try {
    const input = request.parse(JSON.parse(line));
    zellij ??= new Zellij(session);
    const output = await dispatch(zellij, input);
    process.stdout.write(`${JSON.stringify({ output })}\n`);
  } catch (cause) {
    process.stdout.write(
      `${JSON.stringify({ error: cause instanceof Error ? cause.message : String(cause) })}\n`,
    );
  }
}
