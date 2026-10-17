## Create the project

Use an absolute path on the daemon machine. `init` writes files but does not install packages.

```bash
paseo plugin init /absolute/path/to/my-plugin
cd /absolute/path/to/my-plugin
npm install
```

The generated project contains:

```text
my-plugin/
  paseo-plugin.json
  OVERVIEW.md
  package.json
  tsconfig.json
  index.client.tsx
  index.server.ts
  client/greeting.tsx
  server/greeting.ts
  shared/greeting.ts
```

The manifest supplies the default install ID and supported Paseo versions:

```json
{ "id": "my-plugin", "requirements": { "paseo": ">=0.8.0" } }
```

Keep `requirements.paseo` correct whenever creating or editing a plugin. `init` uses `>=` followed
by the CLI version. Raise the minimum when adopting newer APIs; add an upper bound when a later
Paseo release is incompatible. Use npm semver ranges and explicitly include beta versions when
targeting betas. Missing requirements mean `<0.8.0`; complete the 0.8 entry migration before adding
`>=0.8.0`. Verify compatibility with both the daemon and the app running client contributions.
See [requirements](https://paseo.sh/docs/plugins/reference#requirements).

Each runtime has its own optional entry. A plugin must have at least one. Both entries accept
`.ts` or `.tsx`; use `.tsx` when an entry imports components.

| Path                             | Runtime           |
| -------------------------------- | ----------------- |
| `index.client.tsx` and `client/` | App               |
| `index.server.ts` and `server/`  | Daemon subprocess |
| `shared/`                        | Both              |

Do not put any other code modules in the plugin root.

A client import of `server/`, a server import of `client/`, and every `node:` import reachable from
client code is a compile error. A relative import to another code file in the plugin root is also a
compile error; move it into `client/`, `server/`, or `shared/`. Shared modules contain Zod contracts
and plain values; they do not import Node or React Native runtime APIs.

Default-export one contribution function from each entry and return cleanup:

```tsx
// index.client.tsx
import type { PluginClientContext } from "@getpaseo/plugin/client";

export default function contribute(client: PluginClientContext) {
  // Register components and client callbacks here.
  return () => {};
}
```

```ts
// index.server.ts
import type { PluginServerContext } from "@getpaseo/plugin/server";

export default function contribute(server: PluginServerContext) {
  // Register daemon-side RPC handlers here.
  return () => {};
}
```

Cleanup can be async. Use it for timers, watchers, sockets, subscriptions, and other resources
created by plugin code. Every client `add*` method returns an idempotent remover. Paseo calls the
entry cleanup first, removes registrations that remain, rejects pending RPCs, closes the plugin
session, and stops the subprocess when the plugin stops.
