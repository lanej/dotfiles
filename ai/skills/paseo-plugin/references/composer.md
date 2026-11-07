## Add a composer attachment source

Define a search RPC and declarative source in `shared/`, handle it on the server, and register it on
the client:

```ts
// shared/issues.ts
import { defineAttachmentSource, defineRpc } from "@getpaseo/plugin";
import { z } from "zod";

const searchIssues = defineRpc({
  name: "issues.search",
  input: z.object({ query: z.string() }),
  output: z.object({
    items: z.array(
      z.object({
        id: z.string(),
        identifier: z.string(),
        title: z.string(),
        subtitle: z.string().optional(),
        url: z.string().url(),
        text: z.string(),
        resourceType: z.string(),
      }),
    ),
  }),
});

const issues = defineAttachmentSource({
  id: "issues",
  title: "Acme issue",
  icon: "CircleDot",
  pickerTitle: "Attach Acme issue",
  searchPlaceholder: "Search by identifier or title",
  search: searchIssues,
});
```

```ts
// index.server.ts
import type { PluginServerContext } from "@getpaseo/plugin/server";
import { searchIssues } from "./shared/issues";

export default function contribute(server: PluginServerContext) {
  server.handle(searchIssues, ({ query }) => searchAcmeIssues(query));
  return () => {};
}
```

```tsx
// index.client.tsx
import type { PluginClientContext } from "@getpaseo/plugin/client";
import { issues } from "./shared/issues";

export default function contribute(client: PluginClientContext) {
  client.addAttachmentSource(issues);
  return () => {};
}
```

Return complete text snapshots. Paseo owns the composer menu, picker, pills, drafts, and submission. Credentials and vendor calls stay in the daemon handler.

## Add a client slash command

A slash command runs plugin code in the app when the user submits `/name args`. Nothing is sent to the agent. `args` is the raw text after the command name, trimmed; parse it in the plugin.

```ts
client.addSlashCommand({
  name: "review",
  description: "Run the review bot",
  argumentHint: "[scope]",
  context: "agent", // or "workspace" so drafts get it too
  async onSubmit({ args, agent, rpc, openPanel }) {
    await rpc(startReview, { agentId: agent.id, scope: args });
    openPanel("review");
  },
});
```

The callback receives the same context as the matching Command Center item plus `args`. Paseo owns the autocomplete row, input clearing, and the error toast; put pending UI in a pill or panel. Precedence is built-in client commands, then plugin commands, then provider commands; a lower-precedence collision is dropped. Commands do not run while the composer has attachments. Server-side slash commands do not exist.

## Add a composer pill

A pill is a per-agent button in the composer track bar next to Tasks and Subagents. Add and remove pills from the client entry lifecycle. `addComposerPill` exists on `PluginClientContext`.

```tsx
import type { PluginButtonRegistration, PluginClientContext } from "@getpaseo/plugin/client";

export function contributeClient(client: PluginClientContext) {
  const pills = new Map<string, PluginButtonRegistration>();
  const lifetime = new AbortController();
  const register = (agent: { id: string; workspaceId?: string | null }) => {
    if (lifetime.signal.aborted || !agent.workspaceId) return;
    const agentId = agent.id;
    const workspaceId = agent.workspaceId;
    pills.get(agentId)?.remove();
    pills.set(
      agentId,
      client.addComposerPill({
        id: "review",
        workspaceId,
        agentId,
        button: {
          title: "Open review",
          icon: "Scan",
          label: "Review",
          behavior: {
            kind: "action",
            onPress() {
              client.openPanel("review", { workspaceId, agentId });
            },
          },
        },
      }),
    );
  };
  const removeAll = () => {
    for (const pill of pills.values()) pill.remove();
    pills.clear();
  };
  // An owned list subscription delivers existing agents, then updates, and a fresh snapshot after a reconnect.
  void client.paseo.agents
    .list({ subscribe: {}, signal: lifetime.signal })
    .then(({ subscription }) => {
      subscription.subscribe({
        snapshot: ({ entries }) => {
          removeAll();
          for (const { agent } of entries) register(agent);
        },
        update: (message) => {
          if (message.type !== "agent_update") return;
          const update = message.payload;
          if (update.kind === "upsert") return register(update.agent);
          pills.get(update.agentId)?.remove();
          pills.delete(update.agentId);
        },
      });
      return undefined;
    })
    .catch((error) => {
      if (!lifetime.signal.aborted) console.error("Agent observation failed", error);
    });
  return () => {
    lifetime.abort();
    removeAll();
  };
}
```

Call `contributeClient(client)` from `index.client.tsx`, or move its body into that entry. The `button` descriptor sets the icon, label, and behavior; Paseo owns the pressable, chrome, pending state, error reporting, and placement. `addComposerPill` returns a registration with `update()` and `remove()`. `remove()` is idempotent, and Paseo removes every pill when the plugin, client entrypoint, or host connection is torn down.
