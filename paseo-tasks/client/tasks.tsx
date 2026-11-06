import {
  useRpc, type PluginScreenProps, type PluginWorkspacePanelProps, type PluginSurfaceProps,
} from "@getpaseo/plugin/client";
import { ExternalLink } from "@getpaseo/plugin/client/ui";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { View, Text, Pressable, ScrollView, TextInput } from "react-native";
import { z } from "zod";
import {
  listRpc, bulkRpc, acceptRpc, createRpc, discoverRpc, adoptRpc, managerRpc,
  type Task, type Address, type Brief, type hostSnapshot,
} from "../shared/contracts";

type Surface = Pick<PluginSurfaceProps, "theme" | "layout" | "navigation">;
type Snapshot = z.infer<typeof hostSnapshot>;
const key = (value: Address) => `${value.serverId}/${value.taskId}`;
function Button({ title, onPress, disabled = false, theme }: {
  title: string; onPress(): void; disabled?: boolean; theme: PluginSurfaceProps["theme"];
}) {
  return <Pressable accessibilityRole="button" accessibilityLabel={title} disabled={disabled} onPress={onPress}
    style={{ padding: 10, borderRadius: 6, opacity: disabled ? 0.5 : 1, backgroundColor: theme.colors.surface2 }}>
    <Text style={{ color: theme.colors.foreground }}>{title}</Text>
  </Pressable>;
}
export function TaskCard({ value, selected, onSelect, refresh, theme, layout, navigation, offline = false }: Surface & {
  value: Task; selected?: boolean; onSelect?(): void; refresh(): void; offline?: boolean;
}) {
  const accept = useRpc(acceptRpc);
  const action = useMutation({ mutationFn: (proposalId: string) => accept({
    serverId: value.serverId, taskId: value.taskId, revision: value.revision, proposalId,
  }), onSuccess: refresh });
  const text = { color: theme.colors.foreground };
  const muted = { color: theme.colors.foregroundMuted };
  return <View testID={`task-card-${value.serverId}-${value.taskId}`} style={{ backgroundColor: theme.colors.surface1, padding: layout.compact ? 14 : 20, gap: 8,
    borderRadius: 8, borderWidth: 1, borderColor: selected ? theme.colors.accent : theme.colors.border }}>
    <View style={{ flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
      {onSelect && <Button title={selected ? "Deselect task" : "Select task"} onPress={onSelect} theme={theme} />}
      <Text style={{ ...text, fontSize: 18, flexShrink: 1 }}>{value.title}</Text>
    </View>
    <Text style={muted}>{value.status} · {value.control} · agent {value.activity} · priority {value.priority}{value.group ? ` · ${value.group}` : ""}</Text>
    <Text selectable style={muted}>{key(value)}</Text>
    <Text style={text}>{value.outcome || "Draft idea: define the desired outcome."}</Text>
    {!!value.successCriteria.length && <Text style={text}>Success: {value.successCriteria.join("; ")}</Text>}
    {!!value.constraints.length && <Text style={muted}>Constraints: {value.constraints.join("; ")}</Text>}
    {!!value.approach && <Text style={text}>Approach: {value.approach}</Text>}
    {!!value.progress && <Text style={text}>Progress: {value.progress}</Text>}
    {!!value.evidence.length && <Text selectable style={text}>Evidence: {value.evidence.join("\n")}</Text>}
    {!!value.blocker && <Text style={{ color: theme.colors.statusWarning }}>Blocker: {value.blocker}</Text>}
    {!!value.nextAction && <Text style={text}>Next: {value.nextAction}</Text>}
    {!!value.error && <Text selectable style={{ color: theme.colors.statusDanger }}>{value.error}</Text>}
    <Text selectable style={muted}>Repository: {value.repository ?? "No repository required"}{value.worker ? `\nCheckout: ${value.worker.cwd}` : ""}</Text>
    {value.treehouseLease && <Text selectable style={muted}>Treehouse lease: {value.treehouseLease.lease_id}{"\n"}Branch: {value.treehouseLease.branch}</Text>}
    {value.prWatches.map(watch => <Text key={watch.url} style={muted}>PR watch: {watch.phase} · {watch.detail}{"\n"}Observed: {watch.observedAt}</Text>)}
    <Text style={muted}>Last task update: {value.updatedAt}{value.observedAt ? `\nAgent observed: ${value.observedAt}` : "\nAgent has not been observed"}</Text>
    {value.worker && <Button title="Open task conversation" theme={theme} disabled={offline || !navigation}
      onPress={() => navigation?.openAgent({ serverId: value.serverId, agentId: value.worker!.agentId })} />}
    {value.github.map(url => <ExternalLink key={url} href={url}><Text style={text}>{url}</Text></ExternalLink>)}
    {value.proposals.filter(proposal => !proposal.accepted).map(proposal => <View key={proposal.id} style={{ gap: 8 }}>
      <Text style={text}>Proposed title: {proposal.brief.title}{"\n"}Kind: {proposal.brief.kind}</Text>
      <Text style={text}>Proposed outcome: {proposal.brief.outcome}</Text>
      <Text style={muted}>Success: {proposal.brief.successCriteria.join("; ")}{"\n"}Constraints: {proposal.brief.constraints.join("; ")}</Text>
      <Text selectable style={muted}>Repository: {proposal.brief.repository ?? "None"}{"\n"}Base ref: {proposal.brief.baseRef ?? "None"}</Text>
      <Button title="Accept proposed task brief" theme={theme} disabled={offline || action.isPending}
        onPress={() => action.mutate(proposal.id)} />
    </View>)}
    {action.error && <Text style={{ color: theme.colors.statusDanger }}>{action.error.message}</Text>}
  </View>;
}
function TaskForm({ serverId, theme, onDone, adoptedAgentId }: {
  serverId: string; theme: PluginSurfaceProps["theme"]; onDone(): void; adoptedAgentId?: string;
}) {
  const create = useRpc(createRpc);
  const adopt = useRpc(adoptRpc);
  const [title, setTitle] = useState("");
  const [outcome, setOutcome] = useState("");
  const [criteria, setCriteria] = useState("");
  const [constraints, setConstraints] = useState("");
  const [repository, setRepository] = useState("");
  const [baseRef, setBaseRef] = useState("origin/main");
  const [kind, setKind] = useState<Brief["kind"]>("investigation");
  const [group, setGroup] = useState("");
  // NOTE: A UUID is retained through retries; a lost creation response must not launch a second worker.
  const [requestId] = useState(() => {
    const random = () => Math.floor(Math.random() * 16).toString(16);
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, char =>
      char === "x" ? random() : ((Math.floor(Math.random() * 16) & 3) | 8).toString(16));
  });
  const mutation = useMutation({
    mutationFn: () => {
      const input = { requestId, serverId, start: true, group: group || null, brief: {
        title, outcome, successCriteria: criteria.split("\n").map(value => value.trim()).filter(Boolean),
        constraints: constraints.split("\n").map(value => value.trim()).filter(Boolean), kind,
        repository: repository || null, baseRef: kind === "coding" ? baseRef || null : null,
      } };
      return adoptedAgentId ? adopt({ ...input, agentId: adoptedAgentId }) : create(input);
    },
    onSuccess: onDone,
  });
  const field = (label: string, value: string, onChangeText: (text: string) => void, multiline = false) =>
    <View key={label} style={{ gap: 4 }}>
      <Text style={{ color: theme.colors.foregroundMuted }}>{label}</Text>
      <TextInput accessibilityLabel={label} value={value} onChangeText={onChangeText} multiline={multiline}
        placeholderTextColor={theme.colors.foregroundMuted}
        style={{ color: theme.colors.foreground, backgroundColor: theme.colors.surface2, padding: 10, borderRadius: 6 }} />
    </View>;
  return <View style={{ gap: 10 }}>
    <Text style={{ color: theme.colors.foreground }}>Create on {serverId}{adoptedAgentId ? ` · adopt ${adoptedAgentId}` : ""}</Text>
    {field("Task title", title, setTitle)}
    {field("Desired outcome", outcome, setOutcome, true)}
    {field("Success criteria, one per line", criteria, setCriteria, true)}
    {field("Constraints, one per line", constraints, setConstraints, true)}
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
      {(["coding", "investigation", "planning", "decision"] as const).map(value =>
        <Button key={value} title={`${kind === value ? "✓ " : ""}${value}`} theme={theme} onPress={() => setKind(value)} />)}
    </View>
    {field("Repository directory on this host", repository, setRepository)}
    {kind === "coding" && !adoptedAgentId && field("Base Git ref", baseRef, setBaseRef)}
    {field("Task group", group, setGroup)}
    <Button title={adoptedAgentId ? "Adopt selected conversation" : "Create task"} theme={theme}
      disabled={!title.trim() || mutation.isPending} onPress={() => mutation.mutate()} />
    {mutation.error && <Text style={{ color: theme.colors.statusDanger }}>{mutation.error.message}</Text>}
  </View>;
}
export function TasksScreen(props: PluginScreenProps) {
  const { theme, layout, host, navigation } = props;
  const list = useRpc(listRpc);
  const bulk = useRpc(bulkRpc);
  const discover = useRpc(discoverRpc);
  const manager = useRpc(managerRpc);
  const queryClient = useQueryClient();
  const queryKey = ["tasks", host.id];
  const query = useQuery({ queryKey, queryFn: () => list({ aggregate: true }), refetchInterval: 10000 });
  const refresh = () => { void queryClient.invalidateQueries({ queryKey }); };
  const [selected, setSelected] = useState<Address[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [candidate, setCandidate] = useState<string>();
  const [filter, setFilter] = useState("");
  const [priority, setPriority] = useState("50");
  const [managerDirectory, setManagerDirectory] = useState("");
  const operation = useMutation({ mutationFn: (action: "pause" | "resume" | "archive" | "reprioritize") =>
    bulk({ tasks: selected, action, ...(action === "reprioritize" ? { priority: Number(priority) } : {}) }), onSuccess: refresh });
  const discovery = useMutation({ mutationFn: () => discover({ serverId: host.id }) });
  const createManager = useMutation({ mutationFn: () => manager({ cwd: managerDirectory }),
    onSuccess: result => navigation?.openAgent(result) });
  const inputStyle = { color: theme.colors.foreground, backgroundColor: theme.colors.surface2, padding: 10, borderRadius: 6 };
  return <ScrollView testID="tasks-screen" style={{ flex: 1, backgroundColor: theme.colors.surface0 }}
    contentContainerStyle={{ padding: layout.compact ? 12 : 24, gap: 12 }}>
    <Text style={{ color: theme.colors.foreground, fontSize: layout.compact ? 22 : 28 }}>Tasks</Text>
    <Text style={{ color: theme.colors.foregroundMuted }}>Open a worker's conversation to discuss its task directly. A task's status and its agent's activity are separate.</Text>
    <TextInput accessibilityLabel="Filter tasks by title, status, or group" placeholder="Filter tasks" placeholderTextColor={theme.colors.foregroundMuted}
      value={filter} onChangeText={setFilter} style={inputStyle} />
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
      <Button title="New task" theme={theme} onPress={() => { setCandidate(undefined); setShowForm(value => !value); }} />
      <Button title="Discover conversations" theme={theme} onPress={() => discovery.mutate()} />
      <Button title="Refresh" theme={theme} onPress={refresh} />
    </View>
    <TextInput accessibilityLabel="Task manager working directory" placeholder="Task manager working directory" placeholderTextColor={theme.colors.foregroundMuted}
      value={managerDirectory} onChangeText={setManagerDirectory} style={inputStyle} />
    <Button title="Open a new task manager conversation" theme={theme} disabled={!managerDirectory || createManager.isPending}
      onPress={() => createManager.mutate()} />
    {showForm && <TaskForm key={candidate ?? "new"} serverId={host.id} theme={theme}
      adoptedAgentId={candidate} onDone={() => { setShowForm(false); refresh(); }} />}
    {discovery.data?.map(value => <View key={value.agentId} style={{ gap: 6 }}>
      <Text style={{ color: theme.colors.foreground }}>{value.title} · {value.activity}{"\n"}{value.cwd}</Text>
      <Button title={`Select ${value.title} for adoption`} theme={theme} onPress={() => { setCandidate(value.agentId); setShowForm(true); }} />
    </View>)}
    {selected.length > 0 && <View style={{ gap: 8 }}>
      <Text style={{ color: theme.colors.foreground }}>{selected.length} tasks selected</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {(["pause", "resume", "archive"] as const).map(action =>
          <Button key={action} title={action} theme={theme} disabled={operation.isPending} onPress={() => operation.mutate(action)} />)}
        <TextInput accessibilityLabel="Task priority" keyboardType="numeric" value={priority} onChangeText={setPriority} style={inputStyle} />
        <Button title="Reprioritize" theme={theme} disabled={operation.isPending} onPress={() => operation.mutate("reprioritize")} />
      </View>
    </View>}
    {operation.data?.map(value => <Text key={key(value)} style={{ color: value.result === "applied" ? theme.colors.foreground : theme.colors.statusWarning }}>
      {key(value)}: {value.result} · {value.message}
    </Text>)}
    {[query.error, operation.error, discovery.error, createManager.error].filter(Boolean).map((error, index) =>
      <Text key={index} style={{ color: theme.colors.statusDanger }}>{error!.message}</Text>)}
    {query.isPending && <Text style={{ color: theme.colors.foregroundMuted }}>Loading tasks…</Text>}
    {query.data?.map(snapshot => <View key={snapshot.serverId} style={{ gap: 10 }}>
      <Text style={{ color: theme.colors.foreground, fontSize: 18 }}>{snapshot.label} · {snapshot.connection}</Text>
      <Text style={{ color: theme.colors.foregroundMuted }}>Last observation: {snapshot.observedAt ?? "Never connected"}</Text>
      {snapshot.error && <Text style={{ color: theme.colors.statusWarning }}>{snapshot.error}</Text>}
      {snapshot.tasks.filter(value => value.control !== "archived" &&
        `${value.title} ${value.status} ${value.group ?? ""}`.toLowerCase().includes(filter.toLowerCase())).map(value =>
        <TaskCard key={key(value)} value={value} theme={theme} layout={layout} navigation={navigation} refresh={refresh}
          offline={snapshot.connection !== "online"} selected={selected.some(item => key(item) === key(value))}
          onSelect={() => setSelected(current => current.some(item => key(item) === key(value)) ?
            current.filter(item => key(item) !== key(value)) : [...current, { serverId: value.serverId, taskId: value.taskId }])} />)}
      {!snapshot.tasks.length && <Text style={{ color: theme.colors.foregroundMuted }}>No tasks observed on this host.</Text>}
    </View>)}
  </ScrollView>;
}
export function TaskPanel(props: PluginWorkspacePanelProps) {
  const list = useRpc(listRpc);
  const query = useQuery({ queryKey: ["task-panel", props.host.id, props.workspaceId],
    queryFn: () => list({ aggregate: false }), refetchInterval: 10000 });
  const values = query.data?.flatMap((host: Snapshot) => host.tasks).filter(value => value.worker?.workspaceId === props.workspaceId) ?? [];
  return <ScrollView style={{ flex: 1, backgroundColor: props.theme.colors.surface0 }}
    contentContainerStyle={{ padding: props.layout.compact ? 12 : 24, gap: 12 }}>
    {values.map(value => <TaskCard key={key(value)} {...props} value={value} refresh={() => { void query.refetch(); }} />)}
    {!values.length && <Text style={{ color: props.theme.colors.foregroundMuted }}>No task is assigned to this workspace.</Text>}
    {query.error && <Text style={{ color: props.theme.colors.statusDanger }}>{query.error.message}</Text>}
  </ScrollView>;
}
