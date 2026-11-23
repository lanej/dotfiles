import type {
  AgentSession,
  ExtensionAPI,
  ExtensionContext,
  ToolDefinition,
} from "@earendil-works/pi-coding-agent";

export function runChild(
  context: ExtensionContext,
  role: string,
  prompt: string,
  options: {
    pi: ExtensionAPI;
    cwd: string;
    configCwd: string;
    model: NonNullable<ExtensionContext["model"]>;
    thinkingLevel: ReturnType<ExtensionAPI["getThinkingLevel"]>;
    maxTurns: number;
    signal: AbortSignal;
    agentId: string;
    sessionDir: string;
    driverTools: ToolDefinition[];
    onSessionCreated(session: AgentSession): void;
  },
): Promise<{ responseText: string; aborted: boolean; failure?: string }>;
