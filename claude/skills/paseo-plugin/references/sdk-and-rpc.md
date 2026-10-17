## Choose the correct API

Use the existing Paseo SDK for normal Paseo operations. Use plugin RPC only for plugin-specific backend behavior.

### Call Paseo from a surface

`usePaseo()` borrows the selected host's current connection. Never create another client inside a surface. It is the plugin's one client in every surface: release your subscriptions in your cleanup; plugin teardown ends the rest.

```tsx
import { usePaseo } from "@getpaseo/plugin/client";

function PullRequestAction() {
  const paseo = usePaseo();

  async function createReviewWorkspace() {
    const workspace = await paseo.workspaces.create({
      title: "Review PR 42",
      source: {
        kind: "worktree",
        cwd: "/absolute/path/to/repository",
        action: "checkout",
        checkoutSource: { kind: "change_request", forge: "github", number: 42 },
      },
    });
    await workspace.agents.create({
      config: { provider: "codex/gpt-5.5" },
      prompt: "Review PR #42.",
    });
  }

  // Wire createReviewWorkspace to a Pressable.
  return null;
}
```

The API covers workspaces, agents, providers, and daemon config. It omits connection lifecycle because Paseo owns the connection. Consult the current [SDK reference](https://paseo.sh/docs/sdk/reference.md) for method details.

### Add daemon-side behavior

Define one Zod contract in `shared/`, register its subprocess handler in `index.server.ts`, and
call it from client code with `useRpc()`:

```ts
// shared/greeting.ts
import { defineRpc } from "@getpaseo/plugin";
import { z } from "zod";

const greeting = defineRpc({
  name: "greeting.create",
  input: z.object({ name: z.string() }),
  output: z.object({ message: z.string() }),
});
```

```ts
// server/greeting.ts
import type { RpcInput } from "@getpaseo/plugin";
import { greeting } from "../shared/greeting";

export async function createGreeting({ name }: RpcInput<typeof greeting>) {
  return { message: `Hello, ${name}!` };
}
```

```ts
// index.server.ts
import type { PluginServerContext } from "@getpaseo/plugin/server";
import { createGreeting } from "./server/greeting";
import { greeting } from "./shared/greeting";

export default function contribute(server: PluginServerContext) {
  server.handle(greeting, createGreeting);
  return () => {};
}
```

```tsx
// client/greeting.tsx
import { useRpc } from "@getpaseo/plugin/client";
import { greeting } from "../shared/greeting";

function Greeting() {
  const createGreeting = useRpc(greeting);
  // Use createGreeting({ name: "Ada" }) in a query, mutation, or event.
  return null;
}
```

Inputs and outputs are validated on both sides. Backend handlers receive the same `PaseoApi` as `{ paseo }`; their IPC-backed daemon session lives exactly as long as the subprocess. Backend code can use Node APIs and installed dependencies. Keep credentials, filesystem access, shell commands, and vendor API calls in the handler rather than the client surface.

Use TanStack Query for async request state, caching, and mutations.

### Debug daemon-side behavior

Backend contributions can use normal Node logging. `console.log()` writes to the plugin's stdout;
`console.error()` writes to stderr. Paseo captures both streams without interfering with plugin IPC.

Inspect recent output after install, reload, an RPC failure, or a subprocess crash:

```bash
paseo plugin logs my-plugin
paseo plugin logs my-plugin --json
paseo plugin logs my-plugin --host <url>
```

The same tail is available from **Settings → Plugins → Logs**. It includes initialization, handler,
cleanup, and final crash output. Reload, disable, and process failure retain the tail. Removing the
plugin clears it; restarting the daemon clears the in-memory tail. Structured copies also go to the
daemon log. Never log credentials or other secrets.
