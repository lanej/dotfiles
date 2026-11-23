import type {
  BeforeAgentStartEvent,
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { Connection } from "../server/connection";
import { authorizeTurnRpc } from "../shared/contracts";

export default function turnOwner(pi: ExtensionAPI) {
  const home = process.env.PASEO_HOME;
  const worker = {
    serverId: process.env.PASEO_TASK_SERVER_ID,
    taskId: process.env.PASEO_TASK_ID,
    agentId: process.env.PASEO_AGENT_ID,
  };
  let rejectedTrigger: BeforeAgentStartEvent["messageType"] | undefined;
  async function authorize() {
    const binding = authorizeTurnRpc.input.parse(worker);
    if (!home)
      throw new Error("Managed Pi workers require the Paseo host directory");
    const connection = new Connection(home, { reconnect: false });
    try {
      if ((await connection.localServerId()) !== binding.serverId)
        throw new Error("Connected to a different Paseo host");
      authorizeTurnRpc.output.parse(
        await connection.raw.invokePluginRpc(
          "tasks",
          authorizeTurnRpc.name,
          binding,
        ),
      );
    } finally {
      await connection.close();
    }
  }

  async function denied(ctx: ExtensionContext): Promise<boolean> {
    try {
      await authorize();
      return false;
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      try {
        ctx.ui.notify(`Task turn blocked: ${reason}`, "error");
      } catch {
        // Pi continues after handler exceptions. Deny even when the operator UI has disconnected.
      }
      return true;
    }
  }

  pi.on("input", async (_event, ctx) => {
    if (await denied(ctx)) return { action: "handled" };
    return { action: "continue" };
  });
  pi.on("before_agent_start", async (event, ctx) => {
    rejectedTrigger = (await denied(ctx)) ? event.messageType : undefined;
    if (rejectedTrigger) ctx.abort();
  });
  pi.on("message_end", ({ message }) => {
    if (message.role !== rejectedTrigger) return;
    // Pi finalizes the starting message even after a startup abort. Replace it before Pi saves it for later runs.
    rejectedTrigger = undefined;
    const marker = {
      content: "Paseo blocked this task input.",
      timestamp: message.timestamp,
    };
    if (message.role === "user")
      return { message: { role: "user", ...marker } };
    return {
      message: {
        role: "custom",
        customType: "paseo-task-input-blocked",
        display: true,
        ...marker,
      },
    };
  });
  pi.on("agent_end", () => {
    rejectedTrigger = undefined;
  });
}
