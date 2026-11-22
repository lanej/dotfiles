import type {
  SessionEntry,
  SessionMessageEntry,
} from "@earendil-works/pi-coding-agent";
import { z } from "zod";

export enum PiMode {
  Tui = "tui",
  Rpc = "rpc",
  Json = "json",
  Print = "print",
}
export const piModeSchema = z.enum(PiMode);

export enum PiEvent {
  SessionStart = "session_start",
  SessionShutdown = "session_shutdown",
  SessionTree = "session_tree",
  SessionCompact = "session_compact",
  ModelSelect = "model_select",
  Input = "input",
  AgentStart = "agent_start",
  AgentSettled = "agent_settled",
  PromptStart = "ui_prompt_start",
  PromptEnd = "ui_prompt_end",
  ToolStart = "tool_execution_start",
}

export enum PiEntryType {
  Message = "message",
  Custom = "custom",
  Compaction = "compaction",
  Usage = "usage",
  BranchSummary = "branch_summary",
}

export enum PiMessageRole {
  Assistant = "assistant",
  User = "user",
  ToolResult = "toolResult",
}

export function isEntry<K extends PiEntryType>(
  entry: SessionEntry,
  kind: K,
): entry is Extract<SessionEntry, { type: `${K}` }> {
  const tag: string = kind;
  return entry.type === tag;
}

export function isMessageRole<K extends PiMessageRole>(
  message: SessionMessageEntry["message"],
  role: K,
): message is Extract<SessionMessageEntry["message"], { role: `${K}` }> {
  const tag: string = role;
  return message.role === tag;
}

export enum FooterStatus {
  Bead = "pi-bead",
  Plan = "pi-plan",
}

export enum NavigationKey {
  Up = "up",
  Down = "down",
  Right = "right",
  Escape = "escape",
  Enter = "enter",
  Cancel = "ctrl+c",
  VimUp = "k",
  VimDown = "j",
}

export enum ArrowSequence {
  Up = "\x1b[A",
  Down = "\x1b[B",
}
