## Add a workspace panel

Workspace panels live beside agents, terminals, files, and diffs. Plugins run on desktop and
mobile, and Paseo has multiple themes. Every `Text` must take its color from `theme.colors`.
Use `layout.compact` for padding and stacking. Unstyled text is black and fails in dark themes.

```tsx
import {
  type PluginClientContext,
  type PluginWorkspacePanelProps,
  useWorkspace,
} from "@getpaseo/plugin/client";
import { useMemo } from "react";
import { Text, View } from "react-native";

function Overview({ theme, layout, workspaceId }: PluginWorkspacePanelProps) {
  const name = useWorkspace(workspaceId, (workspace) => workspace.name);
  const styles = useMemo(
    () => ({
      screen: {
        flex: 1,
        padding: layout.compact ? 16 : 24,
        gap: layout.compact ? 8 : 12,
        backgroundColor: theme.colors.surface0,
      },
      title: { color: theme.colors.foreground, fontSize: layout.compact ? 20 : 24 },
    }),
    [theme, layout.compact],
  );
  return (
    <View style={styles.screen}>
      <Text style={styles.title}>{name}</Text>
    </View>
  );
}

export default function contribute(client: PluginClientContext) {
  client.addWorkspacePanel({
    id: "overview",
    title: "Workspace overview",
    icon: "PanelsTopLeft",
    context: "workspace",
    Component: Overview,
  });
  client.addCommandCenterItem({
    id: "open-overview",
    title: "Open workspace overview",
    icon: "PanelsTopLeft",
    context: "workspace",
    onSelect({ openPanel }) {
      openPanel("overview");
    },
  });
  return () => {};
}
```

Use `useWorkspace(id, selector)` and `useAgent(id, selector)`. Selectors are required
and their results use shallow equality. Never select the whole snapshot or add an RPC to discover
the active workspace or agent. Command callbacks receive the selected host's `paseo`, typed
`rpc(contract, input)`, `openScreen({ screenId, params? })`, and contextual `openPanel(id)`
capabilities.

## Add a screen and a sidebar item

Plugin screens use React Native primitives and work across desktop, browser, iOS, and Android. A sidebar item, in the header or the footer, is a component: render one or more `SidebarRow`s from `@getpaseo/plugin/client/ui`, with `SidebarSeparator` between groups, and call `openScreen` or `openPopover` from them. A screen's `title` is a string or a function of its `params`; its component receives the `params` it was opened with. Color text from `theme.colors` and pad from `layout.compact`.

```tsx
import type {
  PluginClientContext,
  PluginScreenProps,
  PluginSidebarItemProps,
} from "@getpaseo/plugin/client";
import { SidebarRow } from "@getpaseo/plugin/client/ui";
import { useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";

function Counter({ theme, layout }: PluginScreenProps) {
  const [count, setCount] = useState(0);
  const styles = useMemo(
    () => ({
      screen: {
        flex: 1,
        padding: layout.compact ? 16 : 24,
        gap: 16,
        backgroundColor: theme.colors.surface0,
      },
      count: { color: theme.colors.foreground, fontSize: layout.compact ? 36 : 48 },
      button: { padding: 14, borderRadius: 10, backgroundColor: theme.colors.accent },
      buttonText: { color: theme.colors.accentForeground, textAlign: "center" as const },
    }),
    [theme, layout.compact],
  );
  return (
    <View style={styles.screen}>
      <Text style={styles.count}>{count}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Increment counter, currently ${count}`}
        onPress={() => setCount((value) => value + 1)}
        style={styles.button}
      >
        <Text style={styles.buttonText}>Count me in</Text>
      </Pressable>
    </View>
  );
}

function CounterItem({ currentScreen, openScreen }: PluginSidebarItemProps) {
  return (
    <SidebarRow
      icon="ListPlus"
      active={currentScreen?.screenId === "main"}
      onPress={() => openScreen({ screenId: "main" })}
    />
  );
}

export default function contribute(client: PluginClientContext) {
  client.addScreen({ id: "main", title: "Counter", Component: Counter });
  client.addSidebarHeaderItem({ id: "main", title: "Counter", Component: CounterItem });
  return () => {};
}
```

Icons are Lucide icon names. `theme` is a typed `PluginTheme` on every screen and panel. Primary text uses `theme.colors.foreground`; labels use `theme.colors.foregroundMuted`; the root view uses `theme.colors.surface0`. `layout.compact` is true on mobile and narrow windows. Paseo owns the route, header, host picker, close action, error boundary, and per-installation query client.

Before writing imports, classify each module as shared, client, or server. Follow the
[SDK import boundaries](https://paseo.sh/docs/plugins/reference.md#runtime-modules), including
transitive and type dependencies. The root is shared-only; hooks and client contexts belong to
`@getpaseo/plugin/client`, server contexts to `/server`, and host UI to `/client/react-native` or `/client/ui`.
Install dependencies locally for typechecking; Paseo supplies host runtime modules. JSX uses the
automatic runtime. Do not import `/client/host` from plugin code.

## Works on mobile

Before reporting a plugin done:

- Use React Native primitives only: `View`, `Text`, `Pressable`, `ScrollView`, and `TextInput`.
- Do not use HTML elements, `className`, CSS strings, or `onClick`.
- Do not put `"DOM"` in `tsconfig.json` or use `/// <reference lib="dom" />`. Put DOM globals only in
  `client/web.ts`, declare only what that module uses, gate every export on `Platform.OS === "web"`,
  and provide the native alternative or a no-op.
- Take colors from `theme.colors`.
- Check the compact layout.

Run this audit on `client/`:

```bash
rg -n "document\.|window\.|localStorage|navigator\.|<[a-z]+[ >]|className=|onClick=" client/
```

A hit outside `client/web.ts` is a bug.
