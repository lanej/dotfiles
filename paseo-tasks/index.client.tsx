import type { PluginClientContext, PluginSidebarItemProps } from "@getpaseo/plugin/client";
import { SidebarRow } from "@getpaseo/plugin/client/ui";
import { TasksScreen, TaskPanel } from "./client/tasks";

function TasksItem({ currentScreen, openScreen }: PluginSidebarItemProps) {
  return <SidebarRow icon="ListTodo" active={currentScreen?.screenId === "tasks"}
    onPress={() => openScreen({ screenId: "tasks" })} />;
}
export default function contribute(client: PluginClientContext) {
  const cleanup = [
    client.addScreen({ id: "tasks", title: "Tasks", Component: TasksScreen }),
    client.addSidebarHeaderItem({ id: "tasks", title: "Tasks", Component: TasksItem }),
    client.addWorkspacePanel({ id: "task", title: "Task context", icon: "ListTodo", context: "workspace", Component: TaskPanel }),
    client.addCommandCenterItem({ id: "tasks", title: "Open tasks", icon: "ListTodo", context: "global",
      onSelect: ({ openScreen }) => openScreen({ screenId: "tasks" }) }),
    client.addCommandCenterItem({ id: "task", title: "Open task context", icon: "ListTodo", context: "workspace",
      onSelect: ({ openPanel }) => openPanel("task") }),
  ];
  return () => { for (const dispose of cleanup.reverse()) dispose(); };
}
